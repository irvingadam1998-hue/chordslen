#!/usr/bin/env python3
"""Isolated real-song experiments: immutable inputs, no production/model edits."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.model.features import file_digest
from backend.model.labels import INTERVALS, QUALITIES, parse_label, state_name
from backend.model.metrics import aggregate, intervals_from_timeline, score_song


def write_json(path, value):
    # Never overwrite an experiment or another agent's artifact.
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def code_fingerprints():
    paths = [Path(__file__), Path(__file__).with_name('review.html')]
    for directory in ('backend/model', 'backend/scripts'):
        paths.extend((ROOT / directory).glob('*.py'))
    return {str(p.relative_to(ROOT)): file_digest(p) for p in sorted(paths)}


def normalize_audio(source, target):
    if Path(source).suffix.lower() == '.wav':
        shutil.copyfile(source, target)
    else:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(source),
                        '-vn', '-acodec', 'pcm_s16le', str(target)], check=True)


def hpss_audio(source, target, sample_rate):
    """Ablation only: reduce percussion, not vocals or individually separated stems."""
    import librosa
    import numpy as np
    import soundfile as sf
    from backend.scripts.analyze import _harmonic_audio
    y, _ = librosa.load(source, sr=sample_rate, mono=True)
    out = np.empty_like(y)
    chunk = max(512, int(10 * sample_rate / 512) * 512)
    context = max(512, int(sample_rate / 512) * 512)
    for start in range(0, len(y), chunk):
        end = min(len(y), start + chunk)
        first, last = max(0, start - context), min(len(y), end + context)
        separated = _harmonic_audio(y[first:last])
        out[start:end] = separated[start - first:end - first]
    sf.write(target, out, sample_rate, subtype='FLOAT')


def summarize(result):
    intervals = intervals_from_timeline(result['chords_timeline'], result['duration'])
    sevenths = sum(end - start for start, end, name in intervals
                   if parse_label(name).quality in (2, 3, 4))
    durations = {}
    for start, end, name in intervals:
        durations[name] = durations.get(name, 0.0) + end - start
    return {'events': len(intervals), 'duration_seconds': result['duration'],
            'seventh_seconds': sevenths,
            'seventh_fraction': sevenths / result['duration'] if result['duration'] else None,
            'seconds_per_chord': dict(sorted(durations.items(), key=lambda p: -p[1])),
            'accuracy_available': False}


def alternatives(result, diagnostic_path):
    import numpy as np
    with np.load(diagnostic_path, allow_pickle=False) as data:
        probability = data['joint']
        frame_seconds = float(data['frame_seconds'])
    rows = []
    for event in result['chords_timeline']:
        first = max(0, round(event['time'] / frame_seconds))
        last = min(len(probability), max(first + 1, round(event['end'] / frame_seconds)))
        if first >= last:
            continue
        mean = probability[first:last].mean(axis=0)
        top = np.argsort(mean)[-4:][::-1]
        rows.append({'start': event['time'], 'end': event['end'], 'prediction': event['chord'],
                     'margin': float(mean[top[0]] - mean[top[1]]),
                     'alternatives': [{'chord': state_name(int(s)), 'probability': float(mean[s])}
                                      for s in top]})
    # Uncalibrated ambiguity ranking, NOT a list of verified errors.
    return sorted(rows, key=lambda row: row['margin'])


def render_review(folder, report):
    template = Path(__file__).with_name('review.html').read_text()
    payload = json.dumps(report, ensure_ascii=False).replace('<', '\\u003c')
    content = template.replace('__REPORT_JSON__', payload)
    content = content.replace('__TITLE__', html.escape(report.get('title') or 'Revisión de acordes'))
    (folder / 'review.html').write_text(content)


def analyze(args):
    import soundfile as sf
    import torch
    from backend.model.inference import load_model, analyze_neural
    from backend.scripts.analyze import _analyze_audio
    from backend.scripts.youtube import download_audio
    source_checkpoint = args.checkpoint.resolve()
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = (args.output or ROOT / 'experiments' / 'real-world' / stamp).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    before = code_fingerprints()
    checkpoint_hash = file_digest(source_checkpoint)
    checkpoint = folder / 'model.pt'
    shutil.copyfile(source_checkpoint, checkpoint)
    if file_digest(checkpoint) != checkpoint_hash or file_digest(source_checkpoint) != checkpoint_hash:
        raise ValueError('El checkpoint cambió durante la copia; repite cuando termine el entrenamiento')
    torch.set_num_threads(2)
    loaded = load_model(checkpoint, args.device, allow_experimental=True)
    audio = folder / 'audio.wav'
    title, artist, notices = '', '', []
    if args.url:
        # Cookies live only in the downloader's private temporary directory.
        with tempfile.TemporaryDirectory(prefix='chordlens-real-world-') as temp:
            downloaded, title, artist = download_audio(args.url, temp, notices=notices)
            normalize_audio(downloaded, audio)
    else:
        normalize_audio(args.audio.resolve(), audio)
        title = args.audio.stem
    duration = sf.info(audio).duration
    report = {'schema_version': 1, 'purpose': 'development_diagnostic_not_heldout_test',
              'title': title, 'artist_metadata_unverified': artist, 'source_url': args.url,
              'audio_sha256': file_digest(audio), 'checkpoint_sha256': checkpoint_hash,
              'source_checkpoint': str(source_checkpoint), 'config': loaded[1].to_dict(),
              'duration_seconds': duration, 'warnings': notices, 'results': {}, 'summary': {},
              'ambiguities': {}, 'failures': [], 'code_fingerprints': before,
              'accuracy_available': False, 'reference_status': 'missing_human_timed_annotations'}
    print(f'Experimento: {folder}', flush=True)
    inputs = [('current', audio), ('neural', audio)]
    if args.compare_hpss:
        print('Preparando variante HPSS (reduce percusión; no separa voz)...', flush=True)
        started = perf_counter()
        hpss_audio(audio, folder / 'harmonic.wav', loaded[1].features.sample_rate)
        report['hpss_seconds'] = perf_counter() - started
        report['hpss_audio_sha256'] = file_digest(folder / 'harmonic.wav')
        inputs.append(('neural_hpss', folder / 'harmonic.wav'))
    for name, path in inputs:
        print(f'Analizando {name}...', flush=True)
        try:
            if name == 'current':
                result = _analyze_audio(str(path), title=title, max_duration=None)
            else:
                result = analyze_neural(str(path), checkpoint, title=title, mode='accurate',
                                        loaded_model=loaded, allow_experimental=True,
                                        diagnostics_path=folder / f'{name}.npz')
            if not result.get('success'):
                raise ValueError(result.get('error', 'Análisis fallido'))
            # The neural path calls analyze_neural directly: fallback cannot hide failure.
            write_json(folder / f'{name}.json', result)
            report['results'][name] = result
            report['summary'][name] = summarize(result)
            if name != 'current':
                report['ambiguities'][name] = alternatives(result, folder / f'{name}.npz')
        except Exception as exc:
            report['failures'].append({'engine': name, 'error': f'{type(exc).__name__}: {exc}'})
    report['code_unchanged_during_run'] = before == code_fingerprints()
    report['complete'] = not report['failures'] and report['code_unchanged_during_run']
    # No model-predicted chord or boundary is written as reference truth.
    (folder / 'reference.lab').write_text(f'# Sin revisar: X significa desconocido, no silencio.\n0.000000 {duration:.9f} X\n')
    write_json(folder / 'report.json', report)
    render_review(folder, report)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    print(f'Revisión: {folder / "review.html"}\nPrecisión: pendiente de referencia humana con tiempos.')
    if not report['complete']:
        raise ValueError(f'Experimento incompleto: {report["failures"]}; código estable={report["code_unchanged_during_run"]}')


def read_reference(path, duration):
    from backend.model.dataset import read_annotations
    rows = read_annotations({'annotation': str(path), 'format': 'lab'})
    if any(end > duration + 1e-5 for _, end, _ in rows):
        raise ValueError('La referencia excede la duración del audio; comprueba versión y desplazamiento')
    for _, _, symbol in rows:
        label = parse_label(symbol)
        if symbol not in ('X', 'N') and label.root < 0:
            raise ValueError(f'Etiqueta inválida: {symbol}; usa X si el tramo no está revisado')
    if not any(parse_label(symbol).state >= 0 for _, _, symbol in rows):
        raise ValueError('No hay acordes revisados evaluables. No se calculará precisión a partir de X.')
    return rows


def triads(intervals):
    result = []
    for start, end, symbol in intervals:
        label = parse_label(symbol)
        if label.quality in (2, 3, 4):
            quality = 1 if label.quality == 4 else 0
            symbol = state_name(label.root * len(QUALITIES) + quality,
                                label.bass if label.bass >= 0 else None)
        result.append((start, end, symbol))
    return result


def extension_errors(reference, estimated, duration):
    """Exact duration of added/missed sevenths, conditional on the SAME base triad."""
    import numpy as np
    from backend.model.metrics import sample
    edges = np.unique(np.clip([0, duration] + [v for row in reference + estimated for v in row[:2]], 0, duration))
    times, weights = (edges[1:] + edges[:-1]) / 2, np.diff(edges)
    a, b = sample(reference, times), sample(estimated, times)
    added = missed = triad_seconds = seventh_seconds = 0.0
    family = {0: 0, 1: 1, 2: 0, 3: 0, 4: 1}
    for ref, pred, length in zip(a, b, weights):
        r, p = parse_label(ref), parse_label(pred)
        if r.quality in (0, 1):
            triad_seconds += length
        elif r.quality in (2, 3, 4):
            seventh_seconds += length
        if (r.root != p.root or r.quality not in family or p.quality not in family
                or family[r.quality] != family[p.quality]):
            continue
        if r.quality in (0, 1) and p.quality in (2, 3, 4):
            added += length
        if r.quality in (2, 3, 4) and p.quality in (0, 1):
            missed += length
    return {'added_sevenths_same_triad_seconds': float(added),
            'missed_sevenths_same_triad_seconds': float(missed),
            'reference_triad_seconds': float(triad_seconds),
            'reference_seventh_seconds': float(seventh_seconds)}


def score(args):
    folder = args.run.resolve()
    report = json.loads((folder / 'report.json').read_text())
    if not report.get('complete'):
        raise ValueError('No se puntúa una ejecución incompleta o con código cambiado durante el análisis')
    if file_digest(folder / 'audio.wav') != report['audio_sha256']:
        raise ValueError('El audio cambió desde el análisis')
    duration = report['duration_seconds']
    reference = read_reference(args.reference, duration)
    reference_sha = file_digest(args.reference)
    scored_reference = triads(reference) if args.reference_kind == 'simplified' else reference
    output = {'purpose': 'development_single_song_not_general_accuracy',
              'audio_sha256': report['audio_sha256'], 'checkpoint_sha256': report['checkpoint_sha256'],
              'reference_sha256': reference_sha, 'reference_kind': args.reference_kind,
              'evaluation_vocabulary': 'triads' if args.reference_kind == 'simplified' else 'full',
              'report_sha256': file_digest(folder / 'report.json'), 'results': {}}
    for name, result in report['results'].items():
        estimated = intervals_from_timeline(result['chords_timeline'], duration)
        scored_estimated = triads(estimated) if args.reference_kind == 'simplified' else estimated
        metrics = aggregate([score_song(scored_reference, scored_estimated, duration)])
        metrics['seventh_errors'] = (extension_errors(reference, estimated, duration)
                                    if args.reference_kind == 'exact' else
                                    {'unavailable': 'Una referencia simplificada no certifica séptimas falsas.'})
        output['results'][name] = metrics
    target = folder / f'scores-{reference_sha[:12]}-{args.reference_kind}.json'
    write_json(target, output)
    # Preserve the exact human reference with the scores, without overwriting anything.
    reference_target = folder / f'reviewed-{reference_sha[:12]}.lab'
    if not reference_target.exists():
        with reference_target.open('xb') as stream:
            stream.write(args.reference.read_bytes())
    for name, metrics in output['results'].items():
        print(f'{name}: WCSR={metrics["weighted_chord_accuracy"]:.2%}; '
              f'cobertura={metrics["vocabulary_coverage"]:.2%}; cambios F1={metrics["changes"]["f1"]:.3f}')
    print(f'Informe: {target}\nEstos resultados describen esta referencia, no canciones nuevas.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('analyze', help='Descargar/analizar y preparar revisión sin inventar métricas')
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument('--url')
    source.add_argument('--audio', type=Path)
    run.add_argument('--checkpoint', type=Path, required=True)
    run.add_argument('--output', type=Path, help='Directorio nuevo; nunca se sobrescribe')
    run.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='cpu')
    run.add_argument('--compare-hpss', action='store_true')
    run.set_defaults(function=analyze)
    scoring = sub.add_parser('score', help='Comparar con una referencia humana alineada')
    scoring.add_argument('--run', type=Path, required=True)
    scoring.add_argument('--reference', type=Path, required=True)
    scoring.add_argument('--reference-kind', choices=('exact', 'simplified'), required=True)
    scoring.set_defaults(function=score)
    args = parser.parse_args()
    try:
        args.function(args)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__':
    main()

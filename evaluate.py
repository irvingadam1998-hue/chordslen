#!/usr/bin/env python3
"""Compare actual baseline vs actual NN on the same songs; never substitute fallback."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
from backend.model.dataset import load_manifest, read_annotations
from backend.model.features import file_digest
from backend.model.metrics import score_song, aggregate, intervals_from_timeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/manifest.jsonl'))
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--split', choices=('validation', 'test'), default='test')
    parser.add_argument('--output', type=Path, default=Path('experiments/evaluation.json'))
    parser.add_argument('--mode', choices=('fast', 'accurate'), default='accurate')
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    parser.add_argument('--boundary-tolerance', type=float, default=0.25)
    parser.add_argument('--frame-seconds', type=float, default=0.02)
    parser.add_argument('--no-viterbi', action='store_true')
    parser.add_argument('--vocabulary', choices=('full', 'triads'),
                        help='Sustituye decode.vocabulary del checkpoint (triads: séptimas a tríadas)')
    parser.add_argument('--key-prior-weight', type=float,
                        help='Sustituye decode.key_prior_weight: preferencia por los acordes de la tonalidad')
    parser.add_argument('--key-source', choices=('chords', 'spectrum'),
                        help='Sustituye decode.key_source del checkpoint')
    parser.add_argument('--switch-cost', type=float,
                        help='Sustituye decode.switch_cost del checkpoint; ajústalo en validation, nunca en test')
    args = parser.parse_args()
    if args.frame_seconds <= 0 or args.boundary_tolerance < 0:
        parser.error('Los parámetros temporales deben ser positivos')
    if args.switch_cost is not None and args.switch_cost < 0:
        parser.error('--switch-cost debe ser no negativo')
    if not args.manifest.is_file():
        print('Métricas no disponibles: falta el manifiesto con audio y anotaciones. Consulta ACR_GUIDE.md.')
        return
    rows = load_manifest(args.manifest)
    selected = [r for r in rows if r['split'] == args.split]
    if not selected:
        parser.error(f'No hay canciones en {args.split}')
    loaded, neural_error = None, 'No se indicó un checkpoint entrenado'
    if args.checkpoint:
        try:
            from backend.model.inference import load_model
            loaded = load_model(args.checkpoint, args.device, allow_experimental=True)
        except Exception as exc:
            neural_error = f'{type(exc).__name__}: {exc}'
    if loaded and args.switch_cost is not None:
        # Only this process: the checkpoint file keeps its trained decode settings.
        loaded[1].decode.switch_cost = args.switch_cost
    if loaded and args.vocabulary:
        loaded[1].decode.vocabulary = args.vocabulary
    if loaded and args.key_source:
        loaded[1].decode.key_source = args.key_source
    if loaded and args.key_prior_weight is not None:
        if args.key_prior_weight < 0:
            parser.error('--key-prior-weight debe ser no negativo')
        loaded[1].decode.key_prior_weight = args.key_prior_weight
    if loaded:
        provenance = loaded[4]['provenance']
        # Validation can be reused for model selection; test must be wholly unseen.
        previous = provenance if args.split == 'test' else [r for r in provenance if r['split'] == 'train']
        for row in selected:
            digest = file_digest(row['audio'])
            if any(row['artist_id'] == old['artist_id'] or row['origin_id'] == old['origin_id']
                   or digest == old['audio_sha256'] for old in previous):
                parser.error(f'Leakage contra el checkpoint: {row["id"]}')
    from backend.scripts.analyze import _analyze_audio
    import soundfile as sf
    report = {'schema_version': 1, 'split': args.split, 'manifest_sha256': file_digest(args.manifest),
              'checkpoint_sha256': file_digest(args.checkpoint) if loaded else None,
              'config': loaded[1].to_dict() if loaded else None, 'mode': args.mode,
              'viterbi': not args.no_viterbi, 'frame_seconds': args.frame_seconds,
              'boundary_tolerance': args.boundary_tolerance, 'songs': [], 'failures': []}
    scores = {'current': [], 'neural': []}
    for row in selected:
        print(f'Evaluando {row["id"]}...', flush=True)
        reference = read_annotations(row)
        # Both engines receive the entire identical file. No legacy six-minute truncation.
        duration = sf.info(row['audio']).duration
        record = {'id': row['id'], 'audio_sha256': file_digest(row['audio']),
                  'annotation_sha256': file_digest(row['annotation'])}
        results = {}
        try:
            started = perf_counter()
            results['current'] = _analyze_audio(row['audio'], max_duration=None)
            record['current_seconds'] = perf_counter() - started
            if not results['current'].get('success'):
                raise ValueError(results['current'].get('error'))
            if loaded:
                from backend.model.inference import analyze_neural
                started = perf_counter()
                results['neural'] = analyze_neural(row['audio'], args.checkpoint, mode=args.mode,
                                                   device=args.device, allow_experimental=True,
                                                   smooth=not args.no_viterbi, loaded_model=loaded)
                record['neural_seconds'] = perf_counter() - started
            # Only aggregate paired successes when comparing two models.
            paired_scores = {}
            for engine, result in results.items():
                score = score_song(reference, intervals_from_timeline(result['chords_timeline'], duration),
                                   duration, args.frame_seconds, args.boundary_tolerance,
                                   implicit_bass=row.get('implicit_bass', False))
                record[engine] = aggregate([score])
                paired_scores[engine] = score
            for engine, score in paired_scores.items():
                scores[engine].append(score)
        except Exception as exc:
            report['failures'].append({'id': row['id'], 'error': f'{type(exc).__name__}: {exc}'})
            continue
        report['songs'].append(record)
    report['current'] = aggregate(scores['current'])
    report['neural'] = aggregate(scores['neural']) if loaded else {'available': False, 'reason': neural_error}
    report['complete'] = not report['failures'] and len(report['songs']) == len(selected)
    if loaded and report['checkpoint_sha256'] != file_digest(args.checkpoint):
        report['complete'] = False
        report['failures'].append({'id': 'checkpoint', 'error': 'El archivo de pesos cambió durante la evaluación; repite con un checkpoint inmutable.'})
    if loaded and scores['neural']:
        report['paired_song_delta'] = [{'id': r['id'], 'delta': r['neural']['weighted_chord_accuracy'] - r['current']['weighted_chord_accuracy']}
                                       for r in report['songs'] if r['neural']['weighted_chord_accuracy'] is not None
                                       and r['current']['weighted_chord_accuracy'] is not None]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False))
    for engine in ('current', 'neural'):
        result = report[engine]
        print(f'\n{engine.title()} system:')
        if not result['available']:
            print('  Métricas no disponibles:', result.get('reason', 'sin canciones'))
            continue
        for metric in ('weighted_chord_accuracy', 'frame_accuracy', 'root_accuracy', 'quality_accuracy', 'vocabulary_coverage'):
            value = result[metric]
            print(f'  {metric}: {value:.2%}' if value is not None else f'  {metric}: no disponible')
        print('  cambios F1:', round(result['changes']['f1'], 4))
        print('  confusiones:', result['chords']['top_confusions'][:5])
    print(f'\nInforme: {args.output}; fallos: {len(report["failures"])}')
    if report['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

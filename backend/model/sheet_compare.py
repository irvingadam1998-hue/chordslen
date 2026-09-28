"""Compare engines with a chord sheet: which chords and in what order, without timings.

A sheet has no timings, so this is not WCSR. It reports, per engine:
- in_sheet: share of chord time whose triad appears in the sheet;
- exact: the same with sevenths kept (Am7 != Am);
- order: similarity of the chord order with the sheet (compare engines, not songs);
- invented: triads absent from the sheet, with their seconds.
"""
import argparse
from collections import Counter
import difflib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from .labels import NOTES, QUALITIES, SUFFIX, parse_label

TRIAD = {'7': 'maj', 'maj7': 'maj', 'm7': 'min'}
# Sheet spellings outside the model vocabulary, reduced to their triad.
REDUCED = ((re.compile(r'^([A-G][#b]?)m7b5$'), 'dim'), (re.compile(r'^([A-G][#b]?)m(?:Maj|maj)7$'), 'm'))


def _reduce(name):
    name = name.split('/')[0]
    for pattern, suffix in REDUCED:
        match = pattern.match(name)
        if match:
            return match[1] + suffix, True
    return name, False


def triad(name):
    name, _ = _reduce(name)
    label = parse_label(name)
    if label.presence != 1 or label.root < 0 or label.quality < 0:
        return None
    quality = TRIAD.get(QUALITIES[label.quality], QUALITIES[label.quality])
    return NOTES[label.root] + SUFFIX[QUALITIES.index(quality)]


def exact(name):
    name, reduced = _reduce(name)
    state = parse_label(name).state
    return None if reduced or state < 0 else state


def merge(sequence):
    return [c for i, c in enumerate(sequence) if c and (i == 0 or c != sequence[i - 1])]


def with_ends(timeline, duration):
    # The classic detector only reports start times; each chord lasts until the next.
    return [{**e, 'end': e.get('end', timeline[i + 1]['time'] if i + 1 < len(timeline) else duration)}
            for i, e in enumerate(timeline)]


def score(timeline, chords, min_seconds=1.0):
    sheet_triads = {triad(c) for c in chords}
    sheet_exact = {exact(c) for c in chords} - {None}
    total = in_triad = in_exact = 0.0
    invented, kept = Counter(), []
    for event in timeline:
        seconds, name = event['end'] - event['time'], triad(event['chord'])
        if name is None or seconds <= 0:
            continue
        total += seconds
        if name in sheet_triads:
            in_triad += seconds
        else:
            invented[name] += seconds
        if exact(event['chord']) in sheet_exact:
            in_exact += seconds
        if seconds >= min_seconds:
            kept.append(name)
    order = difflib.SequenceMatcher(None, merge(kept), merge([triad(c) for c in chords]), autojunk=False).ratio()
    return {'in_sheet': in_triad / total if total else 0, 'exact': in_exact / total if total else 0,
            'order': order, 'invented': [(k, round(v, 1)) for k, v in invented.most_common(3)]}


def ensure_audio(song, entry, cache):
    target = cache / f'{song}.wav'
    if not target.is_file():
        root = str(Path(__file__).resolve().parents[1] / 'scripts')
        if root not in sys.path:
            sys.path.insert(0, root)
        from youtube import download_audio
        with tempfile.TemporaryDirectory() as work:
            path, _, _ = download_audio(entry['url'], work)
            cache.mkdir(parents=True, exist_ok=True)
            shutil.move(path, target)
    return target


def analyze(audio, checkpoint, vocabulary, switch_cost):
    if checkpoint is None:
        from ..scripts.analyze import _analyze_audio
        return _analyze_audio(str(audio))
    from .inference import analyze_neural, load_model
    loaded = load_model(checkpoint, allow_experimental=True)
    if switch_cost is not None:
        loaded[1].decode.switch_cost = switch_cost
    result = analyze_neural(str(audio), checkpoint, mode='accurate', loaded_model=loaded,
                            vocabulary=vocabulary, allow_experimental=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sheets', type=Path, default=Path('data/real/sheets.json'))
    parser.add_argument('--cache', type=Path, default=Path('data/real/youtube'))
    parser.add_argument('--checkpoint', action='append', default=[], metavar='NOMBRE=RUTA',
                        help='Modelo a comparar; repetible. El detector clásico siempre se incluye.')
    parser.add_argument('--vocabulary', choices=('full', 'triads'), default='triads')
    parser.add_argument('--switch-cost', type=float, help='Mismo decodificador para todos los modelos')
    parser.add_argument('--output', type=Path, default=Path('experiments/sheet-compare.json'))
    args = parser.parse_args()
    import soundfile
    sheets = json.loads(args.sheets.read_text())
    engines = [('clásico', None)] + [tuple(item.split('=', 1)) for item in args.checkpoint]
    report = {}
    for song, entry in sheets.items():
        audio = ensure_audio(song, entry, args.cache)
        chords = entry['chords'].split()
        report[song] = {}
        print(f'\n{entry.get("title", song)} (cancionero: {entry.get("key", "?")})')
        print(f'  {"motor":28} {"en cancionero":>14} {"exacto":>8} {"orden":>6}  tonalidad        inventados')
        for name, checkpoint in engines:
            result = analyze(audio, checkpoint, args.vocabulary, args.switch_cost)
            if not result.get('success') or (checkpoint and result.get('engine') != 'neural'):
                raise SystemExit(f'{name}: el análisis falló o no usó la red: {result.get("error") or result.get("warnings")}')
            row = score(with_ends(result['chords_timeline'], soundfile.info(audio).duration), chords)
            row['key'] = result.get('key', '')
            report[song][name] = row
            print(f'  {name:28} {row["in_sheet"]:>13.1%} {row["exact"]:>8.1%} {row["order"]:>6.2f}  '
                  f'{row["key"]:15}  {row["invented"]}', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f'\nInforme: {args.output}')


if __name__ == '__main__':
    main()

"""Full-mix training data: public chord annotations paired with audio the user owns.

catalog: normalizes Isophonics and Billboard annotations into <artist>/<title>.lab
         and lists the songs whose audio is needed.
match:   pairs the user's audio files with those annotations, estimates the offset
         between the user's release and the annotated one, and writes shifted LAB.
The result feeds `prepare --lab-annotations/--lab-audio`.
"""
import argparse
import csv
import difflib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import numpy as np
from .labels import INTERVALS, parse_label

AUDIO_EXTENSIONS = ('.wav', '.flac', '.mp3', '.ogg', '.m4a')
CATALOG_FIELDS = ('dataset', 'artist', 'title', 'album', 'duration_seconds', 'lab')
ALIGN_HOP_SECONDS = 2048 / 22050


def normalize(text):
    """Comparable key: no accents, remaster/live suffixes, punctuation or leading 'the'."""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower()
    text = re.sub(r'[\(\[][^\)\]]*[\)\]]', ' ', text)
    text = re.sub(r'\s-\s.*(remaster|live|version|mono|stereo|edit|mix).*$', ' ', text)
    text = text.replace('&', ' and ')
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    return re.sub(r'^the\s+', '', text)


def clean_title(stem):
    # "01_-_I_Saw_Her_Standing_There", "CD1_-_05_-_Help", "04 I Want It All" -> title.
    stem = re.sub(r'^(CD\d+[\s_]*-?[\s_]*)?\d+[\s_.]*(-[\s_]*)?', '', stem)
    return re.sub(r'\s+', ' ', stem.replace('_', ' ')).strip()


def safe_name(text):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', text).strip(' .') or 'sin-nombre'


def lab_duration(path):
    lines = [line.split() for line in Path(path).read_text().splitlines() if line.strip()]
    return float(lines[-1][1]) if lines else 0.0


def isophonics_entries(root):
    for chordlab in sorted(Path(root).glob('isophonics-*/chordlab')):
        for lab in sorted(chordlab.rglob('*.lab')):
            parts = lab.relative_to(chordlab).parts
            yield {'dataset': 'Isophonics', 'artist': parts[0], 'title': clean_title(lab.stem),
                   'album': clean_title(parts[1]) if len(parts) > 2 else '', 'source': lab}


def billboard_entries(root):
    index = Path(root) / 'raw' / 'billboard-2.0-index.csv'
    labs = Path(root) / 'billboard-2.0.1-lab' / 'McGill-Billboard'
    if not index.is_file() or not labs.is_dir():
        return
    with index.open(newline='') as stream:
        for row in csv.DictReader(stream):
            lab = labs / f'{int(row["id"]):04d}' / 'majmin7inv.lab'
            if row['title'] and lab.is_file():
                yield {'dataset': 'Billboard', 'artist': row['artist'], 'title': row['title'],
                       'album': '', 'source': lab}


def catalog(root, output):
    """Isophonics first: when a song is in both corpora, its hand-checked LAB wins."""
    root, output = Path(root), Path(output)
    seen, rows = set(), []
    for entry in (*isophonics_entries(root), *billboard_entries(root)):
        key = (normalize(entry['artist']), normalize(entry['title']))
        if key in seen:
            continue
        seen.add(key)
        target = output / safe_name(entry['artist']) / (safe_name(entry['title']) + '.lab')
        target.parent.mkdir(parents=True, exist_ok=True)
        # Billboard LAB is tab separated; the LAB reader splits on any whitespace.
        target.write_text(entry['source'].read_text())
        rows.append({'dataset': entry['dataset'], 'artist': entry['artist'], 'title': entry['title'],
                     'album': entry['album'], 'duration_seconds': round(lab_duration(target), 1),
                     'lab': str(target)})
    listing = output / 'catalog.csv'
    with listing.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows, listing


def audio_metadata(path):
    """ffprobe tags; falls back to 'Artist - Title' file names or <artist>/<title> folders."""
    tags = {}
    try:
        result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
                                capture_output=True, text=True, timeout=30, check=False)
        info = json.loads(result.stdout or '{}').get('format', {})
        tags = {k.lower(): v for k, v in info.get('tags', {}).items()}
        duration = float(info.get('duration', 0) or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        duration = 0.0
    artist, title = tags.get('artist') or tags.get('album_artist'), tags.get('title')
    if not (artist and title):
        stem = re.sub(r'^\d+[\s_.-]+', '', Path(path).stem)
        if ' - ' in stem:
            artist, title = (part.strip() for part in stem.split(' - ', 1))
        else:
            artist, title = Path(path).parent.name, stem
    return artist, title, duration


def find_entry(artist, title, entries, cutoff=0.85):
    by_artist = [e for e in entries if e['artist_key'] == normalize(artist)]
    exact = [e for e in by_artist if e['title_key'] == normalize(title)]
    if exact:
        return exact[0]
    titles = [e['title_key'] for e in by_artist]
    close = difflib.get_close_matches(normalize(title), titles, n=1, cutoff=cutoff)
    return by_artist[titles.index(close[0])] if close else None


def label_chroma(intervals, frames, hop):
    """Binary pitch-class template per frame; unknown and silent frames stay empty."""
    template = np.zeros((12, frames), dtype=np.float32)
    for start, end, symbol in intervals:
        label = parse_label(symbol)
        if label.presence != 1 or label.root < 0 or label.quality < 0:
            continue
        first, last = int(round(start / hop)), int(round(end / hop))
        for interval in INTERVALS[label.quality]:
            template[(label.root + interval) % 12, max(0, first):max(0, last)] = 1
    return template


def estimate_offset(chroma, template, max_lag_frames):
    """Lag L (frames) maximizing the cosine of audio(t) and labels(t - L)."""
    audio = chroma / np.maximum(np.linalg.norm(chroma, axis=0, keepdims=True), 1e-6)
    labels = template / np.maximum(np.linalg.norm(template, axis=0, keepdims=True), 1e-6)
    scores = {}
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        a = audio[:, max(0, lag):]
        b = labels[:, max(0, -lag):]
        n = min(a.shape[1], b.shape[1])
        active = b[:, :n].any(axis=0)
        if active.sum() < 50:
            continue
        scores[lag] = float((a[:, :n] * b[:, :n]).sum(axis=0)[active].mean())
    if not scores:
        return 0, 0.0, 0.0
    best = max(scores, key=scores.get)
    return best, scores[best], scores[best] - float(np.median(list(scores.values())))


def read_lab(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) == 3:
            rows.append((float(parts[0]), float(parts[1]), parts[2].strip()))
    return rows


def shift_lab(intervals, offset, duration):
    shifted = []
    for start, end, symbol in intervals:
        start, end = max(0.0, start + offset), min(duration, end + offset)
        if end - start > 1e-3:
            shifted.append((start, end, symbol))
    return shifted


def match(catalog_csv, audio_dir, output, max_offset=15.0, min_score=0.45, min_margin=0.05):
    import librosa
    output = Path(output)
    with open(catalog_csv, newline='') as stream:
        entries = list(csv.DictReader(stream))
    for entry in entries:
        entry['artist_key'], entry['title_key'] = normalize(entry['artist']), normalize(entry['title'])
    report, used = [], set()
    files = sorted(p for p in Path(audio_dir).rglob('*') if p.suffix.lower() in AUDIO_EXTENSIONS)
    for number, path in enumerate(files, 1):
        artist, title, _ = audio_metadata(path)
        entry = find_entry(artist, title, entries)
        row = {'audio': str(path), 'artist': artist, 'title': title, 'status': 'sin_anotacion',
               'offset_seconds': '', 'score': '', 'margin': '', 'missing_chord_seconds': ''}
        print(f'[{number}/{len(files)}] {artist} - {title}', flush=True)
        if entry is None:
            report.append(row)
            continue
        key = (entry['artist_key'], entry['title_key'])
        row.update(artist=entry['artist'], title=entry['title'])
        if key in used:
            row['status'] = 'duplicado'
            report.append(row)
            continue
        y, sr = librosa.load(path, sr=22050, mono=True)
        duration = len(y) / sr
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048)
        intervals = read_lab(entry['lab'])
        template = label_chroma(intervals, chroma.shape[1], ALIGN_HOP_SECONDS)
        lag, score, margin = estimate_offset(chroma, template, int(max_offset / ALIGN_HOP_SECONDS))
        offset = lag * ALIGN_HOP_SECONDS
        row.update(offset_seconds=round(offset, 2), score=round(score, 3), margin=round(margin, 3))
        annotated_end = intervals[-1][1] + offset if intervals else 0
        # Releases cut the trailing silence or fade differently; only missing chords matter.
        missing_chords = sum(min(end + offset, annotated_end) - max(start + offset, duration)
                             for start, end, symbol in intervals
                             if end + offset > duration and symbol not in ('N', 'X'))
        row['missing_chord_seconds'] = round(missing_chords, 1)
        if score < min_score or margin < min_margin:
            # A flat score curve means the recording does not follow these chords.
            row['status'] = 'no_coincide'
        elif missing_chords > 5.0 or annotated_end < duration - 15.0:
            row['status'] = 'otra_version'
        else:
            row['status'] = 'ok'
            used.add(key)
            folder = safe_name(entry['artist'])
            name = safe_name(entry['title'])
            (output / 'labs' / folder).mkdir(parents=True, exist_ok=True)
            (output / 'audio' / folder).mkdir(parents=True, exist_ok=True)
            (output / 'labs' / folder / f'{name}.lab').write_text(''.join(
                f'{start:.4f} {end:.4f} {symbol}\n' for start, end, symbol in shift_lab(intervals, offset, duration)))
            link = output / 'audio' / folder / (name + path.suffix.lower())
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(path.resolve())
        report.append(row)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'match_report.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, list(report[0]) if report else ['audio'])
        writer.writeheader()
        writer.writerows(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('catalog', help='Normaliza anotaciones y lista las canciones necesarias')
    make.add_argument('--annotations', type=Path, default=Path('data/annotations'))
    make.add_argument('--output', type=Path, default=Path('data/real/catalog'))
    pair = commands.add_parser('match', help='Empareja tu audio con el catálogo y corrige el desfase')
    pair.add_argument('--catalog', type=Path, default=Path('data/real/catalog/catalog.csv'))
    pair.add_argument('--audio', type=Path, required=True, help='Carpeta con tu música (se busca recursivamente)')
    pair.add_argument('--output', type=Path, default=Path('data/real/matched'))
    pair.add_argument('--max-offset', type=float, default=15.0, help='Desfase máximo a buscar, en segundos')
    pair.add_argument('--min-score', type=float, default=0.45)
    pair.add_argument('--min-margin', type=float, default=0.05)
    args = parser.parse_args()
    if args.command == 'catalog':
        rows, listing = catalog(args.annotations, args.output)
        counts = {}
        for row in rows:
            counts[row['dataset']] = counts.get(row['dataset'], 0) + 1
        print(json.dumps({'canciones': len(rows), **counts, 'lista': str(listing)}, indent=2))
    else:
        report = match(args.catalog, args.audio, args.output, args.max_offset, args.min_score, args.min_margin)
        summary = {}
        for row in report:
            summary[row['status']] = summary.get(row['status'], 0) + 1
        print(json.dumps({**summary, 'informe': str(args.output / 'match_report.csv')}, indent=2))


if __name__ == '__main__':
    main()

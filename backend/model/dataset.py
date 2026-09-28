"""Manifests and annotations first; split whole recordings before making segments."""
import json
from pathlib import Path
import numpy as np
from .labels import IGNORE, parse_label
from .features import cached_features, file_digest


def load_manifest(path, check_files=True):
    path = Path(path).resolve()
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    required = {'id', 'audio', 'annotation', 'format', 'artist_id', 'origin_id', 'split'}
    ids = set()
    for row in rows:
        if not required <= row.keys() or any(not row.get(k) for k in required):
            raise ValueError(f'Manifiesto incompleto: requiere {sorted(required)}')
        if row['id'] in ids:
            raise ValueError(f'ID duplicado: {row["id"]}')
        ids.add(row['id'])
        if row['split'] not in {'train', 'validation', 'test', 'excluded'}:
            raise ValueError(f'Split inválido: {row["split"]}')
        if row['format'] not in {'lab', 'guitarset_jams'}:
            raise ValueError('Formato no implementado: conviértelo explícitamente a LAB')
        for key in ('audio', 'annotation'):
            row[key] = str((path.parent / row[key]).resolve())
            if check_files and row['split'] != 'excluded' and not Path(row[key]).is_file():
                raise FileNotFoundError(row[key])
    assert_no_leakage(rows, check_audio=check_files)
    return rows


def assert_no_leakage(rows, check_audio=False):
    owners = {}
    for row in rows:
        if row['split'] == 'excluded':
            continue
        fields = [(key, row[key]) for key in ('artist_id', 'origin_id')]
        if check_audio:
            fields.append(('audio_sha256', file_digest(row['audio'])))
        for key in fields:
            previous = owners.setdefault(key, row['split'])
            if previous != row['split']:
                raise ValueError(f'Data leakage: {key} aparece en {previous} y {row["split"]}')


def read_annotations(row):
    path = Path(row['annotation'])
    if row['format'] == 'lab':
        intervals = []
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            parts = line.split(maxsplit=2)
            if len(parts) != 3:
                raise ValueError(f'LAB requiere inicio fin acorde: {path}')
            intervals.append((float(parts[0]), float(parts[1]), parts[2].strip()))
    elif row['format'] == 'guitarset_jams':
        content = json.loads(path.read_text())
        annotations = [a for a in content['annotations'] if a['namespace'] == 'chord']
        performed = [a for a in annotations if 'string note transcriptions' in
                     str(a.get('annotation_metadata', {}).get('annotation_rules', ''))]
        if len(performed) != 1:
            raise ValueError(f'No se pudo identificar la anotación ejecutada: {path}')
        intervals = [(float(d['time']), float(d['time'] + d['duration']), d['value'])
                     for d in performed[0]['data']]
    else:
        raise ValueError(f'Formato no soportado: {row["format"]}')
    previous = 0.0
    for start, end, label in intervals:
        if not np.isfinite([start, end]).all() or start < -1e-6 or end <= start or start < previous - 1e-5:
            raise ValueError(f'Intervalos inválidos, desordenados o solapados: {path}')
        previous = end
    return intervals


def align_labels(intervals, times, implicit_bass=False):
    labels = np.full((len(times), 4), IGNORE, dtype=np.int64)
    for start, end, symbol in intervals:
        chord = parse_label(symbol, implicit_bass=implicit_bass)
        first, last = np.searchsorted(times, [start, end], side='left')
        labels[first:last] = (chord.root, chord.quality, chord.presence, chord.bass)
    return labels


def prepare_tracks(rows, cfg, cache_dir):
    tracks = []
    for i, row in enumerate(rows):
        if row['split'] == 'excluded':
            continue
        print(f'features {i + 1}/{len(rows)}: {row["id"]}', flush=True)
        features, duration = cached_features(row['audio'], cfg, cache_dir, mmap=True)
        intervals = read_annotations(row)
        if intervals and intervals[-1][1] > duration + 0.25:
            raise ValueError(f'Anotación excede audio en {row["id"]}; comprueba la edición/offset')
        times = np.arange(features.shape[-1]) * cfg.hop_length / cfg.sample_rate
        labels = align_labels(intervals, times, row.get('implicit_bass', False))
        tracks.append({'row': row, 'features': features, 'labels': labels, 'duration': duration})
    return tracks


def training_statistics(tracks):
    selected = [t for t in tracks if t['row']['split'] == 'train']
    if not selected:
        raise ValueError('No hay canciones de entrenamiento')
    count = sum(t['features'].shape[1] for t in selected)
    total = sum(t['features'].astype(np.float64).sum(axis=1) for t in selected)
    squares = sum((t['features'].astype(np.float64) ** 2).sum(axis=1) for t in selected)
    mean = total / count
    std = np.sqrt(np.maximum(squares / count - mean ** 2, 1e-4))
    return mean.astype(np.float32), std.astype(np.float32)


def transpose_segment(x, y, semitones, cfg):
    """Shift raw features and root/bass labels together; vacated CQT bins become silence."""
    if not semitones:
        return x, y
    x, y = x.copy(), y.copy()
    if cfg.representation == 'cqt':
        main = cfg.bins_per_octave * cfg.octaves
        shift = semitones * (cfg.bins_per_octave // 12)
        x[:main] = np.roll(x[:main], shift, axis=0)
        if shift > 0:
            x[:shift] = 0
        else:
            x[main + shift:main] = 0
    elif cfg.representation == 'chroma':
        main = 12
        x[:main] = np.roll(x[:main], semitones, axis=0)
    else:
        raise ValueError('La transposición solo admite cqt o chroma')
    # Chroma and bass branches are pitch classes, so they rotate circularly.
    offset = main
    for enabled in (cfg.chroma, cfg.bass):
        if enabled:
            x[offset:offset + 12] = np.roll(x[offset:offset + 12], semitones, axis=0)
            offset += 12
    for column in (0, 3):
        valid = y[:, column] >= 0
        y[valid, column] = (y[valid, column] + semitones) % 12
    return x, y


class ChordDataset:
    """Map-style PyTorch Dataset protocol; lazy torch import keeps fallback light."""
    def __init__(self, tracks, split, frames, mean, std, features=None, pitch_shift=0):
        self.tracks = [t for t in tracks if t['row']['split'] == split]
        self.frames, self.mean, self.std = frames, mean, std
        if pitch_shift and features is None:
            raise ValueError('pitch_shift requiere la configuración de features')
        self.features_cfg, self.pitch_shift = features, pitch_shift
        self.segments = []
        for i, track in enumerate(self.tracks):
            for start in range(0, track['features'].shape[-1], frames):
                if (track['labels'][start:start + frames, 2] != IGNORE).any():
                    self.segments.append((i, start))
        if not self.segments:
            raise ValueError(f'No hay segmentos con supervisión en {split}')

    def __len__(self):
        return len(self.segments)

    def __getitem__(self, index):
        import torch
        track_idx, start = self.segments[index]
        track = self.tracks[track_idx]
        x = track['features'][:, start:start + self.frames]
        y = track['labels'][start:start + self.frames]
        if self.pitch_shift:
            # torch RNG: seeded per DataLoader worker and restored on --resume.
            semitones = int(torch.randint(-self.pitch_shift, self.pitch_shift + 1, ()))
            x, y = transpose_segment(x, y, semitones, self.features_cfg)
        x = (x - self.mean[:, None]) / self.std[:, None]
        length = len(y)
        x = np.pad(x, ((0, 0), (0, self.frames - length)))
        y = np.pad(y, ((0, self.frames - length), (0, 0)), constant_values=IGNORE)
        return torch.from_numpy(x.copy()), torch.from_numpy(y.copy()), length

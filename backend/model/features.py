"""Bounded spectral blocks on a common frame grid; no annotation-dependent DSP."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
from .config import fingerprint

FEATURE_VERSION = 1


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _block_features(y, cfg):
    import librosa
    if cfg.harmonic:
        y = librosa.effects.harmonic(y)
    need_cqt = cfg.representation in {'cqt', 'chroma'} or cfg.chroma or cfg.bass
    cqt = None
    if need_cqt:
        cqt = np.abs(librosa.cqt(y, sr=cfg.sample_rate, hop_length=cfg.hop_length,
                               fmin=cfg.fmin, n_bins=cfg.bins_per_octave * cfg.octaves,
                               bins_per_octave=cfg.bins_per_octave, tuning=0)).astype(np.float32)
        # Fold the fine pitch bins around each semitone centre, not after it.
        fine = cfg.bins_per_octave // 12
        aligned = np.pad(cqt, ((fine // 2, 0), (0, 0)))[:len(cqt)]
        semitones = aligned.reshape(cfg.octaves * 12, fine, -1).sum(axis=1)
        chroma = semitones.reshape(cfg.octaves, 12, -1).sum(axis=0)
        chroma /= np.maximum(chroma.max(axis=0, keepdims=True), 1e-6)
        bass = semitones[:min(24, len(semitones))].reshape(-1, 12, semitones.shape[-1]).sum(axis=0)
        bass /= np.maximum(bass.max(axis=0, keepdims=True), 1e-6)
    if cfg.representation == 'cqt':
        main = np.log1p(100 * cqt)
    elif cfg.representation == 'chroma':
        main = chroma
    else:
        spectrum = np.abs(librosa.stft(y, n_fft=cfg.n_fft, hop_length=cfg.hop_length))
        if cfg.representation == 'mel':
            spectrum = librosa.feature.melspectrogram(S=spectrum ** 2, sr=cfg.sample_rate,
                                                     n_fft=cfg.n_fft, n_mels=cfg.n_mels)
        main = np.log1p(spectrum)
    parts = [main]
    if cfg.chroma:
        parts.append(chroma)
    if cfg.bass:
        parts.append(bass)
    return np.concatenate(parts, axis=0).astype(np.float32)


def extract_features(path, cfg):
    import librosa
    cfg.validate()
    y, sr = librosa.load(path, sr=cfg.sample_rate, mono=True)
    duration = len(y) / sr
    if not len(y) or not np.isfinite(y).all():
        raise ValueError('Audio vacío o con muestras no finitas')
    # Frame centres are t = k*hop/sr, strictly before the end of the audio.
    frames = max(1, int(np.ceil(len(y) / cfg.hop_length)))
    result = np.empty((cfg.dimensions, frames), dtype=np.float32)
    chunk = max(1, round(cfg.block_seconds * sr / cfg.hop_length))
    context = int(np.ceil(2 * sr / cfg.hop_length))
    for start in range(0, frames, chunk):
        end = min(start + chunk, frames)
        first = max(0, start - context)
        last = min(len(y), (end + context) * cfg.hop_length)
        block = y[first * cfg.hop_length:last]
        # CQT needs enough support even for very short uploaded clips.
        block = np.pad(block, (0, max(0, 2 * sr - len(block))))
        local = _block_features(block, cfg)
        offset = start - first
        result[:, start:end] = local[:, offset:offset + end - start]
    if not np.isfinite(result).all():
        raise ValueError('Features no finitas')
    return result, duration


def cached_features(path, cfg, cache_dir, mmap=False):
    """mmap=True returns a read-only memory map, so a large corpus need not fit in RAM."""
    key = fingerprint({'audio': file_digest(path), 'config': asdict(cfg),
                       'feature_version': FEATURE_VERSION})
    target = Path(cache_dir) / (key + '.npz')
    target.parent.mkdir(parents=True, exist_ok=True)
    if mmap:
        array, meta = target.with_suffix('.npy'), target.with_suffix('.json')
        if not (array.is_file() and meta.is_file()):
            if target.is_file():
                with np.load(target, allow_pickle=False) as data:
                    features, duration = data['features'], float(data['duration'])
            else:
                features, duration = extract_features(path, cfg)
            temporary = array.with_suffix('.tmp.npy')
            np.save(temporary, features)
            temporary.replace(array)
            # Written last: an array without its metadata is recomputed, never trusted.
            meta.write_text(json.dumps({'duration': duration}))
        return np.load(array, mmap_mode='r'), json.loads(meta.read_text())['duration']
    if target.is_file():
        with np.load(target, allow_pickle=False) as data:
            return data['features'], float(data['duration'])
    features, duration = extract_features(path, cfg)
    # Preparation is sequential; readers only see completed files.
    temporary = target.with_suffix('.tmp.npz')
    np.savez_compressed(temporary, features=features, duration=np.array(duration))
    temporary.replace(target)
    return features, duration

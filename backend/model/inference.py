"""Full-song inference, overlap-add context and the legacy JSON contract."""
from functools import lru_cache
from pathlib import Path
from time import perf_counter
import numpy as np
from .config import Config
from .features import FEATURE_VERSION, extract_features, file_digest
from .labels import NO_CHORD, QUALITIES, INTERVALS, state_name
from .temporal import decode, joint_probabilities, restrict_vocabulary


class ModelUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load(path, mtime_ns, size, device_name, allow_experimental):
    import torch
    from .model import ChordModel
    from .train import CHECKPOINT_VERSION
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    if (checkpoint.get('version') != CHECKPOINT_VERSION or not checkpoint.get('trained')
            or checkpoint.get('feature_version') != FEATURE_VERSION
            or checkpoint.get('qualities') != list(QUALITIES)):
        raise ModelUnavailable('Checkpoint no entrenado o incompatible')
    if not checkpoint.get('production_ready') and not allow_experimental:
        raise ModelUnavailable('Checkpoint experimental: requiere evaluación antes de activarse')
    cfg = Config.from_dict(checkpoint['config'])
    device = torch.device('cuda' if device_name == 'auto' and torch.cuda.is_available()
                          else 'cpu' if device_name == 'auto' else device_name)
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise ModelUnavailable('CUDA no está disponible')
    model = ChordModel(cfg.features.dimensions, cfg.model)
    model.load_state_dict(checkpoint['model'], strict=True)
    if not all(torch.isfinite(value).all() for value in model.state_dict().values()):
        raise ModelUnavailable('Checkpoint con pesos no finitos')
    mean, std = np.array(checkpoint['mean'], dtype=np.float32), np.array(checkpoint['std'], dtype=np.float32)
    if (mean.shape != (cfg.features.dimensions,) or std.shape != mean.shape
            or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std <= 0)):
        raise ModelUnavailable('Normalización del checkpoint inválida')
    model.to(device).eval()
    return model, cfg, mean, std, checkpoint, device


def load_model(path, device='auto', allow_experimental=False):
    if not path or not Path(path).is_file():
        raise ModelUnavailable('No hay checkpoint neuronal disponible')
    info = Path(path).stat()
    return _load(str(Path(path).resolve()), info.st_mtime_ns, info.st_size, device, allow_experimental)


def predict_features(features, loaded, mode='accurate'):
    import torch
    model, cfg, mean, std, checkpoint, device = loaded
    if mode not in {'fast', 'accurate'}:
        raise ValueError('Modo desconocido')
    window = max(1, round(cfg.train.segment_seconds * cfg.features.sample_rate / cfg.features.hop_length))
    stride = window if mode == 'fast' else max(1, window // 2)
    length = features.shape[-1]
    heads = ([('chord', NO_CHORD + 1)] if cfg.model.head == 'joint'
             else [('root', 12), ('quality', len(QUALITIES)), ('presence', 2)])
    outputs = {name: np.zeros((length, size), np.float32) for name, size in heads}
    if cfg.model.bass_head:
        outputs['bass'] = np.zeros((length, 12), np.float32)
    normalizer = np.zeros(length, np.float32)
    starts = list(range(0, max(1, length - window + 1), stride))
    if starts[-1] + window < length:
        starts.append(max(0, length - window))
    with torch.inference_mode():
        for start in starts:
            end = min(length, start + window)
            x = (features[:, start:end] - mean[:, None]) / std[:, None]
            with torch.autocast(device_type=device.type, enabled=cfg.train.amp and device.type == 'cuda'):
                logits = model(torch.from_numpy(x[None]).to(device))
            weights = np.maximum(np.hanning(end - start), 0.1).astype(np.float32)
            for name in outputs:
                probability = logits[name][0].float().softmax(-1).cpu().numpy()
                outputs[name][start:end] += probability * weights[:, None]
            normalizer[start:end] += weights
    for name in outputs:
        outputs[name] /= normalizer[:, None]
        if not np.isfinite(outputs[name]).all():
            raise ModelUnavailable('Predicciones neuronales no finitas')
    return outputs


def estimate_key(probabilities, features=None, cfg=None, source='spectrum'):
    from ..scripts.analyze import detect_key
    # spectrum: independent evidence from the audio; chords: what the model actually hears.
    if source == 'spectrum' and features is not None and cfg is not None:
        chroma_features = None
        if cfg.representation == 'cqt':
            bins = cfg.octaves * cfg.bins_per_octave
            magnitude = np.expm1(features[:bins]) / 100
            chroma_features = magnitude.reshape(cfg.octaves, 12, cfg.bins_per_octave // 12, -1).sum(axis=(0, 2))
        elif cfg.representation == 'chroma':
            chroma_features = features[:12]
        elif cfg.chroma:
            start = cfg.dimensions - 12 * (1 + int(cfg.bass))
            chroma_features = features[start:start + 12]
        if chroma_features is not None:
            spectrum = chroma_features.mean(axis=1)
            return detect_key(spectrum) if spectrum.std() > 1e-8 else None
    chroma = np.zeros(12, dtype=np.float64)
    for root in range(12):
        for quality, intervals in enumerate(INTERVALS):
            mass = probabilities[:, root * len(QUALITIES) + quality].sum()
            for interval in intervals:
                chroma[(root + interval) % 12] += mass / len(intervals)
    return detect_key(chroma) if chroma.std() > 1e-8 else None


def bass_sequence(probabilities, path, cfg, frame_seconds, supervised):
    bass = np.full(len(path), -1, dtype=np.int64)
    if probabilities is None or not supervised:
        return bass
    candidate = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    # Emit a slash only for a chord tone with sustained bass evidence.
    for i, state in enumerate(path):
        if state != NO_CHORD and confidence[i] >= cfg.bass_threshold:
            root, quality = divmod(int(state), len(QUALITIES))
            if (int(candidate[i]) - root) % 12 in INTERVALS[quality]:
                bass[i] = candidate[i]
    starts = np.r_[0, np.flatnonzero((bass[1:] != bass[:-1]) | (path[1:] != path[:-1])) + 1, len(bass)]
    for start, end in zip(starts[:-1], starts[1:]):
        if (end - start) * frame_seconds < cfg.bass_min_seconds:
            bass[start:end] = -1
    return bass


def analyze_neural(path, checkpoint_path, title='', artist='', mode='accurate',
                   device='auto', allow_experimental=False, diagnostics_path=None, smooth=True,
                   loaded_model=None, vocabulary=None):
    from .labels import NOTES
    started = perf_counter()
    loaded = loaded_model if loaded_model is not None else load_model(checkpoint_path, device, allow_experimental)
    model, cfg, _, _, checkpoint, _ = loaded
    if checkpoint.get('production_ready') and checkpoint.get('promotion', {}).get('mode') != mode:
        raise ModelUnavailable('El modo solicitado no corresponde al modo evaluado para este candidato')
    features_started = perf_counter()
    features, duration = extract_features(path, cfg.features)
    prediction_started = perf_counter()
    heads = predict_features(features, loaded, mode)
    probabilities = (heads['chord'] if 'chord' in heads
                     else joint_probabilities(heads['root'], heads['quality'], heads['presence']))
    vocabulary = vocabulary or cfg.decode.vocabulary
    probabilities = restrict_vocabulary(probabilities, vocabulary)
    key = estimate_key(probabilities, features, cfg.features, cfg.decode.key_source)
    decoding_started = perf_counter()
    frame_seconds = cfg.features.hop_length / cfg.features.sample_rate
    states, diagnostic = decode(probabilities, cfg.decode, frame_seconds, key, smooth)
    bass = bass_sequence(heads.get('bass'), states, cfg.decode, frame_seconds, checkpoint['bass_supervised'])
    names = [state_name(state, int(b)) for state, b in zip(states, bass)]
    starts = [0] + [i for i in range(1, len(names)) if names[i] != names[i - 1]]
    timeline = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(names)
        time = start * frame_seconds
        timeline.append({'time': round(time, 4), 'end': round(min(end * frame_seconds, duration), 4),
                         'time_str': f'{int(time) // 60}:{int(time) % 60:02}', 'chord': names[start],
                         'measure': index + 1,
                         'bass': NOTES[int(bass[start])] if bass[start] >= 0 else None,
                         'confidence': round(float(probabilities[start:end, states[start]].mean()), 4)})
    if diagnostics_path:
        target = Path(diagnostics_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(target, **heads, joint=probabilities, decoded_states=states,
                            frame_seconds=np.array(frame_seconds), **diagnostic)
    finished = perf_counter()
    return {'success': True, 'notes_count': len(states), 'chords_timeline': timeline,
            'title': title or Path(path).stem, 'artist': artist, 'duration': duration,
            'key': f'{NOTES[key[0]]} {key[1]}' if key else '', 'engine': 'neural',
            'model': {'experimental': not checkpoint.get('production_ready'), 'mode': mode,
                      'epoch': checkpoint['epoch'] + 1, 'temporal': cfg.model.temporal,
                      'key_prior_weight': cfg.decode.key_prior_weight, 'switch_cost': cfg.decode.switch_cost,
                      'vocabulary': vocabulary, 'key_source': cfg.decode.key_source,
                      'confidence_calibrated': False},
            'timings': {'initialization_seconds': round(features_started - started, 3),
                        'features_seconds': round(prediction_started - features_started, 3),
                        'inference_seconds': round(decoding_started - prediction_started, 3),
                        'chords_seconds': round(finished - decoding_started, 3),
                        'analysis_seconds': round(finished - started, 3)}}

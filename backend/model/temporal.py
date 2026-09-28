"""Explicit log-probability decoding. No hard diatonic replacement or minimum chord length."""
import numpy as np
from .labels import NO_CHORD, QUALITIES, parse_label


def joint_probabilities(root, quality, presence):
    chord = root[:, :, None] * quality[:, None, :] * presence[:, 1, None, None]
    return np.concatenate((chord.reshape(len(root), -1), presence[:, :1]), axis=1)


# Song sheets usually write the triad even when a melody or voicing adds the seventh.
TRIAD_OF = {QUALITIES.index('7'): QUALITIES.index('maj'), QUALITIES.index('maj7'): QUALITIES.index('maj'),
            QUALITIES.index('m7'): QUALITIES.index('min')}


def restrict_vocabulary(probabilities, vocabulary='full'):
    """Fold probability mass before decoding, so a seventh cannot win over its own triad."""
    if vocabulary == 'full':
        return probabilities
    if vocabulary != 'triads':
        raise ValueError('vocabulary debe ser full o triads')
    folded = probabilities.copy()
    roots = np.arange(12) * len(QUALITIES)
    for extended, triad in TRIAD_OF.items():
        folded[:, roots + triad] += folded[:, roots + extended]
        folded[:, roots + extended] = 0
    return folded


def musical_prior(key_root, key_mode):
    # Canonical labels resolve baseline's min/m spelling without changing it.
    from ..scripts.analyze import get_diatonic_chords, get_dominant_chord
    allowed = get_diatonic_chords(key_root, key_mode)
    dominant = get_dominant_chord(key_root, key_mode)
    allowed.update((dominant, dominant + '7'))
    # Secondary V7 chords target each diatonic root; still only a soft bonus.
    from .labels import NOTES
    for name in list(allowed):
        label = parse_label(name)
        if label.root >= 0:
            allowed.add(NOTES[(label.root + 7) % 12] + '7')
    prior = np.zeros(NO_CHORD + 1, dtype=np.float64)
    for name in allowed:
        label = parse_label(name)
        if label.state < 0:
            continue
        prior[label.state] = 1
        # A diatonic chord keeps its bonus when coloured: Cmaj7, Am7, Dsus2 are still in key.
        colours = {'maj': ('maj7', '7', 'sus2', 'sus4'), 'min': ('m7', 'sus2', 'sus4')}
        for quality in colours.get(QUALITIES[label.quality], ()):
            prior[label.root * len(QUALITIES) + QUALITIES.index(quality)] = 1
    return prior


def viterbi(log_probabilities, switch_cost=2.0):
    """O(frames * states) uniform switch penalty, retaining evidence for brief chords."""
    emission = np.asarray(log_probabilities, dtype=np.float64)
    if emission.ndim != 2 or not len(emission) or not np.isfinite(emission).all():
        raise ValueError('Viterbi requiere probabilidades logarítmicas finitas')
    if switch_cost < 0:
        raise ValueError('switch_cost debe ser no negativo')
    states = emission.shape[1]
    back = np.empty(emission.shape, dtype=np.int16)
    score = emission[0].copy()
    index = np.arange(states)
    for t in range(1, len(emission)):
        best = int(np.argmax(score))
        alternate = score[best] - switch_cost
        stay = score >= alternate
        back[t] = np.where(stay, index, best)
        score = emission[t] + np.maximum(score, alternate)
        score -= score.max()
    path = np.empty(len(emission), dtype=np.int64)
    path[-1] = score.argmax()
    for t in range(len(emission) - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return path


def decode(probabilities, cfg, frame_seconds, key=None, smooth=True):
    raw = np.log(np.maximum(probabilities, 1e-9))
    prior = musical_prior(*key) if key is not None and cfg.key_prior_weight else np.zeros(raw.shape[1])
    # Scale accumulated evidence by time, so hop changes do not implicitly retune smoothing.
    combined = (raw + cfg.key_prior_weight * prior[None]) * (frame_seconds / 0.025)
    path = viterbi(combined, cfg.switch_cost) if smooth else combined.argmax(axis=1)
    return path, {'key_prior': prior, 'raw_states': raw.argmax(axis=1)}

"""Time-weighted and frame metrics, with unknown-reference coverage made explicit."""
import numpy as np
from .labels import IGNORE, NO_CHORD, NOTES, QUALITIES, parse_label, state_name, to_harte


def intervals_from_timeline(timeline, duration):
    intervals = []
    last = 0.0
    for i, event in enumerate(timeline):
        start = max(0.0, min(duration, float(event['time'])))
        end = min(duration, float(timeline[i + 1]['time']) if i + 1 < len(timeline) else duration)
        if start > last:
            intervals.append((last, start, 'N'))
        if end > start:
            symbol = event['chord']
            if event.get('bass') and '/' not in symbol and symbol not in {'N', 'X'}:
                symbol += '/' + event['bass']
            intervals.append((start, end, symbol))
            last = end
    if last < duration:
        intervals.append((last, duration, 'N'))
    return intervals


def sample(intervals, times):
    symbols = np.full(len(times), 'X', dtype=object)
    for start, end, symbol in intervals:
        first, last = np.searchsorted(times, [start, end], side='left')
        symbols[first:last] = symbol
    return symbols


def _encoded(symbols, implicit_bass=False):
    cache = {str(s): parse_label(s, implicit_bass=implicit_bass) for s in set(symbols)}
    return [cache[str(s)] for s in symbols]


def _confusion(true, predicted, weights, size):
    matrix = np.zeros((size, size + 1), dtype=np.float64)
    true, predicted = np.array(true), np.array(predicted)
    valid = true >= 0
    predicted = np.where(predicted >= 0, predicted, size)
    np.add.at(matrix, (true[valid], predicted[valid]), weights[valid])
    return matrix


def confusion_summary(matrix, names):
    size = len(names)
    diagonal = np.diag(matrix[:, :size])
    support = matrix.sum(axis=1)
    predicted = matrix.sum(axis=0)[:size]
    precision = np.divide(diagonal, predicted, out=np.zeros(size), where=predicted > 0)
    recall = np.divide(diagonal, support, out=np.zeros(size), where=support > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(size), where=precision + recall > 0)
    active = (support + predicted) > 0
    confusion = [(float(matrix[i, j]), names[i], names[j] if j < size else 'X')
                 for i in range(size) for j in range(size + 1) if i != j and matrix[i, j] > 0]
    confusion.sort(reverse=True)
    denominator = matrix.sum()
    return {'accuracy': float(diagonal.sum() / denominator) if denominator else None,
            'macro_precision': float(precision[active].mean()) if active.any() else None,
            'macro_recall': float(recall[active].mean()) if active.any() else None,
            'macro_f1': float(f1[active].mean()) if active.any() else None,
            'labels': names, 'predicted_labels': names + ['X'], 'confusion_matrix_seconds': matrix.tolist(),
            'per_class': {name: {'precision': float(precision[i]), 'recall': float(recall[i]),
                                 'f1': float(f1[i]), 'support_seconds': float(support[i])}
                          for i, name in enumerate(names)},
            'top_confusions': [{'reference': a, 'predicted': b, 'seconds': round(s, 3)} for s, a, b in confusion[:15]]}


def boundary_counts(ref_times, est_times, tolerance=0.25):
    i = j = matched = 0
    errors = []
    while i < len(ref_times) and j < len(est_times):
        delta = est_times[j] - ref_times[i]
        if abs(delta) <= tolerance:
            matched += 1
            errors.append(abs(delta))
            i += 1
            j += 1
        elif delta < -tolerance:
            j += 1
        else:
            i += 1
    return {'matched': matched, 'reference': len(ref_times), 'predicted': len(est_times),
            'absolute_error_sum': float(sum(errors))}


def boundary_summary(counts):
    tp, ref, pred = (counts[k] for k in ('matched', 'reference', 'predicted'))
    precision = tp / pred if pred else (1.0 if not ref else 0.0)
    recall = tp / ref if ref else (1.0 if not pred else 0.0)
    return {**counts, 'precision': precision, 'recall': recall,
            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            'mean_absolute_error_seconds': counts['absolute_error_sum'] / tp if tp else None}


def score_song(reference, estimated, duration, frame_seconds=0.02, boundary_tolerance=0.25, implicit_bass=False):
    # Exact interval intersection provides WCSR independently of the sampling hop.
    edges = np.unique(np.clip([0, duration] + [v for row in reference + estimated for v in row[:2]], 0, duration))
    weights, midpoints = np.diff(edges), (edges[1:] + edges[:-1]) / 2
    ref = _encoded(sample(reference, midpoints), implicit_bass=implicit_bass)
    est = _encoded(sample(estimated, midpoints))
    true_states, predicted_states = [x.state for x in ref], [x.state for x in est]
    chord = _confusion(true_states, predicted_states, weights, NO_CHORD + 1)
    root = _confusion([x.root for x in ref], [x.root for x in est], weights, 12)
    quality = _confusion([x.quality for x in ref], [x.quality for x in est], weights, len(QUALITIES))
    bass = _confusion([x.bass for x in ref], [x.bass for x in est], weights, 12)
    times = np.arange(0, duration, frame_seconds)
    rf = np.array([x.state for x in _encoded(sample(reference, times))])
    ef = np.array([x.state for x in _encoded(sample(estimated, times))])
    valid = rf >= 0
    # Only count boundaries inside contiguous, annotated and supported regions.
    ts, ps = np.array(true_states), np.array(predicted_states)
    region = (ts[:-1] >= 0) & (ts[1:] >= 0)
    r_changes = edges[1:-1][region & (ts[1:] != ts[:-1])]
    e_changes = edges[1:-1][region & (ps[1:] != ps[:-1])]
    boundaries = boundary_counts(r_changes, e_changes, boundary_tolerance)
    standard = {}
    try:
        import mir_eval.chord
        # Standard metrics on each supported contiguous region; no unknown-gap credit.
        known = ts >= 0
        indices = np.flatnonzero(np.diff(np.r_[False, known, False]))
        sums, total = {}, 0.0
        for first, last in indices.reshape(-1, 2):
            intervals = np.column_stack((edges[first:last], edges[first + 1:last + 1]))
            rnames = [to_harte(state_name(s)) for s in ts[first:last]]
            enames = [to_harte(state_name(s)) for s in ps[first:last]]
            def merge_same(names):
                starts = [0] + [i for i in range(1, len(names)) if names[i] != names[i - 1]]
                ends = starts[1:] + [len(names)]
                return np.array([[intervals[a, 0], intervals[b - 1, 1]] for a, b in zip(starts, ends)]), [names[a] for a in starts]
            ri, rl = merge_same(rnames)
            ei, el = merge_same(enames)
            # Do not shift boundaries or pad across unannotated gaps.
            local = mir_eval.chord.evaluate(ri - ri[0, 0], rl, ei - ri[0, 0], el)
            length = float(edges[last] - edges[first])
            total += length
            for key in ('root', 'majmin', 'sevenths', 'mirex', 'seg', 'underseg', 'overseg'):
                sums[key] = sums.get(key, 0.0) + float(local[key]) * length
        standard = {key: value / total for key, value in sums.items()} if total else {}
    except ImportError:
        standard = {'unavailable': 'Instala backend/requirements-neural.txt para mir_eval'}
    return {'duration_seconds': duration, 'scored_seconds': float(chord.sum()),
            'frame_correct': int(((rf == ef) & valid).sum()), 'frame_total': int(valid.sum()),
            'chord_matrix': chord, 'root_matrix': root, 'quality_matrix': quality, 'bass_matrix': bass,
            'boundaries': boundaries, 'mir_eval_supported_vocabulary': standard}


def aggregate(scores):
    if not scores:
        return {'available': False, 'reason': 'No hay canciones evaluadas'}
    chord = confusion_summary(sum(s['chord_matrix'] for s in scores), [state_name(i) for i in range(NO_CHORD + 1)])
    root = confusion_summary(sum(s['root_matrix'] for s in scores), list(NOTES))
    quality = confusion_summary(sum(s['quality_matrix'] for s in scores), list(QUALITIES))
    bass = confusion_summary(sum(s['bass_matrix'] for s in scores), list(NOTES))
    frames = sum(s['frame_total'] for s in scores)
    scored = sum(s['scored_seconds'] for s in scores)
    duration = sum(s['duration_seconds'] for s in scores)
    boundary = {key: sum(s['boundaries'][key] for s in scores) for key in scores[0]['boundaries']}
    standard = {}
    for key in ('root', 'majmin', 'sevenths', 'mirex', 'seg', 'underseg', 'overseg'):
        valid = [s for s in scores if key in s['mir_eval_supported_vocabulary']]
        denominator = sum(s['scored_seconds'] for s in valid)
        standard[key] = sum(s['mir_eval_supported_vocabulary'][key] * s['scored_seconds'] for s in valid) / denominator if denominator else None
    return {'available': True, 'songs': len(scores), 'duration_seconds': duration,
            'scored_seconds': scored, 'vocabulary_coverage': scored / duration if duration else None,
            'frame_accuracy': sum(s['frame_correct'] for s in scores) / frames if frames else None,
            'weighted_chord_accuracy': chord['accuracy'], 'chord_accuracy': chord['accuracy'],
            'root_accuracy': root['accuracy'], 'quality_accuracy': quality['accuracy'],
            'root_scored_seconds': float(sum(s['root_matrix'].sum() for s in scores)),
            'quality_scored_seconds': float(sum(s['quality_matrix'].sum() for s in scores)),
            'bass_scored_seconds': float(sum(s['bass_matrix'].sum() for s in scores)),
            'bass_accuracy_explicit_annotations': bass['accuracy'],
            'mean_song_chord_accuracy': float(np.mean([np.trace(s['chord_matrix']) / s['scored_seconds']
                                                       for s in scores if s['scored_seconds'] > 0])) if scored else None,
            'chords': chord, 'roots': root, 'qualities': quality, 'bass': bass,
            'changes': boundary_summary(boundary), 'mir_eval_supported_vocabulary': standard}

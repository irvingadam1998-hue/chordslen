"""Explicit vocabulary: unsupported qualities are masked, never silently major."""
from dataclasses import dataclass
import re

NOTES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
QUALITIES = ('maj', 'min', '7', 'maj7', 'm7', 'dim', 'aug', 'sus2', 'sus4')
INTERVALS = ((0, 4, 7), (0, 3, 7), (0, 4, 7, 10), (0, 4, 7, 11),
             (0, 3, 7, 10), (0, 3, 6), (0, 4, 8), (0, 2, 7), (0, 5, 7))
IGNORE = -100
NO_CHORD = 12 * len(QUALITIES)
SUFFIX = ('', 'm', '7', 'maj7', 'm7', 'dim', 'aug', 'sus2', 'sus4')


@dataclass(frozen=True)
class Label:
    root: int = IGNORE
    quality: int = IGNORE
    presence: int = IGNORE
    bass: int = IGNORE

    @property
    def state(self):
        if self.presence == 0:
            return NO_CHORD
        return self.root * len(QUALITIES) + self.quality if self.quality >= 0 else IGNORE


def pitch_class(note):
    match = re.fullmatch(r'([A-G])([#b]*)', note)
    if not match:
        raise ValueError(f'Nota inválida: {note}')
    return ({'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[match[1]]
            + match[2].count('#') - match[2].count('b')) % 12


def parse_label(symbol, implicit_bass=False):
    symbol = str(symbol).strip()
    if symbol in {'N', 'no_chord'}:
        return Label(presence=0)
    if symbol in {'X', '?', '*', ''}:
        return Label()
    match = re.fullmatch(r'([A-G][#b]*):?([^/]*)(?:/(.+))?', symbol)
    if not match:
        return Label()
    root = pitch_class(match[1])
    quality_text = {'': 'maj', 'm': 'min', 'min7': 'm7'}.get(match[2], match[2])
    quality = QUALITIES.index(quality_text) if quality_text in QUALITIES else IGNORE
    # Harte pitch-set annotations are matched exactly, including alterations.
    if quality < 0 and '(' in quality_text:
        try:
            import mir_eval.chord
            _, bitmap, _ = mir_eval.chord.encode(symbol, reduce_extended_chords=False)
            intervals = tuple(i for i, value in enumerate(bitmap) if value)
            quality = INTERVALS.index(intervals) if intervals in INTERVALS else IGNORE
        except (ImportError, ValueError):
            pass
    bass = root if implicit_bass else IGNORE
    if match[3]:
        try:
            if re.fullmatch(r'[A-G][#b]*', match[3]):
                bass = pitch_class(match[3])
            else:
                degree = re.fullmatch(r'([#b]*)([1-7])', match[3])
                if degree:
                    bass = (root + (0, 2, 4, 5, 7, 9, 11)[int(degree[2]) - 1]
                            + degree[1].count('#') - degree[1].count('b')) % 12
        except ValueError:
            pass
    return Label(root, quality, 1, bass)


def state_name(state, bass=None):
    if state == NO_CHORD:
        return 'N'
    if state < 0:
        return 'X'
    root, quality = divmod(int(state), len(QUALITIES))
    name = NOTES[root] + SUFFIX[quality]
    if bass is not None and bass >= 0 and bass != root:
        name += '/' + NOTES[bass]
    return name


def to_harte(symbol):
    label = parse_label(symbol)
    if label.presence == 0:
        return 'N'
    if label.state < 0:
        return 'X'
    quality = 'min7' if QUALITIES[label.quality] == 'm7' else QUALITIES[label.quality]
    suffix = ''
    if label.bass >= 0:
        relative = (label.bass - label.root) % 12
        suffix = '/' + ('1', 'b2', '2', 'b3', '3', '4', '#4', '5', 'b6', '6', 'b7', '7')[relative]
    return NOTES[label.root] + ':' + quality + suffix

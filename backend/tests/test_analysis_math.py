"""Check that faster filtering and scoring preserve the musical inputs/results."""
import unittest

import librosa
import numpy as np
from scipy.ndimage import median_filter

from backend.scripts.analyze import (
    ChordScorer, _harmonic_audio, _median_along_axis, make_chord_templates,
)


class AnalysisMathTests(unittest.TestCase):
    def test_fast_medians_match_scipy_at_edges_and_across_rows(self):
        rng = np.random.default_rng(482)
        for shape in ((1, 1), (4, 9), (31, 35), (128, 85)):
            for dtype in (np.float32, np.float64):
                values = rng.random(shape).astype(dtype)
                for axis in (0, 1):
                    with self.subTest(shape=shape, dtype=dtype, axis=axis):
                        size = (31, 1) if axis == 0 else (1, 31)
                        expected = median_filter(values, size=size, mode='reflect')
                        np.testing.assert_array_equal(_median_along_axis(values, axis), expected)

    def test_harmonic_audio_matches_librosa_for_tones_transients_and_silence(self):
        rng = np.random.default_rng(254)
        t = np.arange(22050, dtype=np.float32) / 22050
        tones = (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 330 * t)) / 4
        transients = tones + rng.normal(0, 0.01, len(t)).astype(np.float32)
        transients[::2205] += 0.5
        for audio in (tones, transients, np.zeros_like(t)):
            expected = librosa.effects.harmonic(audio)
            np.testing.assert_allclose(_harmonic_audio(audio), expected, rtol=1e-6, atol=1e-7)

    def test_scoring_recognizes_major_minor_and_dominant_seventh(self):
        templates = make_chord_templates()
        scorer = ChordScorer(templates)
        for name in ('C', 'D', 'F#', 'Amin', 'C#min', 'G7'):
            with self.subTest(name=name):
                chord, score, _ = scorer.detect(templates[name])
                self.assertEqual(chord, name)
                self.assertGreater(score, 0.9)

    def test_scoring_ties_continuity_and_silence(self):
        template = np.array([1, 0, 0, 0, 0.6, 0, 0, 0.8, 0, 0, 0, 0])
        scorer = ChordScorer({'C': template, 'D': template, 'zero': np.zeros(12)})
        self.assertEqual(scorer.detect(template)[0], 'D')
        self.assertEqual(scorer.detect(template, prev_chord='C')[0], 'C')
        self.assertEqual(scorer.detect(np.zeros(12)), (None, 0.0, None))
        self.assertEqual(ChordScorer({}).detect(template), (None, 0.0, None))


if __name__ == '__main__':
    unittest.main()

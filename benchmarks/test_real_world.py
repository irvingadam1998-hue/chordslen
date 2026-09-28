"""Checks that real-song experiments cannot manufacture precision from predictions."""
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.real_world import extension_errors, read_reference, summarize, triads, write_json


class RealSongMetricsTests(unittest.TestCase):
    def test_unknown_reference_is_not_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reference.lab'
            path.write_text('0 10 X\n')
            with self.assertRaisesRegex(ValueError, 'No hay acordes revisados'):
                read_reference(path, 10)

    def test_reference_must_match_recording_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reference.lab'
            path.write_text('0 10 C\n')
            with self.assertRaisesRegex(ValueError, 'excede'):
                read_reference(path, 9)
            path.write_text('0 3 C\n2 4 Am\n')
            with self.assertRaises(ValueError):
                read_reference(path, 10)

    def test_added_seventh_is_not_a_root_error_or_unknown_region(self):
        reference = [(0, 2, 'Am'), (2, 5, 'F'), (5, 7, 'G7'), (7, 9, 'X')]
        estimated = [(0, 2, 'Am7'), (2, 5, 'Dm7'), (5, 7, 'G'), (7, 9, 'Cmaj7')]
        result = extension_errors(reference, estimated, 9)
        self.assertEqual(result['added_sevenths_same_triad_seconds'], 2)
        self.assertEqual(result['missed_sevenths_same_triad_seconds'], 2)
        self.assertEqual(result['reference_triad_seconds'], 5)
        self.assertEqual(result['reference_seventh_seconds'], 2)

    def test_simplified_comparison_preserves_minor_root_and_bass(self):
        intervals = [(0, 1, 'Fmaj7/A'), (1, 2, 'Am7'), (2, 3, 'G7'), (3, 4, 'N')]
        self.assertEqual([r[2] for r in triads(intervals)], ['F/A', 'Am', 'G', 'N'])

    def test_prevalence_is_duration_weighted_and_not_accuracy(self):
        result = {'duration': 10, 'chords_timeline': [
            {'time': 0, 'chord': 'Am'}, {'time': 9, 'chord': 'Am7'}]}
        summary = summarize(result)
        self.assertEqual(summary['seventh_fraction'], 0.1)
        self.assertFalse(summary['accuracy_available'])

    def test_experiments_do_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            write_json(path, {'run': 1})
            with self.assertRaises(FileExistsError):
                write_json(path, {'run': 2})
            self.assertEqual(json.loads(path.read_text()), {'run': 1})


if __name__ == '__main__':
    unittest.main()

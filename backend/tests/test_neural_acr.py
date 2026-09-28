import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from backend.model.config import Config
from backend.model.dataset import align_labels, assert_no_leakage, read_annotations, transpose_segment
from backend.model.labels import IGNORE, NO_CHORD, parse_label, state_name
from backend.model.metrics import score_song, aggregate, boundary_counts
from backend.model.temporal import viterbi
from backend.scripts import analyze


class LabelAndDataTests(unittest.TestCase):
    def test_extended_qualities_inversions_and_unknown_are_not_collapsed(self):
        for symbol in ('Cmaj7', 'Dm7', 'F#dim', 'Gaug', 'Asus2', 'Bbsus4'):
            label = parse_label(symbol)
            self.assertGreaterEqual(label.state, 0)
        self.assertEqual(parse_label('C:maj/3').bass, 4)
        self.assertEqual(parse_label('C/E').bass, 4)
        self.assertEqual(parse_label('C').bass, IGNORE)
        self.assertEqual(parse_label('C:13').quality, IGNORE)
        self.assertEqual(parse_label('N').state, NO_CHORD)
        self.assertEqual(parse_label('X').state, IGNORE)
        self.assertEqual(state_name(parse_label('Cmaj7').state), 'Cmaj7')

    def test_half_open_alignment_and_unannotated_gap(self):
        y = align_labels([(0, 1, 'C'), (1, 1.5, 'Am'), (2, 3, 'N')], np.array([0, .99, 1, 1.5, 2]))
        self.assertEqual(y[:, 0].tolist(), [0, 0, 9, IGNORE, IGNORE])
        self.assertEqual(y[:, 2].tolist(), [1, 1, 1, IGNORE, 0])

    def test_leakage_rejected_for_artist_and_origin(self):
        first = {'artist_id': 'a', 'origin_id': 'one', 'split': 'train'}
        for artist, origin in [('a', 'two'), ('b', 'one')]:
            with self.assertRaisesRegex(ValueError, 'leakage'):
                assert_no_leakage([first, {'artist_id': artist, 'origin_id': origin, 'split': 'test'}])

    def test_jams_selects_performed_annotation_by_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.jams'
            path.write_text(json.dumps({'annotations': [
                {'namespace': 'chord', 'data': [{'time': 0, 'duration': 1, 'value': 'C'}]},
                {'namespace': 'chord', 'annotation_metadata': {'annotation_rules': 'separate string note transcriptions'},
                 'data': [{'time': 0, 'duration': 1, 'value': 'C:maj7'}]}]}))
            intervals = read_annotations({'format': 'guitarset_jams', 'annotation': str(path)})
            self.assertEqual(intervals, [(0, 1, 'C:maj7')])

    def test_transposition_moves_features_and_labels_together(self):
        cfg = Config.from_dict({'features': {'bins_per_octave': 12, 'octaves': 2, 'hop_length': 512,
                                             'chroma': True, 'bass': True}}).features
        x = np.zeros((cfg.dimensions, 1), dtype=np.float32)
        x[0], x[23], x[24], x[36] = 1, 2, 3, 4  # lowest/highest CQT bin, chroma C, bass C
        y = np.array([[0, 1, 1, 11], [IGNORE, IGNORE, 0, IGNORE]])
        shifted, labels = transpose_segment(x, y, 2, cfg)
        self.assertEqual(shifted[2, 0], 1)
        self.assertEqual(shifted[:2, 0].tolist(), [0, 0])  # vacated bins are silence
        self.assertEqual(shifted[26, 0], 3)
        self.assertEqual(shifted[38, 0], 4)
        self.assertEqual(float(shifted[:24].sum()), 1)  # top bin left the spectrum
        self.assertEqual(labels.tolist(), [[2, 1, 1, 1], [IGNORE, IGNORE, 0, IGNORE]])
        self.assertEqual(x[0, 0], 1)  # cached features are never modified in place
        down, _ = transpose_segment(x, y, -1, cfg)
        self.assertEqual((down[22, 0], down[23, 0]), (2, 0))

    def test_pitch_shift_rejected_for_non_pitch_representations(self):
        with self.assertRaisesRegex(ValueError, 'pitch_shift'):
            Config.from_dict({'features': {'representation': 'mel'}, 'train': {'pitch_shift': 3}})
        with self.assertRaisesRegex(ValueError, 'pitch_shift'):
            Config.from_dict({'train': {'pitch_shift': 7}})

    def test_guitarset_solo_takes_can_be_limited_to_train(self):
        from backend.model.prepare import guitarset_rows
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'annotations').mkdir()
            for artist in range(6):
                for family in '123':
                    for take in ('comp', 'solo'):
                        (root / 'annotations' / f'{artist:02}_Rock{family}-90-C_{take}.jams').write_text('{}')
            splits = {mode: {r['id']: r['split'] for r in guitarset_rows(root, solo=mode)}
                      for mode in ('keep', 'train-only', 'exclude')}
            solos = [k for k in splits['keep'] if k.endswith('_solo')]
            self.assertTrue(all(splits['exclude'][k] == 'excluded' for k in solos))
            self.assertTrue(all(splits['train-only'][k] in {'train', 'excluded'} for k in solos))
            self.assertIn('train', {splits['train-only'][k] for k in solos})
            comps = [k for k in splits['keep'] if k.endswith('_comp')]
            self.assertEqual({k: splits['keep'][k] for k in comps}, {k: splits['exclude'][k] for k in comps})

    def test_real_corpus_names_and_offset(self):
        from backend.model.real_corpus import clean_title, estimate_offset, label_chroma, normalize, shift_lab
        self.assertEqual(clean_title('01_-_I_Saw_Her_Standing_There'), 'I Saw Her Standing There')
        self.assertEqual(clean_title('CD1_-_05_-_Help'), 'Help')
        self.assertEqual(normalize('The Beatles'), normalize('beatles'))
        self.assertEqual(normalize('Help! - Remastered 2009'), normalize('Help!'))
        self.assertEqual(normalize('Corazón (Live)'), 'corazon')
        labels = [(i * 2.0, i * 2.0 + 2, ('C', 'Am', 'F', 'G')[i % 4]) for i in range(40)]
        template = label_chroma(labels, 1000, 0.1)
        audio = np.roll(template, 25, axis=1) + 0.05  # audio starts 2.5 s later
        lag, score, margin = estimate_offset(audio, template, 50)
        self.assertEqual(lag, 25)
        self.assertGreater(margin, 0.05)
        self.assertEqual(shift_lab([(0, 1, 'C'), (1, 3, 'G')], -1.5, 10), [(0.0, 1.5, 'G')])

    def test_memory_mapped_features_match_compressed_cache(self):
        from backend.model import features
        cfg = Config.from_dict({'features': {'representation': 'chroma', 'hop_length': 512}}).features
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / 'a.wav'
            audio.write_bytes(b'x')
            fake = (np.arange(24, dtype=np.float32).reshape(12, 2), 1.5)
            with patch.object(features, 'extract_features', return_value=fake) as extract:
                mapped, duration = features.cached_features(audio, cfg, directory, mmap=True)
                again, _ = features.cached_features(audio, cfg, directory, mmap=True)
            self.assertEqual(extract.call_count, 1)
            self.assertIsInstance(again, np.memmap)
            self.assertEqual((mapped.tolist(), duration), (fake[0].tolist(), 1.5))

    def test_lab_corpus_keeps_artists_in_one_split(self):
        from backend.model.prepare import lab_rows
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for artist, album, song in [('Band', 'One', '01_-_Song'), ('Band', 'Two', '03 - Song'),
                                        ('Solo', 'Live', 'Other')]:
                (root / 'labs' / artist / album).mkdir(parents=True, exist_ok=True)
                (root / 'audio' / artist / album).mkdir(parents=True, exist_ok=True)
                (root / 'labs' / artist / album / f'{song}.lab').write_text('0.0 1.0 C:maj\n')
                (root / 'audio' / artist / album / f'{song}.flac').write_bytes(b'x')
            (root / 'labs' / 'Solo' / 'Live' / 'NoAudio.lab').write_text('0.0 1.0 N\n')
            rows = lab_rows(root / 'labs', root / 'audio', 'My Corpus', split='auto')
            self.assertEqual(len(rows), 3)
            self.assertEqual({r['origin_id'] for r in rows if 'Band' in r['id']}, {'my-corpus:song:Band/song'})
            for artist in ('Band', 'Solo'):
                self.assertEqual(len({r['split'] for r in rows if r['artist_id'].endswith(artist)}), 1)
            assert_no_leakage(rows)


class TemporalAndMetricTests(unittest.TestCase):
    def test_weak_flicker_removed_but_short_confident_change_survives(self):
        p = np.tile([.99, .01], (11, 1))
        p[5] = [.49, .51]
        self.assertEqual(viterbi(np.log(p), 2).tolist(), [0] * 11)
        p[5] = [.00001, .99999]
        self.assertEqual(viterbi(np.log(p), 2)[5], 1)

    def test_exact_duration_and_changes_not_chord_coverage(self):
        ref = [(0, 1, 'C'), (1, 2, 'Am')]
        delayed = [(0, 1.1, 'C'), (1.1, 2, 'Am')]
        report = aggregate([score_song(ref, delayed, 2)])
        self.assertAlmostEqual(report['weighted_chord_accuracy'], .95)
        self.assertEqual(report['changes']['f1'], 1)
        self.assertAlmostEqual(report['changes']['mean_absolute_error_seconds'], .1)
        swapped = aggregate([score_song(ref, [(0, 1, 'Am'), (1, 2, 'C')], 2)])
        self.assertEqual(swapped['weighted_chord_accuracy'], 0)

    def test_unknown_reference_excluded_and_reported(self):
        report = aggregate([score_song([(0, 1, 'C'), (1, 2, 'X')], [(0, 2, 'C')], 2)])
        self.assertEqual(report['vocabulary_coverage'], .5)
        self.assertEqual(report['weighted_chord_accuracy'], 1)

    def test_triads_vocabulary_folds_sevenths_into_their_triad(self):
        from backend.model.labels import QUALITIES
        from backend.model.temporal import restrict_vocabulary
        state = lambda name: parse_label(name).state
        p = np.full((1, NO_CHORD + 1), 0.001)
        p[0, state('Am7')], p[0, state('Am')], p[0, state('C')] = 0.5, 0.2, 0.25
        folded = restrict_vocabulary(p, 'triads')
        self.assertEqual(state_name(int(folded.argmax())), 'Am')
        self.assertAlmostEqual(folded[0, state('Am')], 0.7)
        for name in ('Am7', 'C7', 'Cmaj7'):
            self.assertEqual(folded[0, state(name)], 0)
        self.assertAlmostEqual(folded.sum(), p.sum())
        self.assertIs(restrict_vocabulary(p, 'full'), p)
        self.assertGreater(folded[0, state('Csus4')], 0)  # other qualities are untouched
        with self.assertRaisesRegex(ValueError, 'vocabulary'):
            Config.from_dict({'decode': {'vocabulary': 'jazz'}})

    def test_key_from_chords_and_coloured_diatonic_prior(self):
        from backend.model.inference import estimate_key
        from backend.model.temporal import musical_prior
        state = lambda name: parse_label(name).state
        p = np.zeros((300, NO_CHORD + 1))
        for i, name in enumerate(['C', 'F', 'G', 'C'] * 75):
            p[i, state(name)] = 1
        # Spectrum says E minor; the chord source ignores it and hears C, F, G.
        spectrum = np.zeros((12, 300))
        spectrum[[4, 7, 11]] = 1
        cfg = Config.from_dict({'features': {'representation': 'chroma'}}).features
        self.assertEqual(estimate_key(p, spectrum, cfg, 'chords'), (0, 'major'))
        self.assertEqual(estimate_key(p, spectrum, cfg, 'spectrum'), (4, 'minor'))
        prior = musical_prior(0, 'major')
        for name in ('Cmaj7', 'Am7', 'Dsus2', 'G7', 'Fmaj7'):
            self.assertEqual(prior[state(name)], 1, name)
        for name in ('C#', 'Fm', 'Ebmaj7'):
            self.assertEqual(prior[state(name)], 0, name)
        with self.assertRaisesRegex(ValueError, 'key_source'):
            Config.from_dict({'decode': {'key_source': 'lyrics'}})

    def test_sheet_compare_reduces_sheet_spellings(self):
        from backend.model.sheet_compare import exact, score, triad, with_ends
        self.assertEqual([triad(c) for c in ('Am7', 'G7', 'Bb', 'G/B', 'Em7b5', 'DmMaj7')],
                         ['Am', 'G', 'A#', 'G', 'Edim', 'Dm'])
        self.assertIsNone(exact('Em7b5'))
        timeline = with_ends([{'time': 0, 'chord': 'Am7'}, {'time': 4, 'chord': 'F'}, {'time': 6, 'chord': 'Dm'}], 8)
        row = score(timeline, ['Am', 'F', 'C'])
        self.assertAlmostEqual(row['in_sheet'], 6 / 8)
        self.assertAlmostEqual(row['exact'], 2 / 8)
        self.assertEqual(row['invented'], [('Dm', 2)])

    def test_boundaries_match_only_once(self):
        result = boundary_counts([1.0], [.9, 1.1, 1.2], .25)
        self.assertEqual((result['matched'], result['predicted']), (1, 3))


class FallbackTests(unittest.TestCase):
    def test_missing_checkpoint_returns_legacy_and_notice(self):
        with tempfile.NamedTemporaryFile() as file, patch.object(analyze, '_analyze_audio',
                return_value={'success': True, 'engine': 'current'}) as baseline:
            result = analyze.analyze_file_path(file.name, engine='neural', checkpoint='/nonexistent/weights.pt')
            self.assertEqual(result['engine'], 'current')
            self.assertEqual(result['warnings'][0]['code'], 'ACR_NEURAL_FALLBACK')
            baseline.assert_called_once()

    def test_current_mode_never_loads_torch(self):
        with tempfile.NamedTemporaryFile() as file, patch.object(analyze, '_analyze_audio',
                return_value={'success': True, 'engine': 'current'}):
            self.assertEqual(analyze.analyze_file_path(file.name, engine='current')['engine'], 'current')

    def test_model_change_invalidates_worker_cache(self):
        with patch.dict(os.environ, {'ACR_ENGINE': 'current', 'ACR_MODE': 'fast'}):
            first = analyze.analysis_cache_namespace()
            os.environ['ACR_MODE'] = 'accurate'
            self.assertNotEqual(first, analyze.analysis_cache_namespace())


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Dependencia neuronal opcional no instalada')
class NetworkTests(unittest.TestCase):
    def test_all_temporal_backends_shapes_padding_and_gradients(self):
        import torch
        from backend.model.model import ChordModel
        from backend.model.train import combined_loss, losses_for
        torch.set_num_threads(2)
        for temporal in ('none', 'bilstm', 'transformer'):
            cfg = Config.from_dict({'model': {'temporal': temporal, 'channels': 4, 'embedding': 32, 'bass_head': True}})
            model = ChordModel(84, cfg.model)
            out = model(torch.randn(2, 84, 16), torch.tensor([16, 10]))
            self.assertEqual(tuple(out['root'].shape), (2, 16, 12))
            target = torch.zeros(2, 16, 4, dtype=torch.long)
            target[..., 2] = 1
            target[1, 10:] = IGNORE
            losses = losses_for([np.ones(n) for n in (12, 9, 2, 12)], True, 'cpu')
            loss = combined_loss(out, target, losses, .5)
            loss.backward()
            self.assertTrue(torch.isfinite(loss))
            self.assertGreater(model.root.weight.grad.abs().sum(), 0)

    def test_joint_head_scores_root_and_quality_together(self):
        import torch
        from backend.model.model import ChordModel
        from backend.model.train import chord_targets, combined_loss, losses_for
        cfg = Config.from_dict({'model': {'temporal': 'bilstm', 'channels': 4, 'embedding': 32, 'head': 'joint'}})
        model = ChordModel(84, cfg.model)
        out = model(torch.randn(1, 84, 4), torch.tensor([4]))
        self.assertEqual(set(out), {'chord'})
        self.assertEqual(tuple(out['chord'].shape), (1, 4, NO_CHORD + 1))
        # F major, F minor, no chord, unknown quality.
        target = torch.tensor([[[5, 0, 1, IGNORE], [5, 1, 1, IGNORE], [IGNORE, IGNORE, 0, IGNORE],
                                [5, IGNORE, 1, IGNORE]]])
        self.assertEqual(chord_targets(target).tolist(), [[45, 46, NO_CHORD, IGNORE]])
        losses = losses_for([np.ones(n) for n in (12, 9, 2, 12)], True, 'cpu')
        loss = combined_loss(out, target, losses, .5)
        loss.backward()
        self.assertGreater(model.chord.weight.grad.abs().sum(), 0)
        with self.assertRaisesRegex(ValueError, 'head'):
            Config.from_dict({'model': {'head': 'other'}})

    def test_experimental_or_corrupt_checkpoint_not_silently_enabled(self):
        import torch
        from backend.model.inference import load_model, ModelUnavailable
        from backend.model.labels import QUALITIES
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'experimental.pt'
            torch.save({'version': 1, 'feature_version': 1, 'trained': True,
                        'production_ready': False, 'qualities': list(QUALITIES)}, path)
            with self.assertRaisesRegex(ModelUnavailable, 'experimental'):
                load_model(path)
            path.write_bytes(b'invalid')
            with patch.object(analyze, '_analyze_audio', return_value={'success': True, 'engine': 'current'}):
                result = analyze.analyze_file_path(str(path), engine='neural', checkpoint=str(path))
                self.assertEqual(result['engine'], 'current')


if __name__ == '__main__':
    unittest.main()

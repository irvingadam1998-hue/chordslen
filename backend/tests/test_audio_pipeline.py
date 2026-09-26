import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from test_worker import worker
from backend.extractor_server.jobs import JobStore


class AudioPipelineTests(unittest.TestCase):
    def test_real_upload_detects_chords_across_processing_blocks(self):
        sr = 22050
        t = np.arange(sr * 12, dtype=np.float32) / sr
        c = sum(np.sin(2 * np.pi * f * t) for f in (261.63, 329.63, 392.0)) / 4
        g = sum(np.sin(2 * np.pi * f * t) for f in (196.0, 246.94, 293.66)) / 4
        audio = io.BytesIO()
        sf.write(audio, np.concatenate((c, g)), sr, format='WAV')
        audio.seek(0)
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(worker, 'TMP_ROOT', Path(directory)), \
             patch.object(worker, 'store', JobStore(Path(directory) / 'jobs.sqlite3')), \
             patch.object(worker, 'API_KEY', 'test'), \
             patch.object(worker, '_launch', side_effect=worker._run_job):
            with worker.app.test_client() as client:
                response = client.post('/analyze-file', headers={'x-api-key': 'test'},
                                       data={'audio': (audio, 'progression.wav')})
                result = response.json
                self.assertEqual(response.status_code, 200)
                self.assertTrue(result['success'], result)
                self.assertEqual(result['title'], 'progression')
                timeline = result['chords_timeline']
                self.assertIn('C', [event['chord'] for event in timeline])
                changes = [event['time'] for event in timeline if event['chord'] == 'G']
                self.assertTrue(any(11 <= time <= 13 for time in changes), timeline)
                self.assertTrue(all(0 <= event['time'] < 24 for event in timeline))
                self.assertEqual(list(Path(directory).glob('upload-*')), [])
                response.request.environ['wsgi.input'].close()
                response.close()


if __name__ == '__main__':
    unittest.main()

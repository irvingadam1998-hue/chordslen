import importlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.extractor_server.jobs import JobStore

_boot_dir = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'EXTRACTOR_TMP_DIR': _boot_dir.name}):
    worker = importlib.import_module('backend.extractor_server.app')


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (
            ('store', JobStore(Path(self.tmp.name) / 'jobs.sqlite3')),
            ('TMP_ROOT', Path(self.tmp.name)), ('API_KEY', 'test-secret'),
        ):
            p = patch.object(worker, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.client = worker.app.test_client()
        self.auth = {'x-api-key': 'test-secret'}
        self.origin = 'https://chordlens.example'

    def ticket(self):
        response = self.client.post('/upload-ticket', json={'origin': self.origin}, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        return response.json['token']

    def test_backend_requires_secret(self):
        self.assertEqual(self.client.post('/analyze', json={'url': 'https://youtu.be/abcdefghijk'}).status_code, 401)
        self.assertEqual(self.client.post('/upload-ticket', json={'origin': self.origin}).status_code, 401)
        self.assertEqual(self.client.post('/analyze-file').status_code, 401)

    def test_bad_urls_and_nonfinite_ranges_are_rejected(self):
        for url in ('https://example.com', 'https://youtube.com.evil.test/watch?v=abcdefghijk'):
            self.assertEqual(self.client.post('/analyze', json={'url': url}, headers=self.auth).status_code, 400)
        for start, end in ((-1, 10), (0, float('nan')), (0, 61)):
            response = self.client.post('/transcribe', json={'url': 'https://youtu.be/abcdefghijk', 'start': start, 'end': end}, headers=self.auth)
            self.assertEqual(response.status_code, 400)

    def test_same_video_in_different_url_forms_launches_once(self):
        with patch.object(worker, '_launch') as launch:
            first = self.client.post('/analyze', json={'url': 'https://youtu.be/abcdefghijk'}, headers=self.auth)
            second = self.client.post('/analyze', json={'url': 'https://www.youtube.com/watch?v=abcdefghijk&t=20'}, headers=self.auth)
        self.assertEqual(first.json['job_id'], second.json['job_id'])
        launch.assert_called_once()

    def test_failed_job_preserves_actionable_error_on_every_poll(self):
        job, _ = worker.store.reserve('song')
        worker.store.finish(job, {'success': False, 'error': 'YouTube rechazó la solicitud.',
                                 'code': 'YOUTUBE_BLOCKED', 'fallback': 'upload', 'retry_after': 900})
        for _ in range(2):
            response = self.client.get('/status/' + job, headers=self.auth)
            self.assertEqual(response.json['status'], 'failed')
            self.assertEqual(response.json['fallback'], 'upload')
            self.assertEqual(response.headers['Retry-After'], '900')

    def test_large_upload_reaches_analysis_without_youtube_and_is_deleted(self):
        token = self.ticket()
        headers = {'Origin': self.origin, 'X-Upload-Token': token}
        preflight = self.client.options('/analyze-file', headers={'Origin': self.origin, 'Access-Control-Request-Headers': 'x-upload-token'})
        self.assertEqual(preflight.headers['Access-Control-Allow-Origin'], self.origin)
        def analyze(path):
            self.assertEqual(Path(path).stat().st_size, 6 * 1024 * 1024)
            return {'success': True, 'chords_timeline': [{'time': 0, 'chord': 'C'}]}
        with patch.object(worker, 'analyze_file_path', side_effect=analyze), \
             patch.object(worker, 'analyze_url') as youtube, \
             patch.object(worker, '_launch', side_effect=worker._run_job):
            response = self.client.post('/analyze-file', headers=headers,
                                        data={'audio': (io.BytesIO(b'x' * (6 * 1024 * 1024)), 'demo.wav')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['title'], 'demo')
        self.assertTrue(response.json['success'])
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], self.origin)
        self.assertEqual(list(Path(self.tmp.name).glob('upload-*')), [])
        youtube.assert_not_called()
        replay = self.client.post('/analyze-file', headers=headers, data={'audio': (io.BytesIO(b'x'), 'demo.wav')})
        self.assertEqual(replay.status_code, 401)
        replay.close()
        response.request.environ['wsgi.input'].close()
        response.close()

    def test_empty_and_unsupported_uploads_are_rejected(self):
        for filename, payload in (('song.exe', b'x'), ('song.wav', b'')):
            response = self.client.post('/analyze-file', headers=self.auth, data={'audio': (io.BytesIO(payload), filename)})
            self.assertEqual(response.status_code, 400)

    def test_other_origins_cannot_use_upload_ticket(self):
        token = self.ticket()
        response = self.client.post('/analyze-file', headers={'Origin': 'https://evil.example', 'X-Upload-Token': token})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_oversized_request_is_rejected_before_analysis(self):
        with patch.dict(worker.app.config, {'MAX_CONTENT_LENGTH': 1024}), \
             patch.object(worker, '_launch') as launch:
            response = self.client.post('/analyze-file', headers=self.auth,
                                        data={'audio': (io.BytesIO(b'x' * 2048), 'large.wav')})
        self.assertEqual(response.status_code, 413)
        self.assertFalse(response.json['success'])
        launch.assert_not_called()
        response.request.environ['wsgi.input'].close()
        response.close()


if __name__ == '__main__':
    unittest.main()

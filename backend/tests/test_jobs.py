import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from backend.extractor_server.jobs import JobStore


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'jobs.sqlite3'
        self.store = JobStore(self.path, capacity=1)

    def test_concurrent_identical_requests_only_launch_one_job(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.reserve('same-song'), range(8)))
        self.assertEqual(len({job for job, _ in results}), 1)
        self.assertEqual(sum(created for _, created in results), 1)

    def test_capacity_is_atomic_for_different_songs(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: self.store.reserve(str(i)), range(8)))
        self.assertEqual(sum(created for _, created in results), 1)

    def test_result_can_be_polled_repeatedly_and_reused(self):
        job, _ = self.store.reserve('song')
        self.store.finish(job, {'success': True, 'chords_timeline': []})
        self.assertEqual(self.store.get(job), self.store.get(job))
        self.assertEqual(self.store.reserve('song'), (job, False))

    def test_failed_result_releases_slot_and_can_retry(self):
        job, _ = self.store.reserve('song')
        self.store.finish(job, {'success': False, 'code': 'YOUTUBE_BLOCKED', 'error': 'blocked'})
        self.assertEqual(self.store.get(job)['status'], 'failed')
        next_job, created = self.store.reserve('song')
        self.assertTrue(created)
        self.assertNotEqual(job, next_job)

    def test_restart_releases_orphaned_jobs(self):
        job, _ = self.store.reserve('song')
        restarted = JobStore(self.path)
        self.assertEqual(restarted.get(job)['status'], 'failed')
        self.assertTrue(restarted.reserve('other')[1])

    def test_expired_results_are_not_reused(self):
        job, _ = self.store.reserve('song')
        self.store.finish(job, {'success': True})
        with patch('backend.extractor_server.jobs.time.time', return_value=10**12):
            self.assertIsNone(self.store.get(job))
            self.assertTrue(self.store.reserve('song')[1])

    def test_upload_ticket_is_single_use_bound_to_origin_and_expires(self):
        origin = 'https://chordlens.example'
        token = self.store.issue_ticket(origin)
        self.assertFalse(self.store.consume_ticket(token, 'https://other.example'))
        self.assertTrue(self.store.consume_ticket(token, origin))
        self.assertFalse(self.store.consume_ticket(token, origin))
        with patch('backend.extractor_server.jobs.time.time', return_value=10**12):
            self.assertFalse(self.store.allows_origin(origin))


if __name__ == '__main__':
    unittest.main()

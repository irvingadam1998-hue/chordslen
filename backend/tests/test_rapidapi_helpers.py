import unittest

from backend.scripts.analyze import _extract_rapidapi_download_url


class TestRapidApiHelpers(unittest.TestCase):
    def test_rapidapi_download_url_extraction(self):
        payload = {
            'status': 'ok',
            'title': 'Demo',
            'link': 'https://example.com/download.mp3',
        }
        self.assertEqual(_extract_rapidapi_download_url(payload), 'https://example.com/download.mp3')

        payload2 = {'status': 'ok', 'result': {'downloadUrl': 'https://cdn.example.com/audio.mp3'}}
        self.assertEqual(_extract_rapidapi_download_url(payload2), 'https://cdn.example.com/audio.mp3')


if __name__ == '__main__':
    unittest.main()

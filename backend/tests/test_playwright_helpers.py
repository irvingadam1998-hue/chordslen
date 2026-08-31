import os
import unittest

from backend.scripts.analyze import (
    _extract_rapidapi_download_url,
    _looks_like_googlevideo_audio_url,
    _playwright_proxy_settings,
)


class TestPlaywrightHelpers(unittest.TestCase):
    def test_proxy_settings_parse(self):
        os.environ['RESIDENTIAL_PROXY'] = 'http://user:pass@proxy.example.com:8080'
        proxy = _playwright_proxy_settings()
        self.assertEqual(proxy['server'], 'http://proxy.example.com:8080')
        self.assertEqual(proxy['username'], 'user')
        self.assertEqual(proxy['password'], 'pass')

    def test_googlevideo_audio_url_detection(self):
        url = 'https://rr2---sn-abc.googlevideo.com/videoplayback?expire=123&mime=audio%2Fwebm&source=youtube'
        self.assertTrue(_looks_like_googlevideo_audio_url(url))

        self.assertFalse(_looks_like_googlevideo_audio_url('https://example.com/video.mp4'))

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

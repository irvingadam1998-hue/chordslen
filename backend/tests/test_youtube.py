import base64
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import youtube
from yt_dlp.utils import DownloadError


class YouTubeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'YOUTUBE_MIN_INTERVAL_SECONDS': '0'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.binaries = patch.object(youtube.shutil, 'which', side_effect=lambda name: '/usr/bin/' + name if name in ('node', 'ffmpeg') else None)
        self.binaries.start()
        self.addCleanup(self.binaries.stop)
        youtube._blocked_until = 0
        youtube._last_download = 0

    def test_url_canonicalization_and_host_validation(self):
        for url in (
            'https://youtu.be/abcdefghijk?t=30',
            'https://youtube.com/watch?list=ignored&v=abcdefghijk',
            'https://music.youtube.com/watch?v=abcdefghijk',
            'https://www.youtube.com/shorts/abcdefghijk',
        ):
            self.assertEqual(youtube.extract_video_id(url), 'abcdefghijk')
        for url in ('https://evil.test/youtube.com/watch?v=abcdefghijk',
                    'https://youtube.com.evil.test/watch?v=abcdefghijk',
                    'file:///etc/passwd', 'https://youtube.com/watch?v=short', None):
            self.assertIsNone(youtube.extract_video_id(url))

    def test_defaults_include_js_and_do_not_force_old_clients(self):
        options = youtube.build_options(self.tmp.name)
        self.assertIn('node', options['js_runtimes'])
        self.assertNotIn('extractor_args', options)
        self.assertTrue(options['noplaylist'])
        self.assertEqual(options['retries'], 1)

    def test_explicit_cookies_are_copied_privately_and_po_token_is_a_list(self):
        source = Path(self.tmp.name) / 'source.txt'
        source.write_text('# Netscape HTTP Cookie File\n')
        with patch.dict(os.environ, {'YOUTUBE_COOKIES_FILE': str(source),
                                     'YTDLP_PO_TOKEN': 'example', 'YTDLP_PLAYER_CLIENTS': 'mweb'}):
            options = youtube.build_options(self.tmp.name)
        copy = Path(options['cookiefile'])
        self.assertNotEqual(copy, source)
        self.assertEqual(copy.stat().st_mode & 0o777, 0o600)
        self.assertEqual(options['extractor_args']['youtube']['po_token'], ['mweb.gvs+example'])

    def test_invalid_cookie_configuration_is_not_reported_as_youtube_block(self):
        with patch.dict(os.environ, {'YOUTUBE_COOKIES_B64': 'invalid!'}):
            with self.assertRaises(youtube.YouTubeError) as raised:
                youtube.build_options(self.tmp.name)
        self.assertEqual(raised.exception.code, 'EXTRACTOR_CONFIG')

    def test_one_extraction_provides_both_audio_and_metadata(self):
        with patch('yt_dlp.YoutubeDL') as factory:
            client = factory.return_value.__enter__.return_value
            def extract(url, download):
                self.assertEqual(url, 'https://www.youtube.com/watch?v=abcdefghijk')
                self.assertTrue(download)
                (Path(self.tmp.name) / 'audio.wav').write_bytes(b'audio')
                return {'title': 'Test', 'artist': 'Artist'}
            client.extract_info.side_effect = extract
            with patch.dict(os.environ, {'YOUTUBE_COOKIES_B64': base64.b64encode(b'# Netscape HTTP Cookie File\n').decode()}):
                path, title, artist = youtube.download_audio('https://youtu.be/abcdefghijk?list=ignore', self.tmp.name)
            self.assertEqual((title, artist), ('Test', 'Artist'))
            self.assertTrue(Path(path).exists())
            self.assertFalse((Path(self.tmp.name) / 'cookies.txt').exists())
            client.extract_info.assert_called_once()

    def test_bot_block_stops_subsequent_network_requests(self):
        with patch('yt_dlp.YoutubeDL') as factory:
            client = factory.return_value.__enter__.return_value
            client.extract_info.side_effect = DownloadError("Sign in to confirm you’re not a bot")
            for _ in range(2):
                with self.assertRaises(youtube.YouTubeError) as raised:
                    youtube.download_audio('https://youtu.be/abcdefghijk', self.tmp.name)
                self.assertEqual(raised.exception.code, 'YOUTUBE_BLOCKED')
                self.assertGreater(raised.exception.retry_after, 0)
            client.extract_info.assert_called_once()

    def test_unavailable_video_does_not_block_other_videos(self):
        self.assertEqual(youtube.classify_error('Private video').code, 'YOUTUBE_UNAVAILABLE')
        self.assertEqual(youtube.cooldown_remaining(), 0)

    def test_invalid_ranges(self):
        for start, end in ((-1, 1), (0, 61), (0, float('nan')), (0, float('inf')), (True, 2), (5, 5)):
            self.assertFalse(youtube.validate_range(start, end))
        self.assertTrue(youtube.validate_range(20.5, 80.5))


if __name__ == '__main__':
    unittest.main()

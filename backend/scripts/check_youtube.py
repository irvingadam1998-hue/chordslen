"""Run from the deployed worker to distinguish configuration from YouTube rejection."""
import argparse
import json
import tempfile
from importlib.metadata import version
from pathlib import Path

from youtube import download_audio, YouTubeError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL de un video público corto para verificar el servidor')
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix='chordlens_check_') as directory:
            notices = []
            path, title, _ = download_audio(args.url, directory, notices=notices)
            result = {'success': True, 'title': title, 'bytes': Path(path).stat().st_size,
                      'yt_dlp': version('yt-dlp'), 'ejs': version('yt-dlp-ejs'),
                      'warnings': notices}
    except YouTubeError as exc:
        result = exc.result()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

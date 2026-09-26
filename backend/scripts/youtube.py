"""One YouTube download policy shared by analysis, transcription and extraction."""
import base64
import math
import os
import re
import shutil
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class YouTubeError(RuntimeError):
    def __init__(self, message, code='YOUTUBE_UNAVAILABLE', retry_after=0):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after

    def result(self):
        return {
            'success': False, 'error': str(self), 'code': self.code,
            'fallback': 'upload', 'retry_after': self.retry_after,
        }


_download_lock = threading.Lock()
_blocked_until = 0.0
_last_download = 0.0


def extract_video_id(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            return None
        host = (parsed.hostname or '').lower()
        parts = parsed.path.strip('/').split('/')
        if host == 'youtu.be':
            candidate = parts[0]
        elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
            if parsed.path == '/watch':
                candidate = parse_qs(parsed.query).get('v', [''])[0]
            elif len(parts) == 2 and parts[0] in ('embed', 'shorts', 'live'):
                candidate = parts[1]
            else:
                return None
        else:
            return None
        return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else None
    except ValueError:
        return None


def validate_range(start, end):
    return (
        type(start) in (int, float) and type(end) in (int, float)
        and math.isfinite(start) and math.isfinite(end)
        and 0 <= start < end and end - start <= 60
    )


def cooldown_remaining():
    return max(0, math.ceil(_blocked_until - time.monotonic()))


def classify_error(error):
    message = str(error).lower()
    if any(term in message for term in (
        'not a bot', 'confirm you’re not', "confirm you're not", 'http error 429',
        'too many requests', "this content isn't available, try again later",
        'http error 403',
    )):
        return YouTubeError(
            'YouTube está rechazando las solicitudes desde este servidor. '
            'Puedes continuar subiendo el archivo de audio.',
            'YOUTUBE_BLOCKED', int(os.environ.get('YOUTUBE_COOLDOWN_SECONDS', '900')),
        )
    if any(term in message for term in ('private video', 'video unavailable', 'video is unavailable', 'removed', 'age-restricted', 'sign in to confirm your age')):
        return YouTubeError('Este video no está disponible para el análisis. Puedes subir un archivo de audio.')
    return YouTubeError('No se pudo obtener el audio de YouTube. Intenta más tarde o sube el archivo de audio.')


def build_options(workdir):
    workdir = Path(workdir)
    options = {
        'outtmpl': str(workdir / 'audio.%(ext)s'),
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'noprogress': True,
        'socket_timeout': 30,
        'retries': 1,
        'fragment_retries': 1,
        'extractor_retries': 1,
        'concurrent_fragment_downloads': 1,
        'sleep_interval_requests': 1,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
    }
    node = os.environ.get('YTDLP_NODE_PATH') or shutil.which('node')
    runtimes = {}
    if shutil.which('deno'):
        runtimes['deno'] = {}
    if node:
        runtimes['node'] = {'path': node}
    if not runtimes:
        raise YouTubeError('El servidor necesita Node.js 22+ o Deno para procesar YouTube.', 'EXTRACTOR_CONFIG')
    options['js_runtimes'] = runtimes
    if not shutil.which('ffmpeg'):
        raise YouTubeError('El servidor necesita FFmpeg para procesar el audio.', 'EXTRACTOR_CONFIG')

    # Let maintained yt-dlp defaults select compatible clients unless explicitly configured.
    youtube_args = {}
    clients = os.environ.get('YTDLP_PLAYER_CLIENTS', '').strip()
    if clients:
        youtube_args['player_client'] = [part.strip() for part in clients.split(',') if part.strip()]
    token = os.environ.get('YTDLP_PO_TOKEN', '').strip()
    if token:
        client = os.environ.get('YTDLP_PO_TOKEN_CLIENT', 'mweb.gvs').strip()
        youtube_args['po_token'] = [f'{client}+{token}']
    if youtube_args:
        options['extractor_args'] = {'youtube': youtube_args}

    # A private, per-download copy prevents concurrent writes to configured credentials.
    encoded = os.environ.get('YOUTUBE_COOKIES_B64', '').strip()
    configured = os.environ.get('YOUTUBE_COOKIES_FILE', '').strip()
    cookie_path = workdir / 'cookies.txt'
    try:
        if encoded:
            cookie_path.write_bytes(base64.b64decode(encoded, validate=True))
        elif configured:
            shutil.copyfile(configured, cookie_path)
        if encoded or configured:
            cookie_path.chmod(0o600)
            options['cookiefile'] = str(cookie_path)
    except (ValueError, OSError) as exc:
        raise YouTubeError('La configuración de cookies del servidor no es válida.', 'EXTRACTOR_CONFIG') from exc
    return options


def download_audio(url, workdir, start=None, end=None):
    """Download once, returning audio and metadata from the same extraction."""
    global _blocked_until, _last_download
    import yt_dlp

    video_id = extract_video_id(url)
    if not video_id:
        raise YouTubeError('Introduce un enlace válido de un video de YouTube.', 'INVALID_URL')
    if (start is not None or end is not None) and not validate_range(start, end):
        raise YouTubeError('Selecciona un fragmento de entre 0 y 60 segundos.', 'INVALID_RANGE')

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    with _download_lock:
        remaining = cooldown_remaining()
        if remaining:
            raise YouTubeError(
                'YouTube está rechazando las solicitudes. Puedes continuar subiendo el archivo de audio.',
                'YOUTUBE_BLOCKED', remaining,
            )
        options = build_options(workdir)
        if start is not None:
            options['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start, end)])
        delay = float(os.environ.get('YOUTUBE_MIN_INTERVAL_SECONDS', '5'))
        time.sleep(max(0, delay - (time.monotonic() - _last_download)))
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
            files = [p for p in workdir.glob('audio.*') if p.suffix in ('.wav', '.m4a', '.mp3', '.webm', '.opus', '.ogg') and p.stat().st_size > 0]
            if not files:
                raise YouTubeError('La descarga no produjo un archivo de audio.')
            audio = next((p for p in files if p.suffix == '.wav'), files[0])
            return str(audio), info.get('title', ''), info.get('artist') or info.get('creator') or info.get('uploader', '')
        except yt_dlp.utils.DownloadError as exc:
            error = classify_error(exc)
            if error.code == 'YOUTUBE_BLOCKED':
                _blocked_until = time.monotonic() + error.retry_after
            raise error from exc
        finally:
            _last_download = time.monotonic()
            (workdir / 'cookies.txt').unlink(missing_ok=True)

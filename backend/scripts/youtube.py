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
_blocked_error = None
_last_download = 0.0

COOKIE_UPDATE = 'Vuelve a exportar cookies.txt y reemplázalo en los archivos secretos del backend de Render.'
COOKIE_INVALID = 'YouTube indica que las cookies de la cuenta ya no son válidas. ' + COOKIE_UPDATE


def cookies_invalid(message):
    message = str(message).lower()
    return any(term in message for term in (
        'cookies are no longer valid', 'cookies have expired',
        'cookies are expired', 'cookies have been rotated',
    ))


class DownloadLogger:
    """Keep the actionable diagnostic even when yt-dlp only emits a warning."""
    def __init__(self):
        self.invalid_cookies = False

    def debug(self, message):
        pass

    def warning(self, message):
        self.invalid_cookies |= cookies_invalid(message)

    def error(self, message):
        self.warning(message)


def validate_cookies(path):
    """Check Netscape dates without exposing cookie values or assuming a fixed lifetime."""
    content = path.read_text(encoding='utf-8')
    if not content.splitlines() or content.splitlines()[0] not in ('# Netscape HTTP Cookie File', '# HTTP Cookie File'):
        raise ValueError('Invalid cookie file header')
    groups = {'session': [], 'login': []}
    found = False
    for line in content.splitlines():
        if line.startswith('#HttpOnly_'):
            line = line[len('#HttpOnly_'):]
        if not line.strip() or line.startswith('#'):
            continue
        fields = line.split('\t')
        if (len(fields) != 7 or not re.fullmatch(r'(?:[0-9]+(?:\.[0-9]+)?)?', fields[4])
                or fields[1] not in ('TRUE', 'FALSE') or fields[3] not in ('TRUE', 'FALSE')
                or (fields[1] == 'TRUE') != fields[0].startswith('.')):
            raise ValueError('Invalid Netscape cookie row')
        domain, _, path_value, _, expires, name, value = fields
        if domain.lstrip('.') not in ('youtube.com', 'www.youtube.com') or path_value != '/':
            continue
        found = True
        # yt-dlp treats both 0 and an empty expiry as session cookies.
        expiration = float(expires or 0)
        expired = expiration > 0 and expiration <= time.time()
        group = ('session' if name in ('SAPISID', '__Secure-1PAPISID', '__Secure-3PAPISID')
                 else 'login' if name == 'LOGIN_INFO' else None)
        if group and value:
            groups[group].append(expired)
    if not found:
        raise ValueError('No YouTube cookies')
    if any(expirations and all(expirations) for expirations in groups.values()):
        raise YouTubeError('Las cookies de inicio de sesión de YouTube han vencido. ' + COOKIE_UPDATE,
                           'YOUTUBE_COOKIES_EXPIRED')


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


def classify_error(error, *, cookies_configured=False, invalid_cookies=False):
    message = str(error).lower()
    cooldown = int(os.environ.get('YOUTUBE_COOLDOWN_SECONDS', '900'))
    if invalid_cookies or cookies_invalid(message):
        return YouTubeError(COOKIE_INVALID, 'YOUTUBE_COOKIES_INVALID', cooldown)
    if cookies_configured and any(term in message for term in (
        'not a bot', 'confirm you’re not', "confirm you're not",
    )):
        return YouTubeError(
            'YouTube pide verificar la sesión aunque hay cookies configuradas. ' + COOKIE_UPDATE +
            ' Si el aviso continúa con cookies nuevas, puede ser un bloqueo de la IP del servidor; '
            'este rechazo no confirma que hayan vencido.',
            'YOUTUBE_COOKIES_REJECTED', cooldown,
        )
    if any(term in message for term in (
        'not a bot', 'confirm you’re not', "confirm you're not", 'http error 429',
        'too many requests', "this content isn't available, try again later",
        'http error 403',
    )):
        return YouTubeError(
            'YouTube está rechazando las solicitudes desde este servidor. '
            'Puedes continuar subiendo el archivo de audio.',
            'YOUTUBE_BLOCKED', cooldown,
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
            validate_cookies(cookie_path)
            options['cookiefile'] = str(cookie_path)
    except YouTubeError:
        cookie_path.unlink(missing_ok=True)
        raise
    except (ValueError, OSError):
        cookie_path.unlink(missing_ok=True)
        raise YouTubeError('No se pudo leer un archivo válido de cookies de YouTube. ' + COOKIE_UPDATE,
                           'YOUTUBE_COOKIES_CONFIG') from None
    return options


def download_audio(url, workdir, start=None, end=None, *, notices=None):
    """Download once, returning audio and metadata from the same extraction."""
    global _blocked_until, _blocked_error, _last_download
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
            if _blocked_error is not None:
                raise YouTubeError(str(_blocked_error), _blocked_error.code, remaining)
            raise YouTubeError(
                'YouTube está rechazando las solicitudes. Puedes continuar subiendo el archivo de audio.',
                'YOUTUBE_BLOCKED', remaining,
            )
        options = build_options(workdir)
        logger = DownloadLogger()
        options['logger'] = logger
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
            if logger.invalid_cookies and notices is not None:
                notices.append({'code': 'YOUTUBE_COOKIES_INVALID', 'message': COOKIE_INVALID})
            return str(audio), info.get('title', ''), info.get('artist') or info.get('creator') or info.get('uploader', '')
        except yt_dlp.utils.DownloadError as exc:
            error = classify_error(exc, cookies_configured='cookiefile' in options,
                                   invalid_cookies=logger.invalid_cookies)
            if error.retry_after:
                _blocked_until = time.monotonic() + error.retry_after
                _blocked_error = error
            raise error from exc
        finally:
            _last_download = time.monotonic()
            (workdir / 'cookies.txt').unlink(missing_ok=True)

#!/usr/bin/env python3
import atexit
import base64
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file


app = Flask(__name__)

API_KEY = os.environ.get('API_KEY', '').strip()
TMP_ROOT = Path(os.environ.get('EXTRACTOR_TMP_DIR', tempfile.gettempdir())) / 'chordlens-extractor'
TTL_SECONDS = int(os.environ.get('EXTRACTOR_FILE_TTL_SECONDS', '900'))
TMP_ROOT.mkdir(parents=True, exist_ok=True)

_file_index: dict[str, dict[str, object]] = {}
_lock = threading.Lock()


def _check_auth():
    if not API_KEY:
        return None
    provided = request.headers.get('x-api-key') or request.headers.get('authorization', '').removeprefix('Bearer ').strip()
    if provided != API_KEY:
        return jsonify({'success': False, 'error': 'API key inválida o ausente'}), 401
    return None


def _parse_clients():
    raw = os.environ.get('YTDLP_PLAYER_CLIENTS', '').strip()
    if raw:
        clients = [part.strip() for part in raw.split(',') if part.strip()]
        if clients:
            return clients
    return ['android', 'ios', 'tv_embedded']


def _cookies_file():
    b64 = os.environ.get('YOUTUBE_COOKIES_B64', '').strip()
    if b64:
        out = TMP_ROOT / 'cookies.txt'
        out.write_text(base64.b64decode(b64).decode('utf-8'), encoding='utf-8')
        return str(out)

    candidate = os.environ.get('YOUTUBE_COOKIES_FILE', '').strip()
    if candidate and os.path.isfile(candidate):
        return candidate
    return None


def _yt_dlp_opts(outtmpl: str):
    extractor_args = {'youtube': {'player_client': _parse_clients()}}
    po_token = os.environ.get('YTDLP_PO_TOKEN', '').strip()
    po_client = os.environ.get('YTDLP_PO_TOKEN_CLIENT', 'android.gvs').strip() or 'android.gvs'
    if po_token:
        extractor_args['youtube']['po_token'] = f'{po_client}+{po_token}'

    opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'extractor_args': extractor_args,
        'format': 'bestaudio/best',
    }

    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)

    cookiefile = _cookies_file()
    if cookiefile:
        opts['cookiefile'] = cookiefile

    return opts


def _find_audio_file(workdir: Path):
    candidates = []
    for path in workdir.iterdir():
        if path.is_file() and path.suffix.lower() in {'.wav', '.m4a', '.mp3', '.webm', '.opus', '.ogg', '.aac'}:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    chosen = candidates[0]
    if chosen.stat().st_size < 10000:
        return None
    return chosen


def _extract_metadata(url: str):
    try:
        import yt_dlp
    except ImportError:
        return '', ''

    opts = _yt_dlp_opts(str(TMP_ROOT / 'noop.%(ext)s'))
    opts['skip_download'] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get('title', '')
        artist = info.get('artist') or info.get('creator') or info.get('uploader', '')
        return title, artist
    except Exception:
        return '', ''


def _download_audio(url: str, start: float | None = None, end: float | None = None):
    try:
        import yt_dlp
    except ImportError as e:
        raise RuntimeError(f'yt-dlp no está instalado: {e}')

    job_id = uuid.uuid4().hex
    workdir = TMP_ROOT / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    opts = _yt_dlp_opts(str(workdir / 'audio.%(ext)s'))
    opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}]

    if start is not None and end is not None:
        opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start, end)])
        opts['force_keyframes_at_cuts'] = True

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(str(e))

    audio_path = _find_audio_file(workdir)
    if not audio_path:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError('yt-dlp no produjo un audio utilizable')

    title, artist = _extract_metadata(url)
    return audio_path, title, artist


def _register_file(path: Path):
    file_id = uuid.uuid4().hex
    with _lock:
        _file_index[file_id] = {
            'path': str(path),
            'expires_at': time.time() + TTL_SECONDS,
        }
    return file_id


def _cleanup_expired():
    now = time.time()
    expired = []
    with _lock:
        for file_id, meta in list(_file_index.items()):
            if float(meta['expires_at']) <= now:
                expired.append((file_id, str(meta['path'])))
                _file_index.pop(file_id, None)
    for _, path in expired:
        try:
            parent = Path(path).parent
            shutil.rmtree(parent, ignore_errors=True)
        except Exception:
            pass


def _cleanup_loop():
    while True:
        _cleanup_expired()
        time.sleep(60)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'time': int(time.time())})


@app.route('/audio', methods=['POST'])
def audio():
    auth = _check_auth()
    if auth:
        return auth

    data = request.get_json(silent=True) or {}
    url = str(data.get('url', '')).strip()
    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    try:
        audio_path, title, artist = _download_audio(url)
        file_id = _register_file(audio_path)
        return jsonify({
            'success': True,
            'audio_url': request.url_root.rstrip('/') + f'/files/{file_id}',
            'title': title,
            'artist': artist,
            'ext': audio_path.suffix.lstrip('.'),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/fragment', methods=['POST'])
def fragment():
    auth = _check_auth()
    if auth:
        return auth

    data = request.get_json(silent=True) or {}
    url = str(data.get('url', '')).strip()
    start = data.get('start')
    end = data.get('end')
    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return jsonify({'success': False, 'error': 'start y end requeridos'}), 400
    if float(end) <= float(start):
        return jsonify({'success': False, 'error': 'end debe ser mayor que start'}), 400
    if float(end) - float(start) > 60:
        return jsonify({'success': False, 'error': 'Máximo 60 segundos por fragmento'}), 400

    try:
        audio_path, _, _ = _download_audio(url, float(start), float(end))
        file_id = _register_file(audio_path)
        return jsonify({
            'success': True,
            'audio_url': request.url_root.rstrip('/') + f'/files/{file_id}',
            'ext': audio_path.suffix.lstrip('.'),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/files/<file_id>', methods=['GET'])
def files(file_id: str):
    _cleanup_expired()
    with _lock:
        meta = _file_index.get(file_id)
    if not meta:
        return jsonify({'success': False, 'error': 'Archivo no encontrado o expirado'}), 404

    path = Path(str(meta['path']))
    if not path.is_file():
        return jsonify({'success': False, 'error': 'Archivo no disponible'}), 404
    return send_file(path, mimetype='audio/wav', as_attachment=False, download_name=path.name)


@atexit.register
def _cleanup_all():
    shutil.rmtree(TMP_ROOT, ignore_errors=True)


if __name__ == '__main__':
    threading.Thread(target=_cleanup_loop, daemon=True).start()
    port = int(os.environ.get('PORT', '5002'))
    app.run(host='0.0.0.0', port=port, debug=False)

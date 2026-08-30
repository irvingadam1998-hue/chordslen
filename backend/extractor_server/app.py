#!/usr/bin/env python3
import atexit
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
try:
    from analyze import analyze_url
    from transcribe import transcribe as transcribe_fragment
except ImportError as e:
    analyze_url = None
    transcribe_fragment = None
    print(f'[extractor_server] warning: no analysis/transcribe modules loaded: {e}', file=sys.stderr)


app = Flask(__name__)

API_KEY = os.environ.get('API_KEY', '').strip()
TMP_ROOT = Path(os.environ.get('EXTRACTOR_TMP_DIR', tempfile.gettempdir())) / 'chordlens-extractor'
TTL_SECONDS = int(os.environ.get('EXTRACTOR_FILE_TTL_SECONDS', '60'))
TMP_ROOT.mkdir(parents=True, exist_ok=True)

_file_index: dict[str, dict[str, object]] = {}
_lock = threading.Lock()
_jobs: dict[str, dict[str, object]] = {}
_jobs_lock = threading.Lock()
JOB_TTL_SECONDS = int(os.environ.get('JOB_TTL_SECONDS', '300'))
MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', '1'))
JOBS_DB_PATH = TMP_ROOT / 'jobs.sqlite3'


def _init_jobs_db():
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            '''
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at)')
        conn.commit()


_init_jobs_db()


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
    if TTL_SECONDS <= 0:
        try:
            if path.is_file():
                path.unlink()
            parent = path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass
        return None

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
        _cleanup_jobs()
        time.sleep(60)


def _cleanup_jobs():
    now = time.time()
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute(
            'DELETE FROM jobs WHERE updated_at < ? AND status != ?',
            (now - JOB_TTL_SECONDS, 'processing'),
        )
        conn.commit()


def _count_active_jobs():
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM jobs WHERE status = 'processing'"
        ).fetchone()
        return int(row[0] or 0)


def _delete_job(job_id: str):
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
        conn.commit()


def _create_job(job_id: str):
    now = time.time()
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute(
            'INSERT OR REPLACE INTO jobs(job_id, status, result, error, created_at, updated_at) VALUES (?, ?, NULL, NULL, ?, ?)',
            (job_id, 'processing', now, now),
        )
        conn.commit()


def _set_job_done(job_id: str, result: dict):
    now = time.time()
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute(
            'UPDATE jobs SET status = ?, result = ?, error = NULL, updated_at = ? WHERE job_id = ?',
            ('done', json.dumps(result, ensure_ascii=False), now, job_id),
        )
        conn.commit()


def _set_job_failed(job_id: str, error: str):
    now = time.time()
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        conn.execute(
            'UPDATE jobs SET status = ?, error = ?, result = NULL, updated_at = ? WHERE job_id = ?',
            ('failed', error, now, job_id),
        )
        conn.commit()


def _get_job(job_id: str):
    with sqlite3.connect(JOBS_DB_PATH) as conn:
        row = conn.execute(
            'SELECT job_id, status, result, error, created_at, updated_at FROM jobs WHERE job_id = ?',
            (job_id,),
        ).fetchone()
    if not row:
        return None
    payload = {
        'job_id': row[0],
        'status': row[1],
        'result': json.loads(row[2]) if row[2] else None,
        'error': row[3],
        'created_at': row[4],
        'updated_at': row[5],
    }
    return payload


def _run_analysis_job(job_id: str, url: str):
    try:
        result = analyze_url(url)
        _set_job_done(job_id, result)
    except Exception as exc:
        _set_job_failed(job_id, str(exc))


def _run_transcribe_job(job_id: str, url: str, start: float, end: float):
    try:
        result = transcribe_fragment(url, start, end)
        _set_job_done(job_id, result)
    except Exception as exc:
        _set_job_failed(job_id, str(exc))


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'time': int(time.time())})


@app.route('/analyze', methods=['POST'])
def analyze():
    auth = _check_auth()
    if auth:
        return auth

    data = request.get_json(silent=True) or {}
    url = str(data.get('url', '')).strip()
    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    if analyze_url is None:
        return jsonify({'success': False, 'error': 'Módulo de análisis no disponible'}), 500

    if _count_active_jobs() >= MAX_CONCURRENT_JOBS:
        return jsonify({
            'success': False,
            'error': f'Hay un análisis en curso. Espera a que termine antes de enviar otro. (máximo {MAX_CONCURRENT_JOBS})',
        }), 429

    job_id = uuid.uuid4().hex
    _create_job(job_id)

    threading.Thread(target=_run_analysis_job, args=(job_id, url), daemon=True).start()
    return jsonify({'job_id': job_id, 'status': 'processing'}), 202


@app.route('/status/<job_id>', methods=['GET'])
def analyze_status(job_id: str):
    auth = _check_auth()
    if auth:
        return auth

    _cleanup_jobs()
    job = _get_job(job_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

    if job.get('status') == 'processing':
        return jsonify({'job_id': job_id, 'status': 'processing'}), 202

    if job.get('status') == 'failed':
        _delete_job(job_id)
        return jsonify({'job_id': job_id, 'status': 'failed', 'error': job.get('error', 'Error desconocido')}), 500

    result = job.get('result', {}) or {}
    _delete_job(job_id)
    return jsonify({'job_id': job_id, 'status': 'done', **result}), 200


@app.route('/transcribe', methods=['POST'])
def transcribe_route():
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
        return jsonify({'success': False, 'error': 'Máximo 60 segundos por transcripción'}), 400

    if transcribe_fragment is None:
        return jsonify({'success': False, 'error': 'Módulo de transcripción no disponible'}), 500

    if _count_active_jobs() >= MAX_CONCURRENT_JOBS:
        return jsonify({
            'success': False,
            'error': f'Hay una transcripción en curso. Espera a que termine antes de enviar otra. (máximo {MAX_CONCURRENT_JOBS})',
        }), 429

    job_id = uuid.uuid4().hex
    _create_job(job_id)

    threading.Thread(
        target=_run_transcribe_job,
        args=(job_id, url, float(start), float(end)),
        daemon=True,
    ).start()
    return jsonify({'job_id': job_id, 'status': 'processing'}), 202


@app.route('/transcribe/status/<job_id>', methods=['GET'])
def transcribe_status(job_id: str):
    auth = _check_auth()
    if auth:
        return auth

    _cleanup_jobs()
    job = _get_job(job_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

    if job.get('status') == 'processing':
        return jsonify({'job_id': job_id, 'status': 'processing'}), 202

    if job.get('status') == 'failed':
        _delete_job(job_id)
        return jsonify({'job_id': job_id, 'status': 'failed', 'error': job.get('error', 'Error desconocido')}), 500

    result = job.get('result', {}) or {}
    _delete_job(job_id)
    return jsonify({'job_id': job_id, 'status': 'done', **result}), 200


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

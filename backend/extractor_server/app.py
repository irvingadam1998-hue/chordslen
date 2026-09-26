#!/usr/bin/env python3
"""ChordLens worker: one process, bounded jobs, reusable results and direct uploads."""
import importlib.util
import hmac
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze import analyze_url, analyze_file_path
from transcribe import transcribe as transcribe_fragment
from youtube import download_audio, extract_video_id, validate_range, YouTubeError, cooldown_remaining
try:
    from .jobs import JobStore
except ImportError:
    from jobs import JobStore

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', '').strip()
TMP_ROOT = Path(os.environ.get('EXTRACTOR_TMP_DIR', tempfile.gettempdir())) / 'chordlens-extractor'
TMP_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.environ.get('MAX_UPLOAD_MB', '50')) * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES + 64 * 1024
TTL_SECONDS = max(60, int(os.environ.get('EXTRACTOR_FILE_TTL_SECONDS', '900')))
store = JobStore(TMP_ROOT / 'jobs.sqlite3',
                 ttl=int(os.environ.get('JOB_TTL_SECONDS', '3600')),
                 capacity=int(os.environ.get('MAX_CONCURRENT_JOBS', '1')))
_file_index = {}
_file_lock = threading.Lock()
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.weba', '.webm'}


def _check_auth():
    provided = request.headers.get('x-api-key') or request.headers.get('authorization', '').removeprefix('Bearer ')
    if API_KEY and not hmac.compare_digest(provided or '', API_KEY):
        return jsonify({'success': False, 'error': 'API key inválida o ausente'}), 401
    return None


def _error(message, status=400, code=None):
    return jsonify({'success': False, 'error': message, 'code': code}), status


@app.after_request
def upload_cors(response):
    origin = request.headers.get('Origin', '')
    if request.path == '/analyze-file' and origin and store.allows_origin(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Upload-Token'
        response.headers['Vary'] = 'Origin'
    return response


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exception):
    return _error(f'El archivo supera el límite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.', 413)


@app.route('/health')
def health():
    dependencies = {name: importlib.util.find_spec(name) is not None for name in ('librosa', 'yt_dlp', 'yt_dlp_ejs')}
    dependencies['ffmpeg'] = bool(shutil.which('ffmpeg'))
    dependencies['javascript'] = bool(shutil.which('deno') or shutil.which(os.environ.get('YTDLP_NODE_PATH', 'node')))
    ready = all(dependencies.values())
    return jsonify({'ok': ready, 'dependencies': dependencies, 'youtube_retry_after': cooldown_remaining()}), 200 if ready else 503


def _run_job(job_id, function, args, cleanup=None):
    try:
        store.finish(job_id, function(*args))
    except Exception:
        app.logger.exception('Job %s failed', job_id)
        store.finish(job_id, {'success': False, 'error': 'No se pudo procesar el audio. Intenta con otro archivo.'})
    finally:
        if cleanup:
            Path(cleanup).unlink(missing_ok=True)


def _launch(job_id, function, args, cleanup=None):
    try:
        threading.Thread(target=_run_job, args=(job_id, function, args, cleanup), daemon=True).start()
    except Exception:
        if cleanup:
            Path(cleanup).unlink(missing_ok=True)
        store.finish(job_id, {'success': False, 'error': 'No se pudo iniciar el análisis.'})
        raise


def _job_response(job_id):
    job = store.get(job_id)
    if not job:
        return _error('El análisis expiró o no existe. Inicia uno nuevo.', 404)
    if job['status'] == 'processing':
        return jsonify({'job_id': job_id, 'status': 'processing'}), 202
    result = job['result'] or {'success': False, 'error': job['error']}
    response = jsonify({**result, 'job_id': job_id, 'status': job['status']})
    if result.get('retry_after'):
        response.headers['Retry-After'] = str(result['retry_after'])
    # Keep terminal results until TTL: reconnects and other viewers can read them.
    return response, 200


def _start_job(key, function, args):
    job_id, created = store.reserve(key)
    if not job_id:
        response = jsonify({'success': False, 'code': 'WORKER_BUSY', 'error': 'Hay un análisis en curso. Vuelve a intentar en unos segundos.'})
        response.headers['Retry-After'] = '10'
        return response, 429
    if created:
        _launch(job_id, function, args)
    return _job_response(job_id)


@app.route('/analyze', methods=['POST'])
def analyze():
    auth = _check_auth()
    if auth:
        return auth
    data = request.get_json(silent=True)
    url = data.get('url') if isinstance(data, dict) else None
    video_id = extract_video_id(url)
    if not video_id:
        return _error('Introduce un enlace válido de un video de YouTube.', code='INVALID_URL')
    return _start_job(f'analyze:v1:{video_id}', analyze_url, (url,))


@app.route('/status/<job_id>')
@app.route('/transcribe/status/<job_id>')
def status(job_id):
    auth = _check_auth()
    return auth if auth else _job_response(job_id)


@app.route('/transcribe', methods=['POST'])
def transcribe_route():
    auth = _check_auth()
    if auth:
        return auth
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _error('Solicitud inválida.')
    url, start, end = data.get('url'), data.get('start'), data.get('end')
    video_id = extract_video_id(url)
    if not video_id:
        return _error('Introduce un enlace válido de un video de YouTube.', code='INVALID_URL')
    if not validate_range(start, end):
        return _error('Selecciona un fragmento válido de hasta 60 segundos.', code='INVALID_RANGE')
    key = f'transcribe:v1:{video_id}:{float(start)}:{float(end)}'
    return _start_job(key, transcribe_fragment, (url, float(start), float(end)))


@app.route('/upload-ticket', methods=['POST'])
def upload_ticket():
    auth = _check_auth()
    if auth:
        return auth
    data = request.get_json(silent=True) or {}
    origin = data.get('origin', '') if isinstance(data, dict) else ''
    try:
        parsed = urlparse(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError()
    except (ValueError, TypeError):
        return _error('Origen de subida inválido.')
    return jsonify({'token': store.issue_ticket(origin), 'max_bytes': MAX_UPLOAD_BYTES, 'expires_in': 600})


@app.route('/analyze-file', methods=['POST', 'OPTIONS'])
def analyze_file():
    if request.method == 'OPTIONS':
        return '', 204
    token = request.headers.get('X-Upload-Token')
    if token:
        if not store.consume_ticket(token, request.headers.get('Origin', '')):
            return _error('La autorización de subida expiró. Vuelve a seleccionar Analizar.', 401)
    else:
        auth = _check_auth()
        if auth:
            return auth
    audio = request.files.get('audio')
    if not audio or not audio.filename:
        return _error('Selecciona un archivo de audio.')
    filename = secure_filename(audio.filename)
    ext = Path(filename).suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return _error('Formato no soportado. Usa MP3, WAV, OGG, FLAC, M4A, AAC o WebM.')
    job_id, _ = store.reserve()
    if not job_id:
        return _error('Hay un análisis en curso. Vuelve a intentar en unos segundos.', 429, 'WORKER_BUSY')
    path = TMP_ROOT / f'upload-{job_id}{ext}'
    try:
        audio.save(path)
        if not 0 < path.stat().st_size <= MAX_UPLOAD_BYTES:
            path.unlink(missing_ok=True)
            store.finish(job_id, {'success': False, 'error': 'El archivo está vacío o supera el límite de tamaño.'})
            return _error('El archivo está vacío o supera el límite de tamaño.', 400)
        _launch(job_id, _analyze_upload, (str(path), Path(filename).stem), cleanup=path)
    except Exception:
        path.unlink(missing_ok=True)
        store.finish(job_id, {'success': False, 'error': 'No se pudo guardar el archivo de audio.'})
        raise
    return _job_response(job_id)


def _analyze_upload(path, title):
    result = analyze_file_path(path)
    result['title'] = title
    return result


def _serve_download(fragment=False):
    auth = _check_auth()
    if auth:
        return auth
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _error('Solicitud inválida.')
    start, end = (data.get('start'), data.get('end')) if fragment else (None, None)
    if fragment and not validate_range(start, end):
        return _error('Selecciona un fragmento válido de hasta 60 segundos.')
    workdir = Path(tempfile.mkdtemp(prefix='audio-', dir=TMP_ROOT))
    try:
        notices = []
        path, title, artist = download_audio(data.get('url'), workdir, start, end, notices=notices)
        file_id = uuid.uuid4().hex
        with _file_lock:
            _file_index[file_id] = (path, time.time() + TTL_SECONDS)
        return jsonify({'success': True, 'audio_url': request.url_root.rstrip('/') + f'/files/{file_id}',
                        'title': title, 'artist': artist, 'ext': Path(path).suffix.lstrip('.'),
                        'warnings': notices})
    except YouTubeError as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        return jsonify(exc.result()), 503 if exc.retry_after or exc.code.startswith('YOUTUBE_COOKIES_') else 400
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        app.logger.exception('Audio extraction failed')
        return _error('No se pudo obtener el audio.', 500)


@app.route('/audio', methods=['POST'])
def audio():
    return _serve_download()


@app.route('/fragment', methods=['POST'])
def fragment():
    return _serve_download(fragment=True)


@app.route('/files/<file_id>')
def files(file_id):
    auth = _check_auth()
    if auth:
        return auth
    with _file_lock:
        record = _file_index.get(file_id)
    if not record or record[1] <= time.time() or not Path(record[0]).is_file():
        return _error('Archivo expirado o no encontrado.', 404)
    return send_file(record[0], as_attachment=True)


def _cleanup_loop():
    while True:
        time.sleep(60)
        store.cleanup()
        with _file_lock:
            expired = [key for key, (_, expires) in _file_index.items() if expires <= time.time()]
            for key in expired:
                path, _ = _file_index.pop(key)
                shutil.rmtree(Path(path).parent, ignore_errors=True)


threading.Thread(target=_cleanup_loop, daemon=True).start()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5002')), threaded=True)

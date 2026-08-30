#!/usr/bin/env python3
"""
ChordLens Flask API — deploy this on a VPS to bypass Railway's YouTube block.

Setup:
  pip install flask yt-dlp librosa numpy soundfile

Run:
  API_KEY=your_secret python app.py

Or with gunicorn:
  gunicorn -w 2 -b 0.0.0.0:5001 app:app
"""

import sys
import os
import time
import threading
import uuid

from flask import Flask, request, jsonify

# ── Import analysis logic from sibling scripts/ dir ─────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
try:
    from analyze import analyze_url, analyze_file_path
    from transcribe import transcribe
except ImportError as e:
    print(f"ERROR: could not import analyze.py — {e}", file=sys.stderr)
    sys.exit(1)

# ── App ──────────────────────────────────────────────────────────────────────
app = Flask(__name__)

API_KEY = os.environ.get('API_KEY', '').strip()
RATE_LIMIT_SECONDS = 5

# In-memory rate limiter: {ip: last_request_timestamp}
_rate_lock = threading.Lock()
_ip_last = {}

_jobs = {}
_jobs_lock = threading.Lock()


def _get_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        last = _ip_last.get(ip, 0)
        if now - last < RATE_LIMIT_SECONDS:
            return True
        _ip_last[ip] = now
        return False


def _check_auth():
    """Returns error response or None if auth passes."""
    if API_KEY:
        provided = request.headers.get('x-api-key', '')
        if provided != API_KEY:
            return jsonify({'success': False, 'error': 'API key inválida o ausente'}), 401
    ip = _get_ip()
    if _is_rate_limited(ip):
        return jsonify({'success': False, 'error': 'Demasiadas solicitudes. Espera 5 segundos.'}), 429
    return None


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True})


def _run_analysis_job(job_id: str, url: str):
    try:
        result = analyze_url(url)
        with _jobs_lock:
            _jobs[job_id] = {
                'status': 'done',
                'result': result,
            }
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = {
                'status': 'failed',
                'error': str(e),
            }


@app.route('/analyze', methods=['POST'])
def analyze():
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname not in ('www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com'):
            return jsonify({'success': False, 'error': 'La URL debe ser de YouTube'}), 400
    except Exception:
        return jsonify({'success': False, 'error': 'URL inválida'}), 400

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {'status': 'processing'}

    threading.Thread(target=_run_analysis_job, args=(job_id, url), daemon=True).start()
    return jsonify({'job_id': job_id, 'status': 'processing'}), 202


@app.route('/status/<job_id>', methods=['GET'])
def analyze_status(job_id: str):
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    with _jobs_lock:
        job = _jobs.get(job_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

    if job.get('status') == 'processing':
        return jsonify({'job_id': job_id, 'status': 'processing'}), 202

    if job.get('status') == 'failed':
        return jsonify({'job_id': job_id, 'status': 'failed', 'error': job.get('error', 'Error desconocido')}), 500

    result = job.get('result', {})
    return jsonify({'job_id': job_id, 'status': 'done', **result}), 200


def _run_transcription_job(job_id: str, url: str, start: float, end: float):
    try:
        result = transcribe(url, float(start), float(end))
        with _jobs_lock:
            _jobs[job_id] = {
                'status': 'done',
                'result': result,
            }
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = {
                'status': 'failed',
                'error': str(e),
            }


@app.route('/transcribe', methods=['POST'])
def transcribe_route():
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    url = str(data.get('url', '')).strip()
    start = data.get('start')
    end = data.get('end')

    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return jsonify({'success': False, 'error': 'start y end requeridos'}), 400
    if end <= start:
        return jsonify({'success': False, 'error': 'end debe ser mayor que start'}), 400
    if end - start > 60:
        return jsonify({'success': False, 'error': 'Máximo 60 segundos por transcripción'}), 400

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {'status': 'processing'}

    threading.Thread(target=_run_transcription_job, args=(job_id, url, float(start), float(end)), daemon=True).start()
    return jsonify({'job_id': job_id, 'status': 'processing'}), 202


@app.route('/transcribe/status/<job_id>', methods=['GET'])
def transcribe_status(job_id: str):
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    with _jobs_lock:
        job = _jobs.get(job_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job no encontrado'}), 404

    if job.get('status') == 'processing':
        return jsonify({'job_id': job_id, 'status': 'processing'}), 202

    if job.get('status') == 'failed':
        return jsonify({'job_id': job_id, 'status': 'failed', 'error': job.get('error', 'Error desconocido')}), 500

    result = job.get('result', {})
    return jsonify({'job_id': job_id, 'status': 'done', **result}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f'[ChordLens Flask] starting on port {port}')
    print(f'[ChordLens Flask] API key: {"set" if API_KEY else "NOT SET (open access)"}')
    app.run(host='0.0.0.0', port=port, debug=False)

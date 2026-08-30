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


@app.route('/analyze', methods=['POST'])
def analyze():
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    # Validate YouTube URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname not in ('www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com'):
            return jsonify({'success': False, 'error': 'La URL debe ser de YouTube'}), 400
    except Exception:
        return jsonify({'success': False, 'error': 'URL inválida'}), 400

    try:
        result = analyze_url(url)
        status = 200 if result.get('success') else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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

    try:
        result = transcribe(url, float(start), float(end))
        status = 200 if result.get('success') else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f'[ChordLens Flask] starting on port {port}')
    print(f'[ChordLens Flask] API key: {"set" if API_KEY else "NOT SET (open access)"}')
    app.run(host='0.0.0.0', port=port, debug=False)

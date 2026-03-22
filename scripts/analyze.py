#!/usr/bin/env python3
import sys
import json
import os
import tempfile
import shutil

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

CHORD_PATTERNS = {
    'maj':  [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    'min':  [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    '7':    [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    'm7':   [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    'maj7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    'dim':  [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    'aug':  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    'sus4': [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0],
}

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def make_chord_templates():
    import numpy as np
    templates = {}
    for root in range(12):
        for quality, pattern in CHORD_PATTERNS.items():
            rotated = pattern[12 - root:] + pattern[:12 - root]
            root_name = NOTE_NAMES[root]
            suffix = '' if quality == 'maj' else quality
            chord_name = f"{root_name}{suffix}"
            templates[chord_name] = np.array(rotated, dtype=float)
    return templates

def detect_chord_from_chroma(chroma_vec, templates):
    import numpy as np
    norm = np.linalg.norm(chroma_vec)
    if norm < 0.01:
        return None
    chroma_n = chroma_vec / norm
    best_chord, best_score = None, -1
    for chord_name, template in templates.items():
        t_norm = np.linalg.norm(template)
        if t_norm == 0:
            continue
        score = float(np.dot(chroma_n, template / t_norm))
        if score > best_score:
            best_score = score
            best_chord = chord_name
    return best_chord if best_score > 0.5 else None

def simplify_chord(chord):
    """Strip extensions (maj7, m7, 7, etc.) keeping only root + major/minor/dim/aug."""
    import re
    m = re.match(r'^([A-G][#b]?)(m(?!aj)|dim|aug|sus[24]?)?', chord)
    if m:
        root = m.group(1)
        quality = m.group(2) or ''
        return root + quality
    return chord

class _QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): sys.stderr.write(msg + '\n')
    def error(self, msg): sys.stderr.write(msg + '\n')

def find_cookies_file():
    """Look for cookies.txt in /app (Docker) or next to this script."""
    candidates = [
        '/app/cookies.txt',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cookies.txt'),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None

def extract_video_id(url):
    """Extract the 11-char YouTube video ID from any YouTube URL format."""
    import re
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def _http_download(url, dest_path, headers=None, timeout=180):
    """Download url to dest_path. Returns file size or raises."""
    import urllib.request
    h = {'User-Agent': 'Mozilla/5.0 (compatible; ChordLens/1.0)'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, 'wb') as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest_path)


def download_via_cobalt(video_id, tmpdir):
    """
    Download audio via Cobalt.tools — open-source media downloader that handles
    YouTube bot detection on their end. Returns (audio_path, None, None) or None.
    """
    import urllib.request
    import json as _json

    url = f'https://www.youtube.com/watch?v={video_id}'
    body = _json.dumps({'url': url, 'downloadMode': 'audio'}).encode()
    req = urllib.request.Request(
        'https://api.cobalt.tools/',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; ChordLens/1.0)',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
    except Exception as e:
        sys.stderr.write(f'[cobalt] API request failed: {e}\n')
        return None

    status = result.get('status', '')
    sys.stderr.write(f'[cobalt] status={status}\n')

    if status not in ('tunnel', 'redirect', 'stream'):
        err = result.get('error', {})
        sys.stderr.write(f'[cobalt] error detail: {err}\n')
        return None

    download_url = result.get('url')
    if not download_url:
        sys.stderr.write('[cobalt] no download URL in response\n')
        return None

    audio_path = os.path.join(tmpdir, 'audio.mp3')
    try:
        size = _http_download(download_url, audio_path)
        sys.stderr.write(f'[cobalt] downloaded {size} bytes\n')
        if size < 10000:
            sys.stderr.write('[cobalt] file too small — likely failed\n')
            return None
        return audio_path, '', ''
    except Exception as e:
        sys.stderr.write(f'[cobalt] download failed: {e}\n')
        return None


def download_via_piped(video_id, tmpdir):
    """
    Download audio via Piped API. Returns (audio_path, title, artist) or None.
    Note: some Piped instances return IP-locked googlevideo URLs; those are skipped.
    """
    import urllib.request
    import json as _json

    PIPED_INSTANCES = [
        'https://pipedapi.kavin.rocks',
        'https://pipedapi.mha.fi',
        'https://api.piped.projectsegfau.lt',
        'https://pipedapi.adminforge.de',
    ]

    data = None
    used_instance = None
    for instance in PIPED_INSTANCES:
        try:
            req = urllib.request.Request(
                f'{instance}/streams/{video_id}',
                headers={'User-Agent': 'Mozilla/5.0'},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _json.loads(resp.read())
            used_instance = instance
            sys.stderr.write(f'[piped] got metadata from {instance}\n')
            break
        except Exception as e:
            sys.stderr.write(f'[piped] {instance} failed: {e}\n')
            continue

    if not data or not used_instance:
        sys.stderr.write('[piped] all instances failed\n')
        return None

    title = data.get('title', '')
    artist = data.get('uploader', '')
    audio_streams = data.get('audioStreams', [])
    if not audio_streams:
        sys.stderr.write('[piped] no audio streams in response\n')
        return None

    audio_streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)

    for stream in audio_streams:
        stream_url = stream.get('url', '')
        if not stream_url:
            continue

        # Skip direct YouTube CDN URLs — they're IP-locked to Piped's server
        if 'googlevideo.com' in stream_url or 'youtube.com/videoplayback' in stream_url:
            sys.stderr.write(f'[piped] skipping IP-locked CDN URL\n')
            continue

        mime = stream.get('mimeType', '')
        ext = 'webm' if ('webm' in mime or 'opus' in mime) else 'm4a'
        audio_path = os.path.join(tmpdir, f'audio.{ext}')

        try:
            sys.stderr.write(f'[piped] downloading proxied stream: {stream_url[:80]}\n')
            size = _http_download(stream_url, audio_path, headers={'Referer': used_instance + '/'})
            sys.stderr.write(f'[piped] downloaded {size} bytes\n')
            if size < 10000:
                sys.stderr.write('[piped] file too small\n')
                continue
            return audio_path, title, artist
        except Exception as e:
            sys.stderr.write(f'[piped] stream download failed: {e}\n')
            continue

    sys.stderr.write('[piped] all streams were IP-locked or failed\n')
    return None

def _analyze_audio(audio_path, title='', artist=''):
    """Analyze a local audio file and return the chord timeline."""
    try:
        import numpy as np
    except ImportError:
        return {"success": False, "error": "numpy no instalado. Ejecuta: pip install numpy"}

    try:
        import librosa
    except ImportError:
        return {"success": False, "error": "librosa no instalado. Ejecuta: pip install librosa soundfile"}

    templates = make_chord_templates()

    # Use lower sample rate for speed; cap at 6 minutes to avoid timeout
    MAX_DURATION = 360
    try:
        y, sr = librosa.load(audio_path, sr=11025, mono=True, duration=MAX_DURATION)
    except Exception as e:
        return {"success": False, "error": f"Error al cargar el audio: {str(e)}"}

    # Larger hop for speed; 2-second windows
    hop_length = 1024
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    window_size = 2.0
    frames_per_window = max(1, int(window_size * sr / hop_length))
    n_frames = chroma.shape[1]

    raw = []
    frame_idx = 0
    t = 0.0
    while frame_idx < n_frames:
        end_idx = min(frame_idx + frames_per_window, n_frames)
        window_chroma = chroma[:, frame_idx:end_idx].mean(axis=1)
        chord = detect_chord_from_chroma(window_chroma, templates)
        if chord:
            chord = simplify_chord(chord)
        raw.append((t, chord))
        frame_idx += frames_per_window
        t += window_size

    # Deduplicate consecutive same chords
    final = []
    last_chord = None
    for time, chord in raw:
        if chord and chord != last_chord:
            final.append((time, chord))
            last_chord = chord

    chords_timeline = []
    for measure, (time, chord) in enumerate(final, start=1):
        chords_timeline.append({
            'time': round(time, 2),
            'time_str': format_time(time),
            'chord': chord,
            'measure': measure
        })

    return {
        "success": True,
        "notes_count": n_frames,
        "chords_timeline": chords_timeline,
        "title": title,
        "artist": artist,
    }


def analyze_file_path(path):
    """Analyze a local audio file directly (no YouTube download needed)."""
    if not os.path.isfile(path):
        return {"success": False, "error": f"Archivo no encontrado: {path}"}
    title = os.path.splitext(os.path.basename(path))[0]
    return _analyze_audio(path, title=title, artist='')


def _ytdlp_download(url, tmpdir, player_clients, cookies_file=None):
    """Attempt yt-dlp download with the given player_clients list. Returns audio_path or None."""
    try:
        import yt_dlp
    except ImportError:
        return None

    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        winget_ffmpeg = os.path.expandvars(
            r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe'
        )
        if os.path.isfile(winget_ffmpeg):
            ffmpeg_path = winget_ffmpeg
            os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')

    base_opts = {
        'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'logger': _QuietLogger(),
        'extractor_args': {'youtube': {'player_client': player_clients}},
    }
    if cookies_file:
        base_opts['cookiefile'] = cookies_file

    if ffmpeg_path:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'ffmpeg_location': os.path.dirname(ffmpeg_path),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        sys.stderr.write(f'[yt-dlp] {player_clients} failed: {e}\n')
        return None

    files = [f for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))]
    if files:
        sys.stderr.write(f'[yt-dlp] {player_clients} succeeded\n')
    return os.path.join(tmpdir, files[0]) if files else None


def analyze_url(url):
    video_id = extract_video_id(url)
    sys.stderr.write(f'[analyze_url] video_id={video_id}\n')

    with tempfile.TemporaryDirectory() as tmpdir:

        # ── Strategy 1: Cobalt.tools ────────────────────────────────────────
        if video_id:
            sys.stderr.write('[analyze_url] trying Cobalt...\n')
            cobalt_result = download_via_cobalt(video_id, tmpdir)
            if cobalt_result:
                audio_path, _, _ = cobalt_result
                # Cobalt doesn't return metadata; fetch via yt-dlp best-effort
                title, artist = _fetch_metadata(url)
                return _analyze_audio(audio_path, title=title, artist=artist)

        # ── Strategy 2: Piped API ───────────────────────────────────────────
        if video_id:
            sys.stderr.write('[analyze_url] trying Piped...\n')
            piped_result = download_via_piped(video_id, tmpdir)
            if piped_result:
                audio_path, title, artist = piped_result
                return _analyze_audio(audio_path, title=title, artist=artist)

        # ── Strategy 3: yt-dlp with multiple clients ────────────────────────
        try:
            import yt_dlp as _yt
        except ImportError:
            return {"success": False, "error": "No se pudo obtener el audio (yt-dlp no instalado, Cobalt y Piped fallaron)."}

        cookies_file = find_cookies_file()
        title, artist = _fetch_metadata(url, cookies_file)

        yt_strategies = [['android'], ['ios'], ['android_embedded'], ['tv_embedded']]
        audio_path = None
        for clients in yt_strategies:
            sys.stderr.write(f'[analyze_url] trying yt-dlp {clients}...\n')
            subdir = tempfile.mkdtemp(dir=tmpdir)
            audio_path = _ytdlp_download(url, subdir, clients, cookies_file)
            if audio_path:
                break

        if not audio_path:
            return {
                "success": False,
                "error": "No se pudo descargar el audio de YouTube. Todas las estrategias fallaron. Podés subir el MP3 manualmente con el botón 'Subir archivo'."
            }

        return _analyze_audio(audio_path, title=title, artist=artist)


def _fetch_metadata(url, cookies_file=None):
    """Try to fetch title/artist via yt-dlp without downloading. Returns (title, artist)."""
    try:
        import yt_dlp as _yt
    except ImportError:
        return '', ''
    for client in (['android'], ['ios'], ['tv_embedded']):
        try:
            opts = {
                'quiet': True, 'no_warnings': True, 'logger': _QuietLogger(),
                'extractor_args': {'youtube': {'player_client': client}},
            }
            if cookies_file:
                opts['cookiefile'] = cookies_file
            with _yt.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', '')
                artist = info.get('artist') or info.get('creator') or info.get('uploader', '')
                return title, artist
        except Exception:
            continue
    return '', ''


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Uso: analyze.py <url> | analyze.py --file <ruta>"}))
        sys.exit(1)

    if sys.argv[1] == '--file':
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "Ruta de archivo no proporcionada"}))
            sys.exit(1)
        result = analyze_file_path(sys.argv[2])
    else:
        result = analyze_url(sys.argv[1])

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode('ascii'))
    sys.stdout.buffer.write(b'\n')

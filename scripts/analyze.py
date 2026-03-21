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

def analyze_url(url):
    try:
        import yt_dlp
    except ImportError:
        return {"success": False, "error": "yt-dlp no instalado. Ejecuta: pip install yt-dlp"}

    try:
        import numpy as np
    except ImportError:
        return {"success": False, "error": "numpy no instalado. Ejecuta: pip install numpy"}

    try:
        import librosa
    except ImportError:
        return {"success": False, "error": "librosa no instalado. Ejecuta: pip install librosa soundfile"}

    # Extract metadata (title/artist) before downloading
    title = ''
    artist = ''
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'logger': _QuietLogger(), 'extractor_args': {'youtube': {'player_client': ['tv_embedded']}}}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            artist = (
                info.get('artist') or
                info.get('creator') or
                info.get('uploader', '')
            )
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        # Look for ffmpeg in PATH or common WinGet install location
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            winget_ffmpeg = os.path.expandvars(
                r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe'
            )
            if os.path.isfile(winget_ffmpeg):
                ffmpeg_path = winget_ffmpeg
                ffmpeg_dir = os.path.dirname(ffmpeg_path)
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')

        has_ffmpeg = ffmpeg_path is not None

        base_opts = {
            'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'logger': _QuietLogger(),
            'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
        }

        if has_ffmpeg:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ydl_opts = {
                **base_opts,
                'format': 'bestaudio/best',
                'ffmpeg_location': ffmpeg_dir,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
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
            return {"success": False, "error": f"Error al descargar el audio: {str(e)}"}

        files = [f for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))]
        if not files:
            return {"success": False, "error": "No se pudo obtener el audio. Instala ffmpeg para mejor compatibilidad."}

        audio_path = os.path.join(tmpdir, files[0])

        # Use lower sample rate for speed; cap at 6 minutes to avoid timeout
        MAX_DURATION = 360
        try:
            y, sr = librosa.load(audio_path, sr=11025, mono=True, duration=MAX_DURATION)
        except Exception as e:
            if not has_ffmpeg:
                return {"success": False, "error": f"No se pudo cargar el audio. Instala ffmpeg (https://ffmpeg.org) y agregalo al PATH. Detalle: {str(e)}"}
            return {"success": False, "error": f"Error al cargar el audio: {str(e)}"}

        templates = make_chord_templates()

        # Larger hop for speed; 2-second windows
        hop_length = 1024
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

        window_size = 2.0
        frames_per_window = max(1, int(window_size * sr / hop_length))
        n_frames = chroma.shape[1]

        # Step 1: detect chord per 2-second window
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

        total_duration = t

        # Deduplicate consecutive same chords — show all changes
        final = []
        last_chord = None
        for time, chord in raw:
            if chord and chord != last_chord:
                final.append((time, chord))
                last_chord = chord

        # Step 6: build final timeline
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

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "URL no proporcionada"}))
        sys.exit(1)

    url = sys.argv[1]
    result = analyze_url(url)
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode('ascii'))
    sys.stdout.buffer.write(b'\n')

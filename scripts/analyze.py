#!/usr/bin/env python3
import sys
import json
import os
import tempfile
import shutil

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Weighted templates: root > fifth > third (more musical than binary)
CHORD_INTERVALS = {
    'maj':  {0: 1.0, 4: 0.6, 7: 0.8},
    'min':  {0: 1.0, 3: 0.6, 7: 0.8},
    '7':    {0: 1.0, 4: 0.6, 7: 0.8, 10: 0.5},
    'm7':   {0: 1.0, 3: 0.6, 7: 0.8, 10: 0.5},
    'maj7': {0: 1.0, 4: 0.6, 7: 0.8, 11: 0.5},
    'dim':  {0: 1.0, 3: 0.6,  6: 0.5},
    'aug':  {0: 1.0, 4: 0.6,  8: 0.5},
    'sus4': {0: 1.0, 5: 0.7,  7: 0.8},
}

# Penalty multipliers: dim/aug penalized unless evidence is strong
# '7' raised slightly to 0.95 (was 0.92) so dominant 7ths compete better
CHORD_TYPE_PENALTY = {
    'maj': 1.0, 'min': 1.0, 'm7': 0.92, '7': 0.95,
    'maj7': 0.88, 'sus4': 0.82, 'dim': 0.65, 'aug': 0.65,
}

# Krumhansl-Schmuckler key profiles for key detection
KS_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KS_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# (root_offset, quality) pairs for diatonic chords
MAJOR_DIATONIC = [(0,'maj'),(2,'min'),(4,'min'),(5,'maj'),(7,'maj'),(9,'min'),(11,'dim')]
MINOR_DIATONIC = [(0,'min'),(2,'dim'),(3,'maj'),(5,'min'),(7,'min'),(8,'maj'),(10,'maj')]

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def make_chord_templates():
    import numpy as np
    templates = {}
    for root in range(12):
        for quality, intervals in CHORD_INTERVALS.items():
            vec = np.zeros(12)
            for interval, weight in intervals.items():
                vec[(root + interval) % 12] = weight
            root_name = NOTE_NAMES[root]
            suffix = '' if quality == 'maj' else quality
            chord_name = f"{root_name}{suffix}"
            templates[chord_name] = vec
    return templates


def _chord_quality(chord_name):
    import re
    m = re.match(r'^[A-G][#b]?(.*)$', chord_name)
    quality = m.group(1) if m else ''
    return quality if quality else 'maj'


def detect_chord_from_chroma(chroma_vec, templates, diatonic_set=None,
                             prev_chord=None, dominant_chord=None):
    """
    Score all templates and return (best_chord, best_score, second_chord).
    Applies: rarity penalty, diatonic boost, dominant boost, continuity boost.
    """
    import numpy as np
    norm = np.linalg.norm(chroma_vec)
    if norm < 0.01:
        return None, 0.0, None
    chroma_n = chroma_vec / norm
    scored = []
    for chord_name, template in templates.items():
        t_norm = np.linalg.norm(template)
        if t_norm == 0:
            continue
        score = float(np.dot(chroma_n, template / t_norm))
        # Penalize rare chord types
        score *= CHORD_TYPE_PENALTY.get(_chord_quality(chord_name), 1.0)
        # Dominant chord boost (V major) — harmonic minor raises the V to major
        if dominant_chord and chord_name == dominant_chord:
            score *= 1.35
        # Dominant 7th boost (V7) — very common in all styles
        if dominant_chord and chord_name == dominant_chord + '7':
            score *= 1.30
        # Boost diatonic chords
        if diatonic_set and chord_name in diatonic_set:
            score *= 1.15
        # Continuity: slight boost for staying on the same chord
        if prev_chord and chord_name == prev_chord:
            score *= 1.05
        scored.append((score, chord_name))

    scored.sort(reverse=True)
    best_score   = scored[0][0] if scored else 0.0
    best_chord   = scored[0][1] if best_score > 0.45 else None
    second_chord = scored[1][1] if len(scored) > 1 else None
    return best_chord, best_score, second_chord


def detect_key(global_chroma):
    """Krumhansl-Schmuckler key estimation. Returns (root: int, mode: str)."""
    import numpy as np
    best_key, best_score, best_mode = 0, -np.inf, 'major'
    for root in range(12):
        for mode, profile in [('major', KS_MAJOR), ('minor', KS_MINOR)]:
            rotated = profile[12 - root:] + profile[:12 - root]
            score = float(np.corrcoef(global_chroma, rotated)[0, 1])
            if score > best_score:
                best_score, best_key, best_mode = score, root, mode
    return best_key, best_mode


def get_diatonic_chords(key_root, key_mode):
    """Return the set of diatonic chord names for the given key."""
    pattern = MAJOR_DIATONIC if key_mode == 'major' else MINOR_DIATONIC
    diatonic = set()
    for offset, quality in pattern:
        root = (key_root + offset) % 12
        suffix = '' if quality == 'maj' else quality
        diatonic.add(f"{NOTE_NAMES[root]}{suffix}")
    return diatonic


def get_dominant_chord(key_root, key_mode):
    """
    Return the dominant (V) chord name.
    In minor keys harmonic minor raises the 7th, making V a MAJOR chord (e.g. E in Am).
    In major keys V is also major.
    """
    dominant_root = (key_root + 7) % 12
    return NOTE_NAMES[dominant_root]   # always major


def apply_harmonic_corrections(timeline, key_root, key_mode):
    """
    Post-processing pass to recover the dominant chord.

    Rules applied (minor keys only):
    1. Em detected immediately before the tonic → convert to E (V→I cadence).
    2. Em detected after a pre-dominant chord (IV, IVm, IIm) → convert to E.
    Also re-deduplicates and re-numbers measures after corrections.
    """
    if key_mode != 'minor' or not timeline:
        return timeline

    tonic     = NOTE_NAMES[key_root]
    dominant  = NOTE_NAMES[(key_root + 7) % 12]   # e.g. 'E' in Am
    dom_minor = dominant + 'm'                     # e.g. 'Em'

    pre_dominants = {
        NOTE_NAMES[(key_root + 5) % 12],        # IV  (F in Am)
        NOTE_NAMES[(key_root + 5) % 12] + 'm',  # IVm
        NOTE_NAMES[(key_root + 2) % 12] + 'm',  # IIm (Dm in Am)
        NOTE_NAMES[(key_root + 2) % 12],         # II
    }

    chords    = [e['chord'] for e in timeline]
    corrected = list(chords)

    for i, chord in enumerate(chords):
        if chord != dom_minor:
            continue
        prev_c = chords[i - 1] if i > 0 else None
        next_c = chords[i + 1] if i + 1 < len(chords) else None

        # Rule 1: Xm → tonic cadence
        if next_c == tonic:
            corrected[i] = dominant
        # Rule 2: pre-dominant → Xm
        elif prev_c in pre_dominants:
            corrected[i] = dominant

    # Rebuild, re-deduplicate, re-number
    result, last = [], None
    for entry, new_chord in zip(timeline, corrected):
        if new_chord != last:
            new_entry = dict(entry, chord=new_chord)
            result.append(new_entry)
            last = new_chord
    for i, entry in enumerate(result, start=1):
        entry['measure'] = i
    return result


def simplify_chord(chord):
    """
    Strip complex extensions but KEEP:
      - minor quality  (m)
      - dim, aug
      - sus2, sus4
      - dominant 7th  (7)  ← B7, A7, C7, E7 etc. are preserved

    Examples:
      Bm7   → Bm     (minor 7th stripped to minor)
      Cmaj7 → C      (major 7th stripped)
      B7    → B7     (dominant 7th kept)
      A7    → A7     (dominant 7th kept)
      Bdim  → Bdim   (kept)
      Csus4 → Csus4  (kept)
    """
    import re
    m = re.match(
        r'^([A-G][#b]?)'                   # root  (required)
        r'(m(?!aj)|dim|aug|sus[24]?|7)?'   # quality: m / dim / aug / sus / 7
        r'.*$',                             # discard everything else
        chord
    )
    if m:
        root    = m.group(1)
        quality = m.group(2) or ''
        return root + quality
    return chord


class _QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): sys.stderr.write(msg + '\n')
    def error(self, msg): sys.stderr.write(msg + '\n')

def find_cookies_file():
    """
    Locate a YouTube cookies file.
    Priority:
      1. YOUTUBE_COOKIES_B64 env var (base64-encoded cookies.txt content)
      2. /app/cookies.txt  (Docker volume mount)
      3. cookies.txt next to this script
    """
    import base64 as _b64

    b64 = os.environ.get('YOUTUBE_COOKIES_B64', '').strip()
    if b64:
        try:
            content = _b64.b64decode(b64).decode('utf-8')
            tmp = '/tmp/yt_cookies.txt'
            with open(tmp, 'w') as f:
                f.write(content)
            sys.stderr.write(f'[cookies] loaded from YOUTUBE_COOKIES_B64 ({len(content)} chars)\n')
            return tmp
        except Exception as e:
            sys.stderr.write(f'[cookies] YOUTUBE_COOKIES_B64 decode failed: {e}\n')

    candidates = [
        '/app/cookies.txt',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cookies.txt'),
    ]
    for path in candidates:
        if os.path.isfile(path):
            sys.stderr.write(f'[cookies] found file: {path}\n')
            return os.path.abspath(path)

    sys.stderr.write('[cookies] no cookies found — set YOUTUBE_COOKIES_B64 in Railway\n')
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


def download_via_invidious(video_id, tmpdir):
    """
    Download audio via Invidious proxy with local=true.
    Invidious fetches from YouTube CDN on THEIR server and streams to us,
    so Railway's IP is never seen by YouTube.
    """
    import urllib.request
    import json as _j

    INSTANCES = [
        'https://inv.nadeko.net',
        'https://invidious.privacyredirect.com',
        'https://yt.cdaut.de',
        'https://invidious.nerdvpn.de',
        'https://invidious.io',
        'https://vid.puffyan.us',
        'https://invidious.lunar.icu',
    ]

    for instance in INSTANCES:
        try:
            api_url = f'{instance}/api/v1/videos/{video_id}?fields=title,author,adaptiveFormats'
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _j.loads(resp.read())
        except Exception as e:
            sys.stderr.write(f'[invidious] {instance} metadata failed: {e}\n')
            continue

        title = data.get('title', '')
        artist = data.get('author', '')
        formats = data.get('adaptiveFormats', [])
        audio = [f for f in formats if f.get('type', '').startswith('audio/')]
        if not audio:
            sys.stderr.write(f'[invidious] {instance} no audio formats\n')
            continue

        audio.sort(key=lambda f: f.get('bitrate', 0), reverse=True)

        for fmt in audio[:3]:
            itag = fmt.get('itag')
            if not itag:
                continue
            mime = fmt.get('type', '')
            ext = 'webm' if ('webm' in mime or 'opus' in mime) else 'm4a'
            audio_path = os.path.join(tmpdir, f'invidious_{itag}.{ext}')
            proxy_url = f'{instance}/latest_version?id={video_id}&itag={itag}&local=true'
            sys.stderr.write(f'[invidious] {instance} itag={itag} ({ext})\n')
            try:
                size = _http_download(proxy_url, audio_path,
                                      headers={'Referer': instance + '/'},
                                      timeout=240)
                sys.stderr.write(f'[invidious] downloaded {size} bytes\n')
                if size > 50000:
                    return audio_path, title, artist
                sys.stderr.write(f'[invidious] file too small ({size}), trying next\n')
            except Exception as e:
                sys.stderr.write(f'[invidious] download error: {e}\n')
                continue

    sys.stderr.write('[invidious] all instances failed\n')
    return None


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

    MAX_DURATION = 360
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=MAX_DURATION)
    except Exception as e:
        return {"success": False, "error": f"Error al cargar el audio: {str(e)}"}

    # 1. Harmonic/percussive separation — removes drums and noise before analysis
    y_harmonic, _ = librosa.effects.hpss(y)

    # 2. Chroma CQT on harmonic component only
    hop_length = 512
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=hop_length)
    n_frames = chroma.shape[1]

    # 3. Key detection from global chroma (Krumhansl-Schmuckler)
    global_chroma = chroma.mean(axis=1)
    key_root, key_mode = detect_key(global_chroma)
    diatonic_set   = get_diatonic_chords(key_root, key_mode)
    dominant_chord = get_dominant_chord(key_root, key_mode)

    # Always allow the V (dominant major) and V7
    diatonic_set.add(dominant_chord)
    diatonic_set.add(dominant_chord + '7')

    # Add dominant-7th versions of every diatonic major chord (secondary dominants).
    # These are extremely common across blues, flamenco, pop, latin, etc.
    # e.g. in Am: A7 (I7), D7 (IV7), G7 (VII7), C7 (III7) are all normal.
    secondary_dominants = set()
    for chord_name in list(diatonic_set):
        if not any(chord_name.endswith(q) for q in ('m', 'dim', 'aug', '7')):
            secondary_dominants.add(chord_name + '7')
    diatonic_set.update(secondary_dominants)

    # Common borrowed chords in minor keys
    if key_mode == 'minor':
        subtonic_root    = (key_root + 10) % 12   # bVII (e.g. G in Am)
        subdominant_root = (key_root + 5)  % 12   # IV major (e.g. F in Am)
        diatonic_set.add(NOTE_NAMES[subtonic_root])
        diatonic_set.add(NOTE_NAMES[subtonic_root] + '7')
        diatonic_set.add(NOTE_NAMES[subdominant_root])

    sys.stderr.write(
        f'[analyze] key={NOTE_NAMES[key_root]} {key_mode}, '
        f'dominant={dominant_chord}, diatonic={sorted(diatonic_set)}\n'
    )

    # 4. Fixed-window segmentation — more reliable than onset detection for
    #    chords played on pads/synths/guitar with no sharp attack transient.
    #    50 % overlap reduces boundary artefacts.
    WINDOW_SECONDS = 0.5
    STEP_SECONDS   = 0.25

    window_frames = max(1, int(WINDOW_SECONDS * sr / hop_length))
    step_frames   = max(1, int(STEP_SECONDS   * sr / hop_length))

    # 5. Per-window chord detection
    CONFIDENCE_THRESHOLD = 0.45   # min cosine similarity to accept a chord
    DIATONIC_GATE        = 0.60   # out-of-key chords need this score
    DOMINANT7_GATE       = 0.50   # lower gate specifically for dominant-7 chords
    DEBOUNCE_COUNT       = 1      # 1 window is enough to commit to a new chord

    raw_chords: list = []
    raw_times:  list = []

    current_chord = None
    cand_chord    = None
    cand_count    = 0

    for start_f in range(0, n_frames, step_frames):
        end_f = min(start_f + window_frames, n_frames)
        t = float(start_f * hop_length / sr)

        seg_duration = (end_f - start_f) * hop_length / sr
        if seg_duration < 0.15:
            raw_chords.append(current_chord)
            raw_times.append(t)
            continue

        seg_chroma = chroma[:, start_f:end_f]
        chroma_vec = np.median(seg_chroma, axis=1)

        chord, score, second_chord = detect_chord_from_chroma(
            chroma_vec, templates, diatonic_set, current_chord, dominant_chord
        )

        if score < CONFIDENCE_THRESHOLD:
            # Low confidence: rescue with dominant or dominant-7 if runner-up
            if second_chord and (second_chord == dominant_chord or
                                 second_chord == dominant_chord + '7'):
                chord = second_chord
            else:
                chord = current_chord
        elif chord:
            chord = simplify_chord(chord)
            # Gate out-of-key chords — but use a lower gate for dominant-7 chords
            # because they are inherently chromatic (secondary dominants / blues)
            if chord not in diatonic_set:
                is_dom7 = chord.endswith('7') and not chord.endswith('maj7')
                gate = DOMINANT7_GATE if is_dom7 else DIATONIC_GATE
                if score < gate:
                    if second_chord and second_chord in diatonic_set:
                        chord = simplify_chord(second_chord)
                    else:
                        chord = current_chord

        # Debounce: commit to a new chord only after DEBOUNCE_COUNT windows
        if chord == current_chord:
            cand_chord, cand_count = None, 0
        elif chord == cand_chord:
            cand_count += 1
            if cand_count >= DEBOUNCE_COUNT:
                current_chord = chord
                cand_chord, cand_count = None, 0
        else:
            cand_chord, cand_count = chord, 1

        raw_chords.append(current_chord)
        raw_times.append(t)

    # 6. Deduplicate consecutive identical chords
    deduped = []
    last_chord = None
    for time, chord in zip(raw_times, raw_chords):
        if chord and chord != last_chord:
            deduped.append((time, chord))
            last_chord = chord

    # 7. Merge very short interruptions: X → Y(< 0.3 s) → X  →  X
    def _durations(seq):
        result = []
        for i in range(len(seq)):
            if i + 1 < len(seq):
                result.append(seq[i + 1][0] - seq[i][0])
            else:
                result.append(float('inf'))
        return result

    MERGE_THRESHOLD = 0.3   # seconds (was 0.5 — reduced to keep short real chords)
    changed = True
    while changed:
        changed = False
        durs = _durations(deduped)
        merged = []
        i = 0
        while i < len(deduped):
            t_i, c_i = deduped[i]
            if (durs[i] < MERGE_THRESHOLD
                    and merged
                    and i + 1 < len(deduped)
                    and merged[-1][1] == deduped[i + 1][1]):
                changed = True
                i += 1
                continue
            merged.append((t_i, c_i))
            i += 1
        deduped = merged

    final = deduped

    chords_timeline = [
        {
            'time': round(time, 2),
            'time_str': format_time(time),
            'chord': chord,
            'measure': measure,
        }
        for measure, (time, chord) in enumerate(final, start=1)
    ]

    # 8. Harmonic corrections: recover dominant chord (e.g. Em → E before Am)
    chords_timeline = apply_harmonic_corrections(chords_timeline, key_root, key_mode)

    return {
        "success": True,
        "notes_count": n_frames,
        "chords_timeline": chords_timeline,
        "title": title,
        "artist": artist,
        "key": f"{NOTE_NAMES[key_root]} {key_mode}",
    }


def validate_result(result, expected_str):
    """
    Compare detected chords against a known-correct progression.
    expected_str: comma-separated chord names, e.g. "Am,Dm,G,F,E7,A7"
    Prints a validation report to stderr and adds a 'validation' key to result.
    """
    if not result.get('success'):
        return result

    expected = [c.strip() for c in expected_str.split(',') if c.strip()]
    detected = [e['chord'] for e in result.get('chords_timeline', [])]
    detected_unique = []
    for c in detected:
        if not detected_unique or c != detected_unique[-1]:
            detected_unique.append(c)

    detected_set = set(detected_unique)
    found     = [c for c in expected if c in detected_set]
    missing   = [c for c in expected if c not in detected_set]
    extra     = [c for c in detected_unique if c not in set(expected)]
    precision = len(found) / len(expected) * 100 if expected else 0.0

    sep = '=' * 60
    sys.stderr.write(f'\n{sep}\n')
    sys.stderr.write('VALIDATION REPORT\n')
    sys.stderr.write(f'{sep}\n')
    sys.stderr.write(f'Expected : {" → ".join(expected)}\n')
    sys.stderr.write(f'Detected : {" → ".join(detected_unique)}\n')
    sys.stderr.write(f'Found    : {found}  ({precision:.0f}% of expected)\n')
    sys.stderr.write(f'Missing  : {missing}\n')
    sys.stderr.write(f'Extra    : {extra}\n')
    sys.stderr.write(f'{sep}\n\n')

    result['validation'] = {
        'expected': expected,
        'detected_unique': detected_unique,
        'found': found,
        'missing': missing,
        'extra': extra,
        'coverage_pct': round(precision, 1),
    }
    return result


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

        # ── Strategy 1: Invidious proxy (local=true hides Railway IP) ─────────
        if video_id:
            sys.stderr.write('[analyze_url] trying Invidious...\n')
            inv_result = download_via_invidious(video_id, tmpdir)
            if inv_result:
                audio_path, title, artist = inv_result
                return _analyze_audio(audio_path, title=title, artist=artist)

        # ── Strategy 2: Cobalt.tools ────────────────────────────────────────
        if video_id:
            sys.stderr.write('[analyze_url] trying Cobalt...\n')
            cobalt_result = download_via_cobalt(video_id, tmpdir)
            if cobalt_result:
                audio_path, _, _ = cobalt_result
                title, artist = _fetch_metadata(url)
                return _analyze_audio(audio_path, title=title, artist=artist)

        # ── Strategy 3: Piped API (proxied streams only) ────────────────────
        if video_id:
            sys.stderr.write('[analyze_url] trying Piped...\n')
            piped_result = download_via_piped(video_id, tmpdir)
            if piped_result:
                audio_path, title, artist = piped_result
                return _analyze_audio(audio_path, title=title, artist=artist)

        # ── Strategy 4: yt-dlp with multiple clients ────────────────────────
        try:
            import yt_dlp as _yt
        except ImportError:
            return {"success": False, "error": "No se pudo obtener el audio (yt-dlp no instalado, Cobalt y Piped fallaron)."}

        cookies_file = find_cookies_file()
        title, artist = _fetch_metadata(url, cookies_file)

        if cookies_file:
            yt_strategies = [['web'], ['android'], ['ios'], ['tv_embedded']]
        else:
            yt_strategies = [['android'], ['ios'], ['android_embedded'], ['tv_embedded']]

        audio_path = None
        for clients in yt_strategies:
            sys.stderr.write(f'[analyze_url] trying yt-dlp {clients}...\n')
            subdir = tempfile.mkdtemp(dir=tmpdir)
            audio_path = _ytdlp_download(url, subdir, clients, cookies_file)
            if audio_path:
                break

        if not audio_path:
            has_cookies = cookies_file is not None
            if has_cookies:
                msg = (
                    "YouTube bloqueó la descarga incluso con cookies. "
                    "Las cookies pueden haber expirado — exporta unas nuevas y actualiza YOUTUBE_COOKIES_B64 en Railway."
                )
            else:
                msg = (
                    "YouTube bloquea las descargas desde servidores (detección de bots). "
                    "Solución: exporta tus cookies de YouTube y agrega la variable YOUTUBE_COOKIES_B64 en Railway. "
                    "Instrucciones en los logs del servidor."
                )
            sys.stderr.write('[analyze_url] ALL strategies failed\n')
            sys.stderr.write('=' * 60 + '\n')
            sys.stderr.write('SOLUCIÓN: Configurar cookies de YouTube en Railway\n')
            sys.stderr.write('1. Instalar extensión: "Get cookies.txt LOCALLY" (Chrome/Firefox)\n')
            sys.stderr.write('2. Ir a youtube.com con sesión iniciada\n')
            sys.stderr.write('3. Exportar cookies.txt con la extensión\n')
            sys.stderr.write('4. Codificar en base64:\n')
            sys.stderr.write('   Linux/Mac: base64 -w 0 cookies.txt\n')
            sys.stderr.write('   Windows PowerShell: [Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))\n')
            sys.stderr.write('5. En Railway > Variables: YOUTUBE_COOKIES_B64 = <resultado del paso 4>\n')
            sys.stderr.write('=' * 60 + '\n')
            return {"success": False, "error": msg}

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
    args = sys.argv[1:]

    if not args:
        print(json.dumps({"success": False, "error": (
            "Uso: analyze.py <url> "
            "| analyze.py --file <ruta> "
            "[--validate \"Am,Dm,G,F,E7,A7\"]"
        )}))
        sys.exit(1)

    # Extract optional --validate flag
    expected_progression = None
    if '--validate' in args:
        idx = args.index('--validate')
        if idx + 1 < len(args):
            expected_progression = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            sys.stderr.write('[validate] --validate requires a chord list, e.g. "Am,Dm,G,F,E7,A7"\n')

    if args[0] == '--file':
        if len(args) < 2:
            print(json.dumps({"success": False, "error": "Ruta de archivo no proporcionada"}))
            sys.exit(1)
        result = analyze_file_path(args[1])
    else:
        result = analyze_url(args[0])

    if expected_progression:
        result = validate_result(result, expected_progression)

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode('ascii'))
    sys.stdout.buffer.write(b'\n')
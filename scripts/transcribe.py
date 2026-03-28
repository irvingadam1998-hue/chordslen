#!/usr/bin/env python3
"""
Transcribe a fragment of a YouTube video to guitar tablature.
Uses librosa pyin for pitch detection (no TensorFlow required).
Usage: python transcribe.py <url> <start_seconds> <end_seconds>
"""
import sys
import json
import os
import tempfile
import shutil
import subprocess
import math

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

GUITAR_STRINGS = [
    (1, 'e', 64),
    (2, 'B', 59),
    (3, 'G', 55),
    (4, 'D', 50),
    (5, 'A', 45),
    (6, 'E', 40),
]

def midi_to_note_name(midi: int) -> str:
    return NOTE_NAMES[midi % 12] + str(midi // 12 - 1)

def hz_to_midi(freq: float) -> int:
    return round(69 + 12 * math.log2(freq / 440.0))

def midi_to_guitar_positions(midi: int):
    positions = []
    for string_num, _, open_midi in GUITAR_STRINGS:
        fret = midi - open_midi
        if 0 <= fret <= 24:
            positions.append((string_num, fret))
    return positions

def assign_strings(notes: list) -> list:
    last_string = 3
    result = []
    for note in notes:
        positions = midi_to_guitar_positions(note['midi'])
        if not positions:
            result.append({**note, 'string': 1, 'fret': 0})
            continue
        def score(p):
            s, f = p
            return f * 0.5 + abs(s - last_string) * 0.3 + (0 if 2 <= s <= 4 else 0.2)
        best = min(positions, key=score)
        last_string = best[0]
        result.append({**note, 'string': best[0], 'fret': best[1]})
    return result

def build_tab(notes: list, duration: float) -> dict:
    strings_map = {1: 'e', 2: 'B', 3: 'G', 4: 'D', 5: 'A', 6: 'E'}
    resolution = 0.1
    cols = max(int(duration / resolution) + 4, 8)
    tab = {name: ['-'] * cols for name in strings_map.values()}
    for note in notes:
        col = int(note['time'] / resolution)
        if col >= cols:
            continue
        sname = strings_map[note['string']]
        for i, ch in enumerate(str(note['fret'])):
            if col + i < cols:
                tab[sname][col + i] = ch
    return {name: ''.join(chars) for name, chars in tab.items()}

def detect_notes_librosa(audio_path: str) -> list:
    import numpy as np
    import librosa

    y, sr = librosa.load(audio_path, sr=22050, mono=True)

    # ── Separación armónica/percusiva ────────────────────────────────────────
    # Aísla el contenido armónico (melodía) del percusivo (batería, ruido)
    # margin=8 agresivo para separar mejor la melodía del fondo
    y_harmonic = librosa.effects.harmonic(y, margin=8)

    hop_length = 512

    # ── pyin sobre la componente armónica ───────────────────────────────────
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y_harmonic,
        fmin=librosa.note_to_hz('E2'),
        fmax=librosa.note_to_hz('E6'),
        sr=sr,
        frame_length=4096,
        hop_length=hop_length,
        fill_na=None,
    )

    times = librosa.times_like(f0, sr=sr, hop_length=hop_length)

    max_conf = float(np.nanmax(voiced_probs)) if len(voiced_probs) > 0 else 0.0
    voiced_count = int(np.sum(voiced_flag))
    print(f"[pyin] frames={len(f0)}, voiced={voiced_count}, max_conf={max_conf:.3f}", file=sys.stderr)

    # Umbral adaptativo: usa el 40% de la confianza máxima encontrada
    if max_conf < 0.05:
        conf_threshold = 0.02
    elif max_conf < 0.3:
        conf_threshold = max_conf * 0.4
    else:
        conf_threshold = 0.25

    print(f"[pyin] conf_threshold={conf_threshold:.3f}", file=sys.stderr)

    notes = []
    i = 0
    while i < len(f0):
        if not voiced_flag[i] or f0[i] is None or np.isnan(f0[i]):
            i += 1
            continue
        if voiced_probs[i] < conf_threshold:
            i += 1
            continue

        start_i = i
        pitches = [float(f0[i])]
        confs = [float(voiced_probs[i])]
        i += 1

        while i < len(f0) and voiced_flag[i] and not np.isnan(f0[i]):
            if voiced_probs[i] < conf_threshold:
                break
            current_midi = hz_to_midi(float(np.mean(pitches)))
            frame_midi = hz_to_midi(float(f0[i]))
            if abs(frame_midi - current_midi) > 2:
                break
            pitches.append(float(f0[i]))
            confs.append(float(voiced_probs[i]))
            i += 1

        dur = float(times[i - 1] - times[start_i]) + (hop_length / sr)
        if dur < 0.04:
            continue

        midi = hz_to_midi(float(np.mean(pitches)))
        confidence = float(np.mean(confs))

        notes.append({
            'time': float(times[start_i]),
            'duration': float(dur),
            'midi': midi,
            'note': midi_to_note_name(midi),
            'confidence': round(confidence, 3),
        })

    return notes

def transcribe(url: str, start: float, end: float) -> dict:
    tmpdir = tempfile.mkdtemp(prefix='chordlens_transcribe_')
    try:
        # ── 1. Descargar fragmento ────────────────────────────────────────────
        out_template = os.path.join(tmpdir, 'fragment.%(ext)s')
        section = f"*{start}-{end}"

        dl = subprocess.run(
            [
                'yt-dlp',
                '--download-sections', section,
                '--force-keyframes-at-cuts',
                '-x', '--audio-format', 'wav',
                '--audio-quality', '0',
                '-o', out_template,
                '--no-playlist',
                '--quiet',
                url,
            ],
            capture_output=True, text=True, timeout=120
        )

        wav_files = [f for f in os.listdir(tmpdir) if f.endswith('.wav')]
        if not wav_files:
            err = dl.stderr[:500] if dl.stderr else 'Archivo no descargado'
            return {'success': False, 'error': f'yt-dlp falló: {err}'}

        audio_path = os.path.join(tmpdir, wav_files[0])
        fragment_duration = end - start

        print(f"[transcribe] audio={wav_files[0]}, size={os.path.getsize(audio_path)} bytes", file=sys.stderr)

        # ── 2. Detectar notas ────────────────────────────────────────────────
        notes_raw = detect_notes_librosa(audio_path)
        print(f"[transcribe] notas detectadas={len(notes_raw)}", file=sys.stderr)

        if not notes_raw:
            return {
                'success': False,
                'error': (
                    'No se detectaron notas melódicas en el fragmento. '
                    'pyin no encontró pitch claro — puede ser que la guitarra tenga mucha distorsión, '
                    'reverb, o hay mucho ruido de fondo. Intentá con una sección más limpia o de guitarra acústica.'
                )
            }

        # ── 3. Asignar cuerdas ───────────────────────────────────────────────
        notes = assign_strings(sorted(notes_raw, key=lambda n: n['time']))

        # ── 4. BPM ───────────────────────────────────────────────────────────
        bpm = None
        try:
            import librosa
            import numpy as np
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = round(float(tempo), 1)
        except Exception:
            pass

        # ── 5. Tablatura ─────────────────────────────────────────────────────
        tab = build_tab(notes, fragment_duration)

        return {
            'success': True,
            'notes': notes,
            'tab': tab,
            'duration': fragment_duration,
            'bpm': bpm,
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout al descargar el fragmento.'}
    except Exception as e:
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        return {'success': False, 'error': str(e)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(json.dumps({'success': False, 'error': 'Uso: transcribe.py <url> <start> <end>'}))
        sys.exit(1)

    url_arg = sys.argv[1]
    try:
        start_arg = float(sys.argv[2])
        end_arg   = float(sys.argv[3])
    except ValueError:
        print(json.dumps({'success': False, 'error': 'start y end deben ser números'}))
        sys.exit(1)

    print(json.dumps(transcribe(url_arg, start_arg, end_arg)))

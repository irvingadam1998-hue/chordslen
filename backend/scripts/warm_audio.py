"""Populate the image's portable Numba cache at build time, without network access."""
import json
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    from .analyze import analyze_file_path
except ImportError:
    from analyze import analyze_file_path


def main():
    # Stereo 44.1 kHz also exercises the conversion used for downloaded WAV files.
    sr = 44100
    t = np.arange(sr * 3, dtype=np.float32) / sr
    tone = sum(np.sin(2 * np.pi * frequency * t) for frequency in (261.63, 329.63, 392.0)) / 4
    with tempfile.TemporaryDirectory(prefix='chordlens_warmup_') as directory:
        path = Path(directory) / 'warmup.wav'
        sf.write(path, np.column_stack((tone, tone)), sr)
        result = analyze_file_path(str(path))
    if not result.get('success') or not result.get('chords_timeline'):
        raise RuntimeError('Audio build warmup failed')
    print(json.dumps({'audio_warmup': 'ok', 'timings': result['timings']}))


if __name__ == '__main__':
    main()

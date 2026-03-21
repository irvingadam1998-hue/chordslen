const SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const FLAT_TO_SHARP: Record<string, string> = {
  Db: 'C#', Eb: 'D#', Gb: 'F#', Ab: 'G#', Bb: 'A#',
}

export function transposeChord(chord: string, semitones: number): string {
  if (semitones === 0) return chord
  const m = chord.match(/^([A-G][#b]?)(m|dim|aug|sus[24]?)?$/)
  if (!m) return chord
  const root = FLAT_TO_SHARP[m[1]] ?? m[1]
  const quality = m[2] ?? ''
  const idx = SHARPS.indexOf(root)
  if (idx === -1) return chord
  const newIdx = ((idx + semitones) % 12 + 12) % 12
  return SHARPS[newIdx] + quality
}

export function getKeyName(semitones: number): string {
  const s = ((semitones % 12) + 12) % 12
  return SHARPS[s]
}

import guitarChords from '@tombatossals/chords-db/lib/guitar.json'

type Position = {
  frets: number[]
  fingers: number[]
  baseFret: number
  barres: number[]
  midi: number[]
}
type ChordDefinition = { suffix: string; positions: Position[] }
const keys: Record<string, string> = {
  'C#': 'Csharp',
  Db: 'Csharp',
  'D#': 'Eb',
  'F#': 'Fsharp',
  Gb: 'Fsharp',
  'G#': 'Ab',
  'A#': 'Bb',
}
const suffixes: Record<string, string> = {
  '': 'major',
  maj: 'major',
  m: 'minor',
  min: 'minor',
  min7: 'm7',
}
const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const flats: Record<string, string> = {
  Db: 'C#',
  Eb: 'D#',
  Gb: 'F#',
  Ab: 'G#',
  Bb: 'A#',
}

export function chordPosition(name: string): Position | null {
  const match = name.match(/^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$/)
  if (!match) return null
  const group = (guitarChords.chords as Record<string, ChordDefinition[]>)[
    keys[match[1]] ?? match[1]
  ]
  const chord = group?.find(
    (c) => c.suffix === (suffixes[match[2]] ?? match[2]),
  )
  if (!chord) return null
  if (match[3]) {
    const bass = notes.indexOf(flats[match[3]] ?? match[3])
    return (
      chord.positions.find((p) => Math.min(...p.midi) % 12 === bass) ?? null
    )
  }
  return chord.positions[0] ?? null
}

export default function ChordDiagram({
  chord,
  compact = false,
}: {
  chord: string
  compact?: boolean
}) {
  const position = chordPosition(chord)
  if (!position)
    return (
      <div className="flex h-full min-h-24 items-center justify-center px-3 text-center text-xs opacity-70">
        {chord === 'N' ? 'Sin acorde' : 'Sin posición disponible'}
      </div>
    )
  return (
    <svg
      viewBox="0 0 120 136"
      role="img"
      aria-label={`Posición de guitarra: ${chord}, traste ${position.baseFret}`}
      className={compact ? 'h-24 w-24' : 'h-36 w-32'}
    >
      {Array.from({ length: 5 }, (_, i) => (
        <line
          key={`f${i}`}
          x1="24"
          x2="104"
          y1={28 + i * 22}
          y2={28 + i * 22}
          stroke="currentColor"
          strokeOpacity={i === 0 && position.baseFret === 1 ? 1 : 0.25}
          strokeWidth={i === 0 && position.baseFret === 1 ? 3 : 1}
        />
      ))}
      {Array.from({ length: 6 }, (_, i) => (
        <line
          key={`s${i}`}
          x1={24 + i * 16}
          x2={24 + i * 16}
          y1="28"
          y2="116"
          stroke="currentColor"
          strokeOpacity=".3"
        />
      ))}
      {position.baseFret > 1 && (
        <text x="5" y="44" fill="currentColor" fontSize="10">
          {position.baseFret}
        </text>
      )}
      {position.barres.map((fret) => {
        const strings = position.frets
          .map((f, i) => (f === fret ? i : -1))
          .filter((i) => i >= 0)
        return strings.length > 1 ? (
          <line
            key={fret}
            x1={24 + strings[0] * 16}
            x2={24 + strings[strings.length - 1] * 16}
            y1={17 + fret * 22}
            y2={17 + fret * 22}
            stroke="currentColor"
            strokeWidth="10"
            strokeLinecap="round"
          />
        ) : null
      })}
      {position.frets.map((fret, i) => (
        <g key={i}>
          {fret > 0 ? (
            <>
              <circle
                cx={24 + i * 16}
                cy={17 + fret * 22}
                r="6"
                fill="currentColor"
              />
              {!compact && (
                <text
                  x={24 + i * 16}
                  y={20 + fret * 22}
                  textAnchor="middle"
                  fontSize="8"
                  fill="var(--diagram-finger, white)"
                >
                  {position.fingers[i] || ''}
                </text>
              )}
            </>
          ) : fret === 0 ? (
            <circle
              cx={24 + i * 16}
              cy="15"
              r="3"
              fill="none"
              stroke="currentColor"
            />
          ) : (
            <text
              x={24 + i * 16}
              y="19"
              textAnchor="middle"
              fontSize="12"
              fill="currentColor"
            >
              ×
            </text>
          )}
          <text
            x={24 + i * 16}
            y="132"
            textAnchor="middle"
            fontSize="9"
            fill="currentColor"
            opacity=".5"
          >
            {['E', 'A', 'D', 'G', 'B', 'e'][i]}
          </text>
        </g>
      ))}
    </svg>
  )
}

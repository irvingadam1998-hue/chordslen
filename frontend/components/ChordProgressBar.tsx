'use client'

import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'
// @ts-ignore
import Guitar from '@tombatossals/react-chords/lib/Chord'
import guitarChords from '@tombatossals/chords-db/lib/guitar.json'

interface ChordProgressBarProps {
  chords: ChordEvent[]
  totalDuration: number
  currentTime: number
  transposeBy: number
  onSeek?: (time: number) => void
}

const NOTE_COLORS: Record<string, string> = {
  'C': '#ef4444', 'C#': '#f97316', 'D': '#f59e0b', 'D#': '#eab308',
  'E': '#84cc16', 'F': '#22c55e', 'F#': '#10b981', 'G': '#06b6d4',
  'G#': '#3b82f6', 'A': '#6366f1', 'A#': '#a855f7', 'B': '#ec4899',
}

const instrument = {
  strings: 6,
  fretsOnChord: 4,
  name: 'Guitar',
  keys: [],
  tunings: { standard: ['E', 'A', 'D', 'G', 'B', 'E'] },
}

function noteToDbKey(note: string) {
  return note.replace('#', 'sharp').replace('b', 'flat')
}

function parseChord(chord: string) {
  const rootMatch = chord.match(/^[A-G][#b]?/)
  if (!rootMatch) return { root: chord, suffix: 'major' }
  const root = rootMatch[0]
  const suffixMap: Record<string, string> = {
    '': 'major', 'maj': 'major', 'm': 'minor', 'min': 'minor',
    '7': '7', 'm7': 'm7', 'maj7': 'maj7', 'M7': 'maj7',
    'sus2': 'sus2', 'sus4': 'sus4', 'add9': 'add9',
    'dim': 'dim', 'aug': 'aug', '6': '6', 'm6': 'm6',
    '9': '9', 'm9': 'm9', '11': '11', '13': '13', '5': '5', '7sus4': '7sus4',
  }
  const suffix = chord.slice(root.length)
  return { root, suffix: suffixMap[suffix] ?? (suffix || 'major') }
}

function getChordPosition(chordName: string) {
  const { root, suffix } = parseChord(chordName)
  const group = (guitarChords.chords as Record<string, any[]>)[noteToDbKey(root)]
  if (!group) return null
  const match = group.find((c: any) => c.suffix === suffix) ?? group[0]
  return match?.positions?.[0] ?? null
}

function getColor(chord: string): string {
  const notes = ['C#', 'D#', 'F#', 'G#', 'A#', 'C', 'D', 'E', 'F', 'G', 'A', 'B']
  for (const n of notes) if (chord.startsWith(n)) return NOTE_COLORS[n] ?? '#6b7280'
  return '#6b7280'
}

export default function ChordProgressBar({ chords, totalDuration, currentTime, transposeBy, onSeek }: ChordProgressBarProps) {
  if (!chords.length || !totalDuration) return null

  const segments = chords.map((chord, i) => {
    const start = chord.time
    const end = i + 1 < chords.length ? chords[i + 1].time : totalDuration
    const width = ((end - start) / totalDuration) * 100
    const transposed = transposeChord(chord.chord, transposeBy)
    return { start, end, width, chord: transposed, original: chord }
  })

  const progress = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0

  const activeIdx = segments.reduce((acc, seg, i) => currentTime >= seg.start ? i : acc, -1)
  const activeChord = activeIdx >= 0 ? segments[activeIdx].chord : null
  const nextChord = activeIdx >= 0 && activeIdx + 1 < segments.length ? segments[activeIdx + 1].chord : null

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-xs font-semibold tracking-widest text-white/30 uppercase">Mapa de acordes</h2>
      <div
        className="relative w-full h-10 rounded-xl overflow-hidden flex cursor-pointer"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const pct = (e.clientX - rect.left) / rect.width
          onSeek?.(pct * totalDuration)
        }}
      >
        {segments.map((seg, i) => (
          <div
            key={i}
            title={`${seg.chord} — ${seg.original.time_str}`}
            style={{ width: `${seg.width}%`, backgroundColor: getColor(seg.chord) + '55', borderRight: '1px solid rgba(0,0,0,0.3)' }}
            className="relative h-full flex items-center justify-center overflow-hidden group hover:brightness-125 transition-all"
          >
            {seg.width > 3 && (
              <span className="text-[10px] font-mono font-bold text-white/80 truncate px-1 pointer-events-none">
                {seg.chord}
              </span>
            )}
          </div>
        ))}

        {/* Playhead */}
        {currentTime >= 0 && (
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_rgba(255,255,255,0.8)] pointer-events-none z-10"
            style={{ left: `${Math.min(progress, 100)}%` }}
          />
        )}
      </div>
      {/* Diagramas acorde actual + siguiente */}
      {activeChord && (
        <div className="flex items-end gap-6 py-3 px-4 rounded-2xl bg-white/3 border border-white/8 mt-1">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">Ahora</span>
            <div className="flex flex-col items-center gap-1.5">
              <div className="rounded-xl p-2" style={{ backgroundColor: getColor(activeChord) + '15', border: `1px solid ${getColor(activeChord)}35` }}>
                {getChordPosition(activeChord) ? (
                  <div style={{ width: 80 }}>
                    <Guitar chord={getChordPosition(activeChord)} instrument={instrument} lite={false} />
                  </div>
                ) : (
                  <div className="flex items-center justify-center font-mono font-bold text-sm" style={{ width: 80, height: 100, color: getColor(activeChord) }}>
                    {activeChord}
                  </div>
                )}
              </div>
              <span className="text-sm font-bold font-mono" style={{ color: getColor(activeChord) }}>{activeChord}</span>
            </div>
          </div>

          <span className="text-white/15 text-xl mb-8 select-none">→</span>

          {nextChord ? (
            <div className="flex flex-col gap-1 opacity-45">
              <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">Siguiente</span>
              <div className="flex flex-col items-center gap-1.5">
                <div className="rounded-xl p-2" style={{ backgroundColor: getColor(nextChord) + '15', border: `1px solid ${getColor(nextChord)}35` }}>
                  {getChordPosition(nextChord) ? (
                    <div style={{ width: 80 }}>
                      <Guitar chord={getChordPosition(nextChord)} instrument={instrument} lite={false} />
                    </div>
                  ) : (
                    <div className="flex items-center justify-center font-mono font-bold text-sm" style={{ width: 80, height: 100, color: getColor(nextChord) }}>
                      {nextChord}
                    </div>
                  )}
                </div>
                <span className="text-sm font-bold font-mono" style={{ color: getColor(nextChord) }}>{nextChord}</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-1 opacity-20">
              <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">Siguiente</span>
              <div className="flex items-center justify-center font-mono text-xs text-white/20" style={{ width: 80, height: 100 }}>—</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

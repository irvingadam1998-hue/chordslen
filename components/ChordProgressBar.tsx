'use client'

import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'

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
    </div>
  )
}

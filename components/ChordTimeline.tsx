'use client'

import { useRef, useEffect } from 'react'
import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'

interface ChordTimelineProps {
  chords: ChordEvent[]
  currentTime?: number
  transposeBy?: number
  onSeek?: (time: number) => void
}

const NOTE_COLORS: Record<string, string> = {
  'C':  '#ef4444',
  'C#': '#f97316',
  'D':  '#f59e0b',
  'D#': '#eab308',
  'E':  '#84cc16',
  'F':  '#22c55e',
  'F#': '#10b981',
  'G':  '#06b6d4',
  'G#': '#3b82f6',
  'A':  '#6366f1',
  'A#': '#a855f7',
  'B':  '#ec4899',
}

function getColor(chord: string): string {
  const notes = ['C#', 'D#', 'F#', 'G#', 'A#', 'C', 'D', 'E', 'F', 'G', 'A', 'B']
  for (const note of notes) {
    if (chord.startsWith(note)) return NOTE_COLORS[note] ?? '#6b7280'
  }
  return '#6b7280'
}

export default function ChordTimeline({ chords, currentTime = -1, transposeBy = 0, onSeek }: ChordTimelineProps) {
  const activeIndex = chords.reduce((acc, chord, idx) =>
    chord.time <= currentTime ? idx : acc, -1)

  const activeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeIndex])

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase">Acordes</h2>
        <span className="text-xs text-gray-700">{chords.length} cambios</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {chords.map((chord, index) => {
          const isActive = index === activeIndex
          const color = getColor(chord.chord)
          return (
            <button
              key={index}
              ref={isActive ? activeRef : null}
              onClick={() => onSeek?.(chord.time)}
              style={isActive ? { backgroundColor: color, borderColor: color } : { borderColor: color + '40' }}
              className={`group flex flex-col items-center rounded-lg px-3 py-2 border transition-all duration-150
                ${isActive
                  ? 'text-gray-950 scale-110 shadow-lg'
                  : 'bg-transparent text-white hover:scale-105'
                }`}
            >
              <span className={`font-mono font-bold text-base leading-none ${isActive ? 'text-gray-950' : 'text-white'}`}>
                {transposeChord(chord.chord, transposeBy)}
              </span>
              <span className={`text-[10px] mt-1 leading-none ${isActive ? 'text-gray-800' : 'text-gray-600'}`}>
                {chord.time_str}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

'use client'

import { useRef, useEffect } from 'react'
import { TranscriptionResult } from '@/lib/types'

interface Props {
  data: TranscriptionResult
  currentTime: number
  rangeStart: number
}

const STRING_COLORS: Record<string, string> = {
  e: '#ef4444',
  B: '#f97316',
  G: '#eab308',
  D: '#22c55e',
  A: '#3b82f6',
  E: '#a855f7',
}

const STRINGS = ['e', 'B', 'G', 'D', 'A', 'E'] as const

export default function TabDisplay({ data, currentTime, rangeStart }: Props) {
  const activeRef = useRef<HTMLDivElement>(null)
  const relativeTime = currentTime - rangeStart

  // Encuentra la nota activa más cercana al tiempo actual
  const activeNoteIdx = data.notes.reduce((acc, n, i) => {
    if (relativeTime >= n.time && relativeTime < n.time + n.duration) return i
    return acc
  }, -1)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [activeNoteIdx])

  return (
    <div className="flex flex-col gap-4">
      {/* Tablatura ASCII */}
      <div className="overflow-x-auto rounded-xl bg-black/40 border border-white/8 p-4">
        <div className="font-mono text-xs leading-6 min-w-max">
          {STRINGS.map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span className="w-4 font-bold" style={{ color: STRING_COLORS[s] }}>{s}</span>
              <span className="text-white/30">|</span>
              <span className="text-white/70 tracking-wider">{data.tab[s]}</span>
              <span className="text-white/30">|</span>
            </div>
          ))}
        </div>
      </div>

      {/* Notas como pills por cuerda */}
      <div className="flex flex-col gap-2 overflow-x-auto">
        {STRINGS.map((s) => {
          const stringNum = STRINGS.indexOf(s) + 1
          const notesOnString = data.notes.filter(n => n.string === stringNum)
          if (notesOnString.length === 0) return null
          return (
            <div key={s} className="flex items-center gap-2">
              <span className="w-4 text-xs font-mono font-bold shrink-0" style={{ color: STRING_COLORS[s] }}>{s}</span>
              <div className="flex gap-1 flex-wrap">
                {notesOnString.map((n, i) => {
                  const isActive = relativeTime >= n.time && relativeTime < n.time + n.duration
                  return (
                    <div
                      key={i}
                      ref={isActive ? activeRef : null}
                      className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold transition-all"
                      style={{
                        backgroundColor: STRING_COLORS[s] + (isActive ? '40' : '18'),
                        border: `1px solid ${STRING_COLORS[s]}${isActive ? 'aa' : '35'}`,
                        color: STRING_COLORS[s],
                        transform: isActive ? 'scale(1.15)' : 'scale(1)',
                      }}
                    >
                      {n.note} <span className="opacity-60">/{n.fret}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

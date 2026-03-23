'use client'

import { useRef, useEffect, useMemo } from 'react'
import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'

interface Props {
  chords: ChordEvent[]
  currentTime?: number
  transposeBy?: number
  onSeek?: (time: number) => void
  totalDuration?: number
}

// Same color palette as before
const NOTE_COLORS: Record<string, string> = {
  'C':  '#ef4444', 'C#': '#f97316', 'D':  '#f59e0b', 'D#': '#eab308',
  'E':  '#84cc16', 'F':  '#22c55e', 'F#': '#10b981', 'G':  '#06b6d4',
  'G#': '#3b82f6', 'A':  '#6366f1', 'A#': '#a855f7', 'B':  '#ec4899',
}

function getColor(chord: string): string {
  const notes = ['C#', 'D#', 'F#', 'G#', 'A#', 'C', 'D', 'E', 'F', 'G', 'A', 'B']
  for (const note of notes) if (chord.startsWith(note)) return NOTE_COLORS[note] ?? '#6b7280'
  return '#6b7280'
}

function formatTime(s: number) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

// Each row = ROW_DURATION seconds of song
const ROW_DURATION = 32

interface Block {
  chord: string
  time: number           // absolute start time
  startPct: number       // % within the row (0–100)
  widthPct: number       // % width within the row (0–100)
  rowIndex: number
}

export default function ChordTimeline({ chords, currentTime = -1, transposeBy = 0, onSeek, totalDuration }: Props) {
  const activeRef = useRef<HTMLDivElement>(null)

  // Estimate total duration
  const total = totalDuration ?? (
    chords.length > 0
      ? chords[chords.length - 1].time + Math.max(
          chords.length > 1 ? chords[chords.length - 1].time - chords[chords.length - 2].time : 4,
          4
        )
      : 0
  )

  // Build chord duration list
  const durations = useMemo(() => chords.map((c, i) => {
    const next = chords[i + 1]
    return next ? next.time - c.time : Math.max(total - c.time, 2)
  }), [chords, total])

  // Split chords into row blocks (a chord spanning a row boundary gets split)
  const blocks = useMemo<Block[]>(() => {
    const result: Block[] = []
    chords.forEach((chord, i) => {
      let t = chord.time
      let rem = durations[i]
      while (rem > 0.01) {
        const rowIdx = Math.floor(t / ROW_DURATION)
        const rowStart = rowIdx * ROW_DURATION
        const rowEnd = rowStart + ROW_DURATION
        const segEnd = Math.min(t + rem, rowEnd)
        const segDur = segEnd - t
        result.push({
          chord: chord.chord,
          time: t,
          startPct: ((t - rowStart) / ROW_DURATION) * 100,
          widthPct: (segDur / ROW_DURATION) * 100,
          rowIndex: rowIdx,
        })
        rem -= segDur
        t = rowEnd
      }
    })
    return result
  }, [chords, durations])

  const numRows = Math.ceil(total / ROW_DURATION)

  // Active block index
  const activeBlockIdx = blocks.reduce((acc, b, i) => b.time <= currentTime ? i : acc, -1)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [activeBlockIdx])

  if (chords.length === 0) return null

  return (
    <div className="w-full flex flex-col gap-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold tracking-widest text-white/30 uppercase">Timeline</h2>
        <span className="text-xs text-white/20 font-mono">{chords.length} acordes · {formatTime(total)}</span>
      </div>

      {/* Rows */}
      {Array.from({ length: numRows }, (_, rowIdx) => {
        const rowBlocks = blocks.filter(b => b.rowIndex === rowIdx)
        const rowStartTime = rowIdx * ROW_DURATION
        const rowLabel = formatTime(rowStartTime)

        // Playhead within this row
        const playheadPct =
          currentTime >= rowStartTime && currentTime < rowStartTime + ROW_DURATION
            ? ((currentTime - rowStartTime) / ROW_DURATION) * 100
            : null

        return (
          <div key={rowIdx} className="flex items-stretch gap-2">
            {/* Row time label */}
            <div className="w-10 shrink-0 flex items-center justify-end">
              <span className="text-[10px] font-mono text-white/20">{rowLabel}</span>
            </div>

            {/* Chord blocks */}
            <div className="relative flex-1 h-14 rounded-lg overflow-hidden bg-white/3">
              {rowBlocks.map((b, j) => {
                const blockIdx = blocks.indexOf(b)
                const isActive = blockIdx === activeBlockIdx
                const color = getColor(b.chord)
                const label = transposeChord(b.chord, transposeBy)

                // How far through this block is the playhead?
                let progressPct = 0
                if (currentTime >= b.time) {
                  const blockDurInRow = (b.widthPct / 100) * ROW_DURATION
                  progressPct = Math.min((currentTime - b.time) / blockDurInRow, 1) * 100
                }

                return (
                  <button
                    key={j}
                    ref={isActive ? activeRef : null}
                    onClick={() => onSeek?.(b.time)}
                    title={`${label} · ${formatTime(b.time)}`}
                    style={{
                      position: 'absolute',
                      left: `${b.startPct}%`,
                      width: `${b.widthPct}%`,
                      top: 0,
                      bottom: 0,
                    }}
                    className="group flex items-center justify-center overflow-hidden transition-all duration-100 hover:z-10"
                  >
                    {/* Base fill */}
                    <div
                      className="absolute inset-0"
                      style={{ backgroundColor: color + (isActive ? '30' : '18') }}
                    />
                    {/* Progress fill (darker, shows elapsed portion) */}
                    {isActive && progressPct > 0 && (
                      <div
                        className="absolute inset-y-0 left-0 transition-all duration-100"
                        style={{ width: `${progressPct}%`, backgroundColor: color + '55' }}
                      />
                    )}
                    {/* Left border accent */}
                    <div
                      className="absolute left-0 inset-y-0 w-[2px]"
                      style={{ backgroundColor: color + (isActive ? 'ff' : '60') }}
                    />
                    {/* Chord name */}
                    <span
                      className={`relative z-10 font-mono font-bold text-sm leading-none truncate px-1.5 transition-all ${
                        isActive ? 'text-white scale-110' : 'text-white/70 group-hover:text-white'
                      }`}
                      style={isActive ? { textShadow: `0 0 12px ${color}` } : {}}
                    >
                      {label}
                    </span>
                  </button>
                )
              })}

              {/* Playhead vertical line */}
              {playheadPct !== null && (
                <div
                  className="absolute top-0 bottom-0 w-[2px] z-20 pointer-events-none"
                  style={{ left: `${playheadPct}%`, backgroundColor: '#fff', opacity: 0.6, boxShadow: '0 0 6px #fff' }}
                />
              )}
            </div>
          </div>
        )
      })}

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-4">
        {Array.from(new Set(chords.map(c => transposeChord(c.chord, transposeBy)))).map(chord => (
          <div
            key={chord}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold"
            style={{ backgroundColor: getColor(chord) + '25', border: `1px solid ${getColor(chord)}50`, color: getColor(chord) }}
          >
            {chord}
          </div>
        ))}
      </div>
    </div>
  )
}

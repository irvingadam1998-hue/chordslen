'use client'

import { useRef, useEffect, useMemo, useState } from 'react'
import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'
// @ts-ignore
import Guitar from '@tombatossals/react-chords/lib/Chord'
import guitarChords from '@tombatossals/chords-db/lib/guitar.json'

interface Props {
  chords: ChordEvent[]
  currentTime?: number
  transposeBy?: number
  onSeek?: (time: number) => void
  totalDuration?: number
}

const NOTE_COLORS: Record<string, string> = {
  'C': '#ef4444', 'C#': '#f97316', 'D': '#f59e0b', 'D#': '#eab308',
  'E': '#84cc16', 'F': '#22c55e', 'F#': '#10b981', 'G': '#06b6d4',
  'G#': '#3b82f6', 'A': '#6366f1', 'A#': '#a855f7', 'B': '#ec4899',
}

function getColor(chord: string): string {
  const notes = ['C#', 'D#', 'F#', 'G#', 'A#', 'C', 'D', 'E', 'F', 'G', 'A', 'B']
  for (const note of notes) if (chord.startsWith(note)) return NOTE_COLORS[note] ?? '#6b7280'
  return '#6b7280'
}

function formatTime(s: number) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

const rowDuration = 32

interface Block {
  chord: string
  time: number
  startPct: number
  widthPct: number
  rowIndex: number
}

// ── Helpers para buscar acordes en la DB ─────────────────────────────────────

// La DB usa claves como "C", "Csharp", "D", etc.
// y sufijos como "major", "minor", "7", "m7", etc.
function noteToDbKey(note: string): string {
  return note
    .replace('#', 'sharp')
    .replace('b', 'flat')
}

// Descompone "C#m7" → { root: "C#", suffix: "m7" }
function parseChord(chord: string): { root: string; suffix: string } {
  const rootMatch = chord.match(/^[A-G][#b]?/)
  if (!rootMatch) return { root: chord, suffix: 'major' }
  const root = rootMatch[0]
  let suffix = chord.slice(root.length)

  // Normalizar sufijos comunes al formato de la DB
  const suffixMap: Record<string, string> = {
    '': 'major',
    'maj': 'major',
    'm': 'minor',
    'min': 'minor',
    '7': '7',
    'm7': 'm7',
    'maj7': 'maj7',
    'M7': 'maj7',
    'sus2': 'sus2',
    'sus4': 'sus4',
    'add9': 'add9',
    'dim': 'dim',
    'aug': 'aug',
    '6': '6',
    'm6': 'm6',
    '9': '9',
    'm9': 'm9',
    '11': '11',
    '13': '13',
    '5': '5',
    '7sus4': '7sus4',
  }

  suffix = suffixMap[suffix] ?? (suffix || 'major')
  return { root, suffix }
}

function getChordFromDb(chordName: string) {
  const { root, suffix } = parseChord(chordName)
  const dbKey = noteToDbKey(root)

  // guitarChords.chords tiene la forma { C: [{...}], Csharp: [{...}], ... }
  const chordGroup = (guitarChords.chords as Record<string, any[]>)[dbKey]
  if (!chordGroup) return null

  // Buscar por suffix
  const match = chordGroup.find((c: any) => c.suffix === suffix)
  // Si no hay match exacto, devolver el primero (major)
  return match ?? chordGroup[0] ?? null
}

// Instrumento guitarra para la librería
const instrument = {
  strings: 6,
  fretsOnChord: 4,
  name: 'Guitar',
  keys: [],
  tunings: { standard: ['E', 'A', 'D', 'G', 'B', 'E'] },
}

// ── Componente de diagrama ────────────────────────────────────────────────────
function ChordDiagram({ chordName, color, label }: {
  chordName: string
  color: string
  label: string
}) {
  const chordData = getChordFromDb(chordName)
  const position = chordData?.positions?.[0] ?? null

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className="rounded-xl p-2 transition-all"
        style={{
          backgroundColor: color + '15',
          border: `1px solid ${color}35`,
        }}
      >
        {position ? (
          <div style={{ width: 80, filter: 'brightness(1.1)' }}>
            <Guitar chord={position} instrument={instrument} lite={false} />
          </div>
        ) : (
          <div
            className="flex items-center justify-center font-mono font-bold text-sm"
            style={{ width: 80, height: 100, color }}
          >
            {label}
          </div>
        )}
      </div>
      <span className="text-sm font-bold font-mono" style={{ color }}>
        {label}
      </span>
    </div>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function ChordTimeline({
  chords,
  currentTime = -1,
  transposeBy = 0,
  onSeek,
  totalDuration,
}: Props) {
  const activeRef = useRef<HTMLButtonElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [rowDuration, setRowDuration] = useState(32)
  const [legendLarge, setLegendLarge] = useState(false)

  const total = totalDuration ?? (
    chords.length > 0
      ? chords[chords.length - 1].time + Math.max(
        chords.length > 1
          ? chords[chords.length - 1].time - chords[chords.length - 2].time
          : 4,
        4
      )
      : 0
  )

  const durations = useMemo(() => chords.map((c, i) => {
    const next = chords[i + 1]
    return next ? next.time - c.time : Math.max(total - c.time, 2)
  }), [chords, total])

  const blocks = useMemo<Block[]>(() => {
    const result: Block[] = []
    chords.forEach((chord, i) => {
      let t = chord.time
      let rem = durations[i]
      while (rem > 0.01) {
        const rowIdx = Math.floor(t / rowDuration)
        const rowStart = rowIdx * rowDuration
        const rowEnd = rowStart + rowDuration
        const segEnd = Math.min(t + rem, rowEnd)
        const segDur = segEnd - t
        result.push({
          chord: chord.chord,
          time: t,
          startPct: ((t - rowStart) / rowDuration) * 100,
          widthPct: (segDur / rowDuration) * 100,
          rowIndex: rowIdx,
        })
        rem -= segDur
        t = rowEnd
      }
    })
    return result
  }, [chords, durations, rowDuration])

  const numRows = Math.ceil(total / rowDuration)

  const activeBlockIdx = blocks.reduce(
    (acc, b, i) => (b.time <= currentTime ? i : acc),
    -1
  )

  // Acorde activo y siguiente (para los diagramas)
  const activeBlock = activeBlockIdx >= 0 ? blocks[activeBlockIdx] : null
  const nextBlock = activeBlockIdx >= 0 ? blocks[activeBlockIdx + 1] ?? null : null

  const activeChordLabel = activeBlock
    ? transposeChord(activeBlock.chord, transposeBy)
    : null
  const nextChordLabel = nextBlock
    ? transposeChord(nextBlock.chord, transposeBy)
    : null

  useEffect(() => {
    const container = containerRef.current
    if (!container || !activeRef.current) return
    const rect = container.getBoundingClientRect()
    const inView = rect.top < window.innerHeight && rect.bottom > 0
    if (inView) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeBlockIdx])

  if (chords.length === 0) return null

  return (
    <div ref={containerRef} className="w-full flex flex-col gap-4">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-widest text-white/30 uppercase">
          Timeline
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setRowDuration(d => Math.max(8, d - 8))}
            className="w-6 h-6 flex items-center justify-center rounded-md text-white/40 hover:text-white/80 hover:bg-white/10 transition-all text-base leading-none"
            title="Zoom in"
          >+</button>
          <button
            onClick={() => setRowDuration(d => Math.min(128, d + 8))}
            className="w-6 h-6 flex items-center justify-center rounded-md text-white/40 hover:text-white/80 hover:bg-white/10 transition-all text-base leading-none"
            title="Zoom out"
          >−</button>
          <span className="text-xs text-white/20 font-mono">
            {chords.length} acordes · {formatTime(total)}
          </span>
        </div>
      </div>

      {/* ── Diagramas: acorde actual + siguiente ── */}
      {activeChordLabel && (
        <div className="flex items-end gap-6 py-3 px-4 rounded-2xl bg-white/3 border border-white/8">

          {/* Acorde actual */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">
              Ahora
            </span>
            <ChordDiagram
              chordName={activeChordLabel}
              color={getColor(activeChordLabel)}
              label={activeChordLabel}
            />
          </div>

          {/* Flecha separadora */}
          <span className="text-white/15 text-xl mb-8 select-none">→</span>

          {/* Siguiente acorde */}
          {nextChordLabel ? (
            <div className="flex flex-col gap-1 opacity-45">
              <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">
                Siguiente
              </span>
              <ChordDiagram
                chordName={nextChordLabel}
                color={getColor(nextChordLabel)}
                label={nextChordLabel}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-1 opacity-20">
              <span className="text-[10px] font-mono text-white/30 tracking-widest uppercase">
                Siguiente
              </span>
              <div className="flex items-center justify-center font-mono text-xs text-white/20" style={{ width: 80, height: 100 }}>
                —
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Filas del timeline ── */}
      {Array.from({ length: numRows }, (_, rowIdx) => {
        const rowBlocks = blocks.filter(b => b.rowIndex === rowIdx)
        const rowStartTime = rowIdx * rowDuration
        const rowLabel = formatTime(rowStartTime)

        const playheadPct =
          currentTime >= rowStartTime && currentTime < rowStartTime + rowDuration
            ? ((currentTime - rowStartTime) / rowDuration) * 100
            : null

        return (
          <div key={rowIdx} className="flex items-stretch gap-2">
            <div className="w-8 sm:w-10 shrink-0 flex items-center justify-end">
              <span className="text-[10px] font-mono text-white/20">{rowLabel}</span>
            </div>

            <div className="relative flex-1 h-10 sm:h-14 rounded-lg overflow-hidden bg-white/3">
              {rowBlocks.map((b, j) => {
                const blockIdx = blocks.indexOf(b)
                const isActive = blockIdx === activeBlockIdx
                const color = getColor(b.chord)
                const label = transposeChord(b.chord, transposeBy)

                let progressPct = 0
                if (currentTime >= b.time) {
                  const blockDurInRow = (b.widthPct / 100) * rowDuration
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
                    <div
                      className="absolute inset-0"
                      style={{ backgroundColor: color + (isActive ? '30' : '18') }}
                    />
                    {isActive && progressPct > 0 && (
                      <div
                        className="absolute inset-y-0 left-0 transition-all duration-100"
                        style={{ width: `${progressPct}%`, backgroundColor: color + '55' }}
                      />
                    )}
                    <div
                      className="absolute left-0 inset-y-0 w-[2px]"
                      style={{ backgroundColor: color + (isActive ? 'ff' : '60') }}
                    />
                    <span
                      className={`relative z-10 font-mono font-bold text-[10px] sm:text-sm leading-none truncate px-1 sm:px-1.5 transition-all ${isActive
                        ? 'text-white scale-110'
                        : 'text-white/70 group-hover:text-white'
                        }`}
                      style={isActive ? { textShadow: `0 0 12px ${color}` } : {}}
                    >
                      {label}
                    </span>
                  </button>
                )
              })}

              {playheadPct !== null && (
                <div
                  className="absolute top-0 bottom-0 w-[2px] z-20 pointer-events-none"
                  style={{
                    left: `${playheadPct}%`,
                    backgroundColor: '#fff',
                    opacity: 0.6,
                    boxShadow: '0 0 6px #fff',
                  }}
                />
              )}
            </div>
          </div>
        )
      })}

      {/* ── Leyenda de acordes únicos ── */}
      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Acordes</span>
        <button
          onClick={() => setLegendLarge(v => !v)}
          className="text-[10px] font-mono text-white/30 hover:text-white/70 transition-all px-2 py-0.5 rounded-md hover:bg-white/10"
        >
          {legendLarge ? '− Achicar' : '+ Agrandar'}
        </button>
      </div>
      <div className={`flex flex-wrap gap-2 ${legendLarge ? 'gap-3' : 'gap-2'}`}>
        {Array.from(new Set(chords.map(c => transposeChord(c.chord, transposeBy)))).map(chord => (
          <div
            key={chord}
            className={`flex items-center gap-1.5 rounded-full font-mono font-semibold transition-all ${
              legendLarge
                ? 'px-4 py-2 text-base'
                : 'px-2.5 py-1 text-xs'
            }`}
            style={{
              backgroundColor: getColor(chord) + '25',
              border: `1px solid ${getColor(chord)}50`,
              color: getColor(chord),
            }}
          >
            {chord}
          </div>
        ))}
      </div>
    </div>
  )
}
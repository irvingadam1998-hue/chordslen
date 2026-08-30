'use client'

import { useRef, useState, useCallback, useEffect } from 'react'

interface Props {
  totalDuration: number
  currentTime: number
  onConfirm: (start: number, end: number) => void
}

const MAX_RANGE = 60

function fmt(s: number) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

export default function RangeSelector({ totalDuration, currentTime, onConfirm }: Props) {
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(Math.min(30, totalDuration))
  const barRef = useRef<HTMLDivElement>(null)
  const dragging = useRef<'start' | 'end' | 'region' | null>(null)
  const dragStartX = useRef(0)
  const dragStartVal = useRef({ start: 0, end: 0 })

  const pct = (t: number) => (t / totalDuration) * 100

  const timeFromX = useCallback((clientX: number) => {
    const bar = barRef.current
    if (!bar) return 0
    const rect = bar.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    return ratio * totalDuration
  }, [totalDuration])

  const onMouseDown = (e: React.MouseEvent, handle: 'start' | 'end' | 'region') => {
    e.preventDefault()
    dragging.current = handle
    dragStartX.current = e.clientX
    dragStartVal.current = { start, end }
  }

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const t = timeFromX(e.clientX)
      const delta = (e.clientX - dragStartX.current) / (barRef.current?.getBoundingClientRect().width ?? 1) * totalDuration

      if (dragging.current === 'start') {
        const newStart = Math.max(0, Math.min(t, end - 1))
        // enforce max range from end side
        setStart(Math.max(end - MAX_RANGE, newStart))
      } else if (dragging.current === 'end') {
        const newEnd = Math.max(start + 1, Math.min(t, totalDuration))
        setEnd(Math.min(start + MAX_RANGE, newEnd))
      } else if (dragging.current === 'region') {
        const dur = dragStartVal.current.end - dragStartVal.current.start
        let newStart = dragStartVal.current.start + delta
        newStart = Math.max(0, Math.min(totalDuration - dur, newStart))
        setStart(newStart)
        setEnd(newStart + dur)
      }
    }
    const onUp = () => { dragging.current = null }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [timeFromX, totalDuration, start, end])

  const duration = end - start
  const playheadPct = currentTime >= 0 ? pct(currentTime) : null

  return (
    <div className="flex flex-col gap-3">
      {/* Barra */}
      <div ref={barRef} className="relative w-full h-10 rounded-xl bg-white/5 border border-white/10 select-none cursor-crosshair">

        {/* Región seleccionada */}
        <div
          className="absolute top-0 bottom-0 bg-yellow-400/20 border-x border-yellow-400/50 cursor-grab active:cursor-grabbing"
          style={{ left: `${pct(start)}%`, width: `${pct(duration)}%` }}
          onMouseDown={(e) => onMouseDown(e, 'region')}
        />

        {/* Handle inicio */}
        <div
          className="absolute top-0 bottom-0 w-3 -ml-1.5 flex items-center justify-center cursor-ew-resize z-10 group"
          style={{ left: `${pct(start)}%` }}
          onMouseDown={(e) => onMouseDown(e, 'start')}
        >
          <div className="w-1 h-6 rounded-full bg-yellow-400 group-hover:h-8 transition-all" />
        </div>

        {/* Handle fin */}
        <div
          className="absolute top-0 bottom-0 w-3 -ml-1.5 flex items-center justify-center cursor-ew-resize z-10 group"
          style={{ left: `${pct(end)}%` }}
          onMouseDown={(e) => onMouseDown(e, 'end')}
        >
          <div className="w-1 h-6 rounded-full bg-yellow-400 group-hover:h-8 transition-all" />
        </div>

        {/* Label duración centrado en región */}
        {duration > 2 && (
          <div
            className="absolute top-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center"
            style={{ left: `${pct(start)}%`, width: `${pct(duration)}%` }}
          >
            <span className="text-[10px] font-mono text-yellow-400/80 bg-black/40 px-1.5 rounded">
              {Math.round(duration)}s
            </span>
          </div>
        )}

        {/* Playhead */}
        {playheadPct !== null && (
          <div
            className="absolute top-0 bottom-0 w-px bg-white/40 pointer-events-none z-20"
            style={{ left: `${playheadPct}%` }}
          />
        )}
      </div>

      {/* Info + botón */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs font-mono text-white/40">
          <span>Inicio: <span className="text-yellow-400/80">{fmt(start)}</span></span>
          <span>Fin: <span className="text-yellow-400/80">{fmt(end)}</span></span>
          <span>Duración: <span className={duration > MAX_RANGE ? 'text-red-400' : 'text-yellow-400/80'}>{Math.round(duration)}s</span></span>
        </div>
        <button
          onClick={() => onConfirm(start, end)}
          disabled={duration > MAX_RANGE || duration < 1}
          className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-yellow-400 text-gray-950 hover:bg-yellow-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          Transcribir fragmento →
        </button>
      </div>

      {duration > MAX_RANGE && (
        <p className="text-xs text-red-400/80">Máximo 60 segundos por transcripción.</p>
      )}
    </div>
  )
}

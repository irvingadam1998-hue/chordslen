'use client'
import { useState } from 'react'
import { ArrowRight, Scissors } from 'lucide-react'
type Props = {
  totalDuration: number
  currentTime: number
  onConfirm: (start: number, end: number) => void
}
const formatTime = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
export default function RangeSelector({
  totalDuration,
  currentTime,
  onConfirm,
}: Props) {
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(Math.min(30, totalDuration))
  const duration = end - start
  return (
    <section className="panel p-5">
      <h3 className="mb-5 flex items-center gap-2 text-sm font-bold">
        <Scissors size={17} /> Selecciona un fragmento
      </h3>
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="flex flex-col gap-3 text-xs">
          <span className="flex justify-between">
            Inicio <output className="font-mono">{formatTime(start)}</output>
          </span>
          <input
            aria-label="Inicio del fragmento"
            type="range"
            min={0}
            max={Math.max(0, end - 1)}
            step={0.1}
            value={start}
            onChange={(e) =>
              setStart(Math.max(end - 60, Number(e.target.value)))
            }
          />
        </label>
        <label className="flex flex-col gap-3 text-xs">
          <span className="flex justify-between">
            Final <output className="font-mono">{formatTime(end)}</output>
          </span>
          <input
            aria-label="Final del fragmento"
            type="range"
            min={Math.min(start + 1, totalDuration)}
            max={Math.min(start + 60, totalDuration)}
            step={0.1}
            value={end}
            onChange={(e) => setEnd(Number(e.target.value))}
          />
        </label>
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <button
          className="text-xs font-semibold underline"
          disabled={currentTime < 0 || currentTime >= totalDuration - 1}
          onClick={() => {
            setStart(currentTime)
            setEnd(Math.min(currentTime + 30, totalDuration))
          }}
        >
          Empezar desde aquí
        </button>
        <button
          className="btn-primary !text-xs"
          disabled={duration < 1 || duration > 60 || end > totalDuration}
          onClick={() => onConfirm(start, end)}
        >
          Transcribir {duration.toFixed(1)} s <ArrowRight size={15} />
        </button>
      </div>
      <p className="muted mt-4 text-[11px]">Hasta 60 segundos por fragmento.</p>
    </section>
  )
}

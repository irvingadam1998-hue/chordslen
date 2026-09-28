'use client'
import { Minus, Plus, RotateCcw, SlidersHorizontal } from 'lucide-react'
export default function TransposePanel({
  capo,
  shift,
  onCapoChange,
  onShiftChange,
}: {
  capo: number
  shift: number
  onCapoChange: (v: number) => void
  onShiftChange: (v: number) => void
}) {
  return (
    <section className="panel p-5">
      <h2 className="mb-5 flex items-center gap-2 text-sm font-extrabold">
        <SlidersHorizontal size={17} /> A tu manera
      </h2>
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="capo" className="text-sm">
          Capo
        </label>
        <select
          id="capo"
          value={capo}
          onChange={(e) => onCapoChange(Number(e.target.value))}
          className="field max-w-36"
        >
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i} value={i}>
              {i ? `Traste ${i}` : 'Sin capo'}
            </option>
          ))}
        </select>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm">Transportar</span>
        <div className="flex items-center gap-1">
          <button
            className="icon-btn"
            aria-label="Bajar un semitono"
            disabled={shift <= -12}
            onClick={() => onShiftChange(shift - 1)}
          >
            <Minus size={16} />
          </button>
          <output
            className="w-10 text-center font-mono text-sm"
            aria-live="polite"
          >
            {shift > 0 ? '+' : ''}
            {shift}
          </output>
          <button
            className="icon-btn"
            aria-label="Subir un semitono"
            disabled={shift >= 12}
            onClick={() => onShiftChange(shift + 1)}
          >
            <Plus size={16} />
          </button>
        </div>
      </div>
      <p className="muted mt-4 text-[11px] leading-relaxed">
        Cambia las posiciones mostradas. El tono de la grabación se mantiene.
      </p>
      {(capo !== 0 || shift !== 0) && (
        <button
          className="mt-3 flex items-center gap-2 text-xs font-bold"
          onClick={() => {
            onCapoChange(0)
            onShiftChange(0)
          }}
        >
          <RotateCcw size={13} /> Restaurar original
        </button>
      )}
    </section>
  )
}

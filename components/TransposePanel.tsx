'use client'

interface TransposePanelProps {
  capo: number
  shift: number
  onCapoChange: (v: number) => void
  onShiftChange: (v: number) => void
}

export default function TransposePanel({ capo, shift, onCapoChange, onShiftChange }: TransposePanelProps) {
  const totalShift = ((shift - capo) % 12 + 12) % 12
  const shiftLabel = shift > 0 ? `+${shift}` : shift < 0 ? `${shift}` : '0'

  return (
    <div className="bg-white/3 border border-white/8 rounded-2xl p-5 flex flex-col gap-5">
      <h3 className="text-xs font-semibold tracking-widest text-white/30 uppercase">Transposición</h3>

      {/* Capo */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/60">Capo</span>
          <span className="text-xs text-white/30">
            {capo === 0 ? 'sin capo' : `traste ${capo}`}
          </span>
        </div>
        <div className="flex gap-1 flex-wrap">
          {Array.from({ length: 12 }, (_, i) => (
            <button
              key={i}
              onClick={() => onCapoChange(i)}
              className={`w-8 h-8 rounded-lg text-xs font-mono font-bold transition-all ${
                capo === i
                  ? 'bg-yellow-400 text-gray-950'
                  : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white/70'
              }`}
            >
              {i}
            </button>
          ))}
        </div>
      </div>

      {/* Semitone shift */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/60">Transportar</span>
          <span className="text-xs text-white/30">{shiftLabel} semitonos</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onShiftChange(shift - 1)}
            className="w-8 h-8 rounded-lg bg-white/5 text-white/60 hover:bg-white/10 hover:text-white text-lg font-bold transition-all"
          >−</button>
          <div className="flex-1 bg-white/5 rounded-lg h-8 flex items-center justify-center">
            <span className="text-sm font-mono text-yellow-400 font-bold">{shiftLabel}</span>
          </div>
          <button
            onClick={() => onShiftChange(shift + 1)}
            className="w-8 h-8 rounded-lg bg-white/5 text-white/60 hover:bg-white/10 hover:text-white text-lg font-bold transition-all"
          >+</button>
          {(capo !== 0 || shift !== 0) && (
            <button
              onClick={() => { onCapoChange(0); onShiftChange(0) }}
              className="px-3 h-8 rounded-lg bg-white/5 text-white/30 hover:text-white/60 text-xs transition-all"
            >
              reset
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      {(capo !== 0 || shift !== 0) && (
        <div className="text-xs text-white/20 bg-white/3 rounded-lg px-3 py-2">
          Transposición neta: <span className="text-yellow-400 font-mono font-bold">
            {totalShift === 0 ? '0' : totalShift > 6 ? `−${12 - totalShift}` : `+${totalShift}`} semitonos
          </span>
        </div>
      )}
    </div>
  )
}

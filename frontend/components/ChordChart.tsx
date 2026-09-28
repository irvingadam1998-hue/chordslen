'use client'
import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'
export default function ChordChart({
  chords,
  transposeBy = 0,
  totalDuration = 0,
}: {
  chords: ChordEvent[]
  transposeBy?: number
  totalDuration?: number
}) {
  const weights: Record<string, number> = {}
  chords.forEach((c, i) => {
    if (c.chord === 'N') return
    const name = transposeChord(c.chord, transposeBy)
    weights[name] =
      (weights[name] ?? 0) +
      (totalDuration > 0
        ? Math.max(0, (chords[i + 1]?.time ?? totalDuration) - c.time)
        : 1)
  })
  const entries = Object.entries(weights).sort((a, b) => b[1] - a[1])
  const sum = entries.reduce((s, [, n]) => s + n, 0)
  return (
    <section className="panel p-5">
      <h2 className="mb-1 text-sm font-extrabold">Vocabulario de la canción</h2>
      <p className="muted mb-5 text-xs">
        {totalDuration > 0
          ? 'Tiempo relativo entre los acordes detectados'
          : 'Frecuencia de aparición'}
      </p>
      <div className="flex max-h-72 flex-col gap-4 overflow-y-auto">
        {entries.map(([name, value]) => (
          <div key={name} className="flex items-center gap-3">
            <span className="w-16 shrink-0 truncate font-mono text-sm font-medium">
              {name}
            </span>
            <div className="h-1.5 flex-1 rounded-full bg-[#edf0e7]">
              <div
                className="h-full rounded-full bg-[#91ab78]"
                style={{ width: `${sum ? (value / sum) * 100 : 0}%` }}
              />
            </div>
            <span className="muted w-9 text-right font-mono text-[10px]">
              {sum ? Math.round((value / sum) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

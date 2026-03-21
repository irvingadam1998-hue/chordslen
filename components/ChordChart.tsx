'use client'

import { useEffect, useRef } from 'react'
import { ChordEvent } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'

interface ChordChartProps {
  chords: ChordEvent[]
  transposeBy?: number
}

const CHART_COLORS = [
  '#f59e0b', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6',
  '#f97316', '#06b6d4', '#ec4899', '#84cc16', '#6366f1',
  '#14b8a6', '#f43f5e',
]

export default function ChordChart({ chords, transposeBy = 0 }: ChordChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const counts: Record<string, number> = {}
    for (const chord of chords) {
      const name = transposeChord(chord.chord, transposeBy)
      counts[name] = (counts[name] || 0) + 1
    }

    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
    if (entries.length === 0) return

    const dpr = window.devicePixelRatio || 1
    const displayWidth = canvas.offsetWidth
    const displayHeight = 280
    canvas.width = displayWidth * dpr
    canvas.height = displayHeight * dpr
    canvas.style.height = `${displayHeight}px`
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, displayWidth, displayHeight)

    const padding = { top: 20, right: 20, bottom: 60, left: 40 }
    const chartWidth = displayWidth - padding.left - padding.right
    const chartHeight = displayHeight - padding.top - padding.bottom

    const maxCount = Math.max(...entries.map(([, c]) => c))
    const barWidth = Math.min(60, chartWidth / entries.length - 8)
    const barSpacing = chartWidth / entries.length

    ctx.strokeStyle = '#374151'
    ctx.lineWidth = 1
    const gridLines = 4
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (chartHeight / gridLines) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartWidth, y)
      ctx.stroke()

      const value = Math.round(maxCount - (maxCount / gridLines) * i)
      ctx.fillStyle = '#6b7280'
      ctx.font = '11px monospace'
      ctx.textAlign = 'right'
      ctx.fillText(String(value), padding.left - 6, y + 4)
    }

    entries.forEach(([chord, count], index) => {
      const x = padding.left + barSpacing * index + barSpacing / 2 - barWidth / 2
      const barHeight = (count / maxCount) * chartHeight
      const y = padding.top + chartHeight - barHeight
      const color = CHART_COLORS[index % CHART_COLORS.length]

      ctx.fillStyle = color + '33'
      ctx.fillRect(x, padding.top, barWidth, chartHeight)

      ctx.fillStyle = color
      ctx.beginPath()
      ctx.roundRect(x, y, barWidth, barHeight, [4, 4, 0, 0])
      ctx.fill()

      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 13px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(chord, x + barWidth / 2, padding.top + chartHeight + 20)

      ctx.fillStyle = '#9ca3af'
      ctx.font = '11px monospace'
      ctx.fillText(String(count), x + barWidth / 2, padding.top + chartHeight + 38)
    })
  }, [chords])

  return (
    <div className="w-full">
      <h2 className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">Distribución</h2>
      <div className="bg-gray-900/50 border border-gray-800/60 rounded-2xl p-4">
        <canvas ref={canvasRef} className="w-full" style={{ height: '280px' }} />
      </div>
    </div>
  )
}

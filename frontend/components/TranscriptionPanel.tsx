'use client'

import { useState } from 'react'
import { TranscriptionResult } from '@/lib/types'
import TabDisplay from './TabDisplay'

interface Props {
  data: TranscriptionResult | null
  loading: boolean
  currentTime: number
  rangeStart: number
}

const STRINGS = ['e', 'B', 'G', 'D', 'A', 'E'] as const

const STRING_COLORS: Record<string, string> = {
  e: '#ef4444',
  B: '#f97316',
  G: '#eab308',
  D: '#22c55e',
  A: '#3b82f6',
  E: '#a855f7',
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-2 animate-pulse">
      <div className="rounded-xl bg-[#f5f7ef] border border-[#dce2d8] p-4">
        <div className="font-mono text-xs leading-6 flex flex-col gap-1">
          {STRINGS.map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span
                className="w-4 font-bold"
                style={{ color: STRING_COLORS[s] }}
              >
                {s}
              </span>
              <span className="text-[#899582]">|</span>
              <div className="h-3 rounded bg-[#dce4d4] flex-1" />
              <span className="text-[#899582]">|</span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-xs text-[#66756c] text-center animate-pulse">
        Transcribiendo el fragmento…
      </p>
    </div>
  )
}

export default function TranscriptionPanel({
  data,
  loading,
  currentTime,
  rangeStart,
}: Props) {
  const [copied, setCopied] = useState(false)

  if (loading) return <Skeleton />
  if (!data) return null

  const tabText = STRINGS.map((s) => `${s}|${data.tab[s]}|`).join('\n')

  const handleCopy = () => {
    navigator.clipboard.writeText(tabText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Meta */}
      <div className="flex items-center gap-4 text-xs font-mono text-[#66756c]">
        <span>{data.notes.length} notas detectadas</span>
        <span>·</span>
        <span>{data.duration.toFixed(1)}s</span>
        {data.bpm && (
          <>
            <span>·</span>
            <span>{Math.round(data.bpm)} BPM</span>
          </>
        )}
        <button
          onClick={handleCopy}
          className="ml-auto px-3 py-1 rounded-lg border border-[#dce2d8] hover:border-[#95ab89] hover:text-[#213e35] transition-all"
        >
          {copied ? '✓ Copiado' : 'Copiar tablatura'}
        </button>
      </div>

      <TabDisplay
        data={data}
        currentTime={currentTime}
        rangeStart={rangeStart}
      />
    </div>
  )
}

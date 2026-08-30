'use client'

import { useEffect, useState } from 'react'

interface LyricsDisplayProps {
  artist: string
  title: string
}

export default function LyricsDisplay({ artist, title }: LyricsDisplayProps) {
  const [lyrics, setLyrics] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(false)
    setLyrics(null)

    fetch('/api/lyrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist, title }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.lyrics) {
          setLyrics(data.lyrics)
        } else {
          setError(true)
        }
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [artist, title])

  return (
    <div className="flex flex-col gap-3 h-full">
      <h2 className="text-xs font-semibold tracking-widest text-white/30 uppercase">Letra</h2>
      <div className="flex-1 bg-white/3 border border-white/8 rounded-2xl px-5 py-4 overflow-y-auto" style={{ maxHeight: '400px' }}>
        {loading && (
          <p className="text-white/20 text-sm animate-pulse">Buscando letra...</p>
        )}
        {error && !loading && (
          <p className="text-white/20 text-sm italic">
            Letra no encontrada para este video.
          </p>
        )}
        {lyrics && (
          <pre className="text-white/50 text-sm leading-7 whitespace-pre-wrap font-sans hover:text-white/70 transition-colors">
            {lyrics.trim()}
          </pre>
        )}
      </div>
    </div>
  )
}

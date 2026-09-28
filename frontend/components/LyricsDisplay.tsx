'use client'
import { useEffect, useState } from 'react'
import { LoaderCircle } from 'lucide-react'
export default function LyricsDisplay({
  artist,
  title,
}: {
  artist: string
  title: string
}) {
  const [lyrics, setLyrics] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/lyrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist, title }),
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then((data) => {
        if (!controller.signal.aborted) setLyrics(data.lyrics || null)
      })
      .catch(() => {})
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [artist, title])
  return (
    <div className="muted max-h-96 overflow-y-auto text-sm leading-7">
      {loading ? (
        <p role="status" className="flex items-center gap-2 text-xs">
          <LoaderCircle size={15} className="animate-spin" /> Buscando letra
        </p>
      ) : lyrics ? (
        <p className="whitespace-pre-wrap">{lyrics.trim()}</p>
      ) : (
        <p className="text-xs">No se encontró una letra para esta canción.</p>
      )}
    </div>
  )
}

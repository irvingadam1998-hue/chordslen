'use client'
import { useEffect, useRef, useState } from 'react'
import { FileAudio, Pause, Play, RotateCcw, RotateCw } from 'lucide-react'
type Props = {
  file: File
  onTimeUpdate: (time: number) => void
  onDuration?: (time: number) => void
  seekRef: React.MutableRefObject<((time: number) => void) | null>
}
const timeLabel = (t: number) =>
  `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`
export default function AudioPlayer({
  file,
  onTimeUpdate,
  onDuration,
  seekRef,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState('')
  useEffect(() => {
    const url = URL.createObjectURL(file)
    const audio = audioRef.current
    if (audio) {
      audio.src = url
      audio.load()
    }
    seekRef.current = (next) => {
      if (audio) {
        audio.currentTime = Math.max(0, Math.min(next, audio.duration || next))
        setTime(audio.currentTime)
        onTimeUpdate(audio.currentTime)
      }
    }
    return () => {
      audio?.pause()
      URL.revokeObjectURL(url)
      seekRef.current = null
    }
  }, [file, seekRef, onTimeUpdate])
  async function toggle() {
    const audio = audioRef.current
    if (!audio) return
    try {
      if (audio.paused) await audio.play()
      else audio.pause()
    } catch {
      setError('El navegador no pudo reproducir este formato de audio.')
    }
  }
  return (
    <div className="px-5 pb-5">
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() =>
          setError('No se pudo reproducir este archivo. Prueba MP3 o WAV.')
        }
        onTimeUpdate={() => {
          const t = audioRef.current?.currentTime || 0
          setTime(t)
          onTimeUpdate(t)
        }}
        onLoadedMetadata={() => {
          const d = audioRef.current?.duration || 0
          if (Number.isFinite(d)) {
            setDuration(d)
            onDuration?.(d)
          }
        }}
      />
      <div className="mb-5 flex items-center gap-2 rounded-lg bg-[#eff2e9] p-3">
        <FileAudio size={17} />
        <p className="truncate text-xs font-semibold">{file.name}</p>
      </div>
      <input
        aria-label="Posición de reproducción"
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={time}
        onChange={(e) => seekRef.current?.(Number(e.target.value))}
        className="w-full"
      />
      <div className="muted mt-1 flex justify-between font-mono text-[10px]">
        <span>{timeLabel(time)}</span>
        <span>{timeLabel(duration)}</span>
      </div>
      <div className="mt-4 flex items-center justify-center gap-4">
        <button
          className="icon-btn"
          aria-label="Retroceder 10 segundos"
          onClick={() => seekRef.current?.(Math.max(0, time - 10))}
        >
          <RotateCcw size={17} />
        </button>
        <button
          className="flex h-12 w-12 items-center justify-center rounded-full bg-[#284e3e] text-white"
          aria-label={playing ? 'Pausar' : 'Reproducir'}
          onClick={toggle}
        >
          {playing ? <Pause size={20} /> : <Play size={20} />}
        </button>
        <button
          className="icon-btn"
          aria-label="Avanzar 10 segundos"
          onClick={() => seekRef.current?.(Math.min(duration, time + 10))}
        >
          <RotateCw size={17} />
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-3 text-xs text-[#8b442d]">
          {error}
        </p>
      )}
    </div>
  )
}

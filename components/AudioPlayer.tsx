'use client'

import { useEffect, useRef, useState } from 'react'

interface AudioPlayerProps {
  file: File
  onTimeUpdate: (time: number) => void
  seekRef: React.MutableRefObject<((time: number) => void) | null>
}

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export default function AudioPlayer({ file, onTimeUpdate, seekRef }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const srcRef = useRef<string | null>(null)

  useEffect(() => {
    const url = URL.createObjectURL(file)
    srcRef.current = url
    const audio = audioRef.current
    if (audio) {
      audio.src = url
      audio.load()
    }
    seekRef.current = (time: number) => {
      if (audio) {
        audio.currentTime = time
        setCurrentTime(time)
      }
    }
    return () => {
      URL.revokeObjectURL(url)
      seekRef.current = null
    }
  }, [file])

  const handleTimeUpdate = () => {
    const audio = audioRef.current
    if (!audio) return
    setCurrentTime(audio.currentTime)
    onTimeUpdate(audio.currentTime)
  }

  const handleLoadedMetadata = () => {
    if (audioRef.current) setDuration(audioRef.current.duration)
  }

  const togglePlay = () => {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) { audio.play(); setPlaying(true) }
    else { audio.pause(); setPlaying(false) }
  }

  const handleSeekBar = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = Number(e.target.value)
    if (audioRef.current) audioRef.current.currentTime = time
    setCurrentTime(time)
    onTimeUpdate(time)
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="w-full rounded-xl bg-white/3 border border-white/8 p-6 flex flex-col gap-5">
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setPlaying(false)}
      />

      {/* File name */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-white truncate">{file.name}</p>
          <p className="text-xs text-white/30">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
        </div>
      </div>

      {/* Seek bar */}
      <div className="flex flex-col gap-2">
        <div className="relative h-1.5 rounded-full bg-white/10 cursor-pointer">
          <div
            className="absolute left-0 top-0 h-full rounded-full bg-yellow-400 transition-none"
            style={{ width: `${progress}%` }}
          />
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={currentTime}
            onChange={handleSeekBar}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>
        <div className="flex justify-between text-[10px] text-white/30 font-mono">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        {/* Rewind 10s */}
        <button
          onClick={() => seekRef.current?.(Math.max(0, currentTime - 10))}
          className="text-white/40 hover:text-white transition-colors"
          title="−10s"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M11.99 5V1l-5 5 5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6h-2c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
            <text x="7" y="16" fontSize="6" fill="currentColor">10</text>
          </svg>
        </button>

        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          className="w-12 h-12 rounded-full bg-yellow-400 text-gray-950 flex items-center justify-center hover:bg-yellow-300 active:scale-95 transition-all"
        >
          {playing ? (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
            </svg>
          ) : (
            <svg className="w-5 h-5 translate-x-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Forward 10s */}
        <button
          onClick={() => seekRef.current?.(Math.min(duration, currentTime + 10))}
          className="text-white/40 hover:text-white transition-colors"
          title="+10s"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12.01 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/>
            <text x="7" y="16" fontSize="6" fill="currentColor">10</text>
          </svg>
        </button>
      </div>
    </div>
  )
}

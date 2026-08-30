'use client'

import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    YT: {
      Player: new (el: HTMLElement, opts: object) => YTPlayer
      PlayerState: { PLAYING: number }
    }
    onYouTubeIframeAPIReady: () => void
  }
}

interface YTPlayer {
  getCurrentTime: () => number
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  destroy: () => void
}

interface YoutubePlayerProps {
  videoId: string
  onTimeUpdate: (time: number) => void
  seekRef: React.MutableRefObject<((time: number) => void) | null>
}

export default function YoutubePlayer({ videoId, onTimeUpdate, seekRef }: YoutubePlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<YTPlayer | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let destroyed = false

    const initPlayer = () => {
      if (destroyed || !containerRef.current) return
      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        playerVars: { autoplay: 0, modestbranding: 1, rel: 0 },
        events: {
          onReady: () => {
            seekRef.current = (time: number) => {
              playerRef.current?.seekTo(time, true)
            }
            intervalRef.current = setInterval(() => {
              if (playerRef.current?.getCurrentTime) {
                onTimeUpdate(playerRef.current.getCurrentTime())
              }
            }, 300)
          },
        },
      })
    }

    if (window.YT?.Player) {
      initPlayer()
    } else {
      window.onYouTubeIframeAPIReady = initPlayer
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const script = document.createElement('script')
        script.src = 'https://www.youtube.com/iframe_api'
        document.head.appendChild(script)
      }
    }

    return () => {
      destroyed = true
      if (intervalRef.current) clearInterval(intervalRef.current)
      playerRef.current?.destroy()
      seekRef.current = null
    }
  }, [videoId])

  return (
    <div className="w-full rounded-xl overflow-hidden bg-gray-900 border border-gray-800" style={{ aspectRatio: '16/9' }}>
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Check, Mic, MicOff } from 'lucide-react'

// ── Autocorrelation pitch detection ──────────────────────────────────────────
function autoCorrelate(buf: Float32Array, sampleRate: number): number {
  const SIZE = buf.length

  // RMS check — too quiet = no signal
  let rms = 0
  for (let i = 0; i < SIZE; i++) rms += buf[i] * buf[i]
  rms = Math.sqrt(rms / SIZE)
  if (rms < 0.008) return -1

  // Trim leading/trailing silence
  let r1 = 0,
    r2 = SIZE - 1
  const thres = 0.2
  for (let i = 0; i < SIZE / 2; i++) {
    if (Math.abs(buf[i]) > thres) {
      r1 = i
      break
    }
  }
  for (let i = 1; i < SIZE / 2; i++) {
    if (Math.abs(buf[SIZE - i]) > thres) {
      r2 = SIZE - i
      break
    }
  }

  const buf2 = buf.slice(r1, r2)
  const len = buf2.length
  if (len < 20) return -1

  // Build autocorrelation
  const c = new Float32Array(len)
  for (let i = 0; i < len; i++)
    for (let j = 0; j < len - i; j++) c[i] += buf2[j] * buf2[j + i]

  // Find first dip (d), then highest peak after it
  let d = 0
  while (d < len - 1 && c[d] > c[d + 1]) d++
  let maxval = -1,
    maxpos = -1
  for (let i = d; i < len; i++) {
    if (c[i] > maxval) {
      maxval = c[i]
      maxpos = i
    }
  }
  if (maxpos <= 0 || maxpos >= len - 1) return -1

  // Parabolic interpolation for sub-sample accuracy
  const x1 = c[maxpos - 1],
    x2 = c[maxpos],
    x3 = c[maxpos + 1]
  const a = (x1 + x3 - 2 * x2) / 2
  const b = (x3 - x1) / 2
  const T0 = a !== 0 ? maxpos - b / (2 * a) : maxpos

  return sampleRate / T0
}

// ── Note math ────────────────────────────────────────────────────────────────
const NOTE_NAMES = [
  'C',
  'C#',
  'D',
  'D#',
  'E',
  'F',
  'F#',
  'G',
  'G#',
  'A',
  'A#',
  'B',
]

function freqToNote(freq: number) {
  const semitones = 12 * Math.log2(freq / 440)
  const midi = Math.round(semitones) + 69
  const octave = Math.floor(midi / 12) - 1
  const name = NOTE_NAMES[((midi % 12) + 12) % 12]
  const cents = Math.round((semitones - Math.round(semitones)) * 100)
  return { name, octave, cents, midi }
}

// ── Guitar strings ────────────────────────────────────────────────────────────
const STRINGS = [
  { note: 'E', sub: '2', midi: 40, num: 6 },
  { note: 'A', sub: '2', midi: 45, num: 5 },
  { note: 'D', sub: '3', midi: 50, num: 4 },
  { note: 'G', sub: '3', midi: 55, num: 3 },
  { note: 'B', sub: '3', midi: 59, num: 2 },
  { note: 'E', sub: '4', midi: 64, num: 1 },
]

function closestString(midi: number) {
  return STRINGS.reduce((best, s) =>
    Math.abs(s.midi - midi) < Math.abs(best.midi - midi) ? s : best,
  )
}

// ── Median helper for note smoothing ─────────────────────────────────────────
function medianFreq(arr: number[]): number {
  const sorted = [...arr].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)]
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Tuner() {
  const [active, setActive] = useState(false)
  const [note, setNote] = useState('—')
  const [octave, setOctave] = useState<number | null>(null)
  const [cents, setCents] = useState(0)
  const [freq, setFreq] = useState<number | null>(null)
  const [strNum, setStrNum] = useState<number | null>(null)
  const [inTune, setInTune] = useState(false)
  const [hasSignal, setHasSignal] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const mountedRef = useRef(true)
  const startingRef = useRef(false)

  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number>(0)
  // Keep last N frequency readings for smoothing
  const freqHistRef = useRef<number[]>([])

  const tick = useCallback(function tickFrame() {
    const analyser = analyserRef.current
    if (!analyser) return

    const buf = new Float32Array(analyser.fftSize)
    analyser.getFloatTimeDomainData(buf)
    const f = autoCorrelate(buf, analyser.context.sampleRate)

    if (f > 50 && f < 1400) {
      // Rolling median over last 5 readings for stability
      const hist = freqHistRef.current
      hist.push(f)
      if (hist.length > 5) hist.shift()
      const smoothF = medianFreq(hist)

      const n = freqToNote(smoothF)
      const s = closestString(n.midi)

      setNote(n.name)
      setOctave(n.octave)
      setCents(n.cents)
      setFreq(Math.round(smoothF * 10) / 10)
      setStrNum(s.num)
      setInTune(Math.abs(n.cents) <= 5)
      setHasSignal(true)
    } else {
      freqHistRef.current = []
      setHasSignal(false)
    }

    rafRef.current = requestAnimationFrame(tickFrame)
  }, [])

  const start = async () => {
    if (startingRef.current) return
    setMicError(null)

    if (typeof window !== 'undefined' && !window.isSecureContext) {
      setMicError(
        'El afinador requiere HTTPS. En desarrollo usá http://localhost.',
      )
      return
    }
    if (!navigator?.mediaDevices?.getUserMedia) {
      setMicError(
        'Tu navegador no soporta acceso al micrófono. Usá Chrome, Firefox o Edge actualizado.',
      )
      return
    }

    startingRef.current = true
    setStarting(true)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
        video: false,
      })
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      const ctx = new (
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext
      )()
      ctxRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 4096 // larger = better low-freq accuracy (E2 = 82 Hz)
      analyser.smoothingTimeConstant = 0
      source.connect(analyser)
      analyserRef.current = analyser
      freqHistRef.current = []
      setActive(true)
      rafRef.current = requestAnimationFrame(tick)
    } catch (err) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      void ctxRef.current?.close()
      const name = (err as DOMException)?.name ?? ''
      const messages: Record<string, string> = {
        NotAllowedError:
          'Permiso denegado. Hacé clic en el candado de la barra de dirección y permitile el micrófono.',
        PermissionDeniedError:
          'Permiso denegado. Hacé clic en el candado de la barra de dirección y permitile el micrófono.',
        NotFoundError:
          'No se encontró ningún micrófono. Conectá uno e intentá de nuevo.',
        DevicesNotFoundError:
          'No se encontró ningún micrófono. Conectá uno e intentá de nuevo.',
        NotReadableError:
          'El micrófono está en uso por otra app. Cerrá otras pestañas o aplicaciones.',
        TrackStartError:
          'El micrófono está en uso por otra app. Cerrá otras pestañas o aplicaciones.',
        SecurityError: 'Bloqueado por seguridad. Necesitás HTTPS o localhost.',
      }
      setMicError(
        messages[name] ??
          `Error: ${name || 'desconocido'}. Revisá los permisos del navegador.`,
      )
    } finally {
      startingRef.current = false
      if (mountedRef.current) setStarting(false)
    }
  }

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    ctxRef.current?.close()
    analyserRef.current = null
    freqHistRef.current = []
    setActive(false)
    setNote('—')
    setOctave(null)
    setCents(0)
    setFreq(null)
    setStrNum(null)
    setInTune(false)
    setHasSignal(false)
    setMicError(null)
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      stop()
    }
  }, [stop])

  const tuneColor = !hasSignal ? '#7a897a' : inTune ? '#426b37' : '#ad573a'
  return (
    <div className="mx-auto flex w-full max-w-sm flex-col items-center gap-7">
      <div
        className="flex w-full gap-2"
        aria-label="Cuerdas en afinación estándar"
      >
        {STRINGS.map((s) => (
          <div
            key={s.num}
            className={`flex-1 rounded-xl border py-3 text-center ${active && hasSignal && strNum === s.num ? 'border-[#64804f] bg-[#d9f58a]' : 'border-[#dce2d8] bg-[#f5f7f0]'}`}
          >
            <span className="font-mono text-lg font-medium">{s.note}</span>
            <span className="muted ml-0.5 text-[10px]">{s.sub}</span>
          </div>
        ))}
      </div>
      <div
        className="flex h-52 w-52 flex-col items-center justify-center rounded-full border-[12px] border-[#edf1e6] bg-[#f8faf4]"
        style={{ borderColor: hasSignal && inTune ? '#d9f58a' : undefined }}
      >
        <p className="eyebrow mb-3">{active ? 'Escuchando' : 'Todo listo'}</p>
        <p
          className="font-mono text-7xl font-medium"
          style={{ color: tuneColor }}
        >
          {hasSignal ? note : '—'}
          <span className="text-2xl">{hasSignal ? octave : ''}</span>
        </p>
        <p className="muted mt-3 font-mono text-xs">
          {hasSignal && freq ? `${freq} Hz` : 'A4 = 440 Hz'}
        </p>
      </div>
      <div className="w-full">
        <div className="relative h-3 rounded-full bg-[#edf1e6]">
          <span className="absolute inset-y-0 left-[45%] w-[10%] bg-[#d9f58a]" />
          <span
            className="absolute -top-1 h-5 w-1 rounded bg-[#284e3e] transition-[left]"
            style={{
              left: `${hasSignal ? Math.max(0, Math.min(99, cents + 50)) : 50}%`,
            }}
          />
        </div>
        <div className="muted mt-3 flex justify-between text-[10px]">
          <span>Más grave</span>
          <span className="font-mono">
            {hasSignal ? `${cents > 0 ? '+' : ''}${cents} cents` : '0 cents'}
          </span>
          <span>Más agudo</span>
        </div>
      </div>
      <p
        role="status"
        className="flex h-6 items-center gap-2 text-sm font-bold"
        style={{ color: tuneColor }}
      >
        {!active ? (
          'Activa el micrófono para empezar'
        ) : !hasSignal ? (
          'Pulsa una cuerda'
        ) : inTune ? (
          <>
            <Check size={17} /> Afinado
          </>
        ) : cents < 0 ? (
          'Sube un poco la afinación'
        ) : (
          'Baja un poco la afinación'
        )}
      </p>
      {micError && (
        <p
          role="alert"
          className="w-full rounded-xl bg-[#fff0e8] p-4 text-xs leading-6 text-[#8b442d]"
        >
          {micError}
        </p>
      )}
      <button
        disabled={starting}
        onClick={active ? stop : start}
        className={`${active ? 'btn-soft' : 'btn-primary'} w-full`}
      >
        {active ? <MicOff size={18} /> : <Mic size={18} />}
        {starting
          ? 'Esperando permiso…'
          : active
            ? 'Detener micrófono'
            : 'Activar micrófono'}
      </button>
      <p className="muted text-center text-[11px]">
        Afinación cromática · E A D G B E
      </p>
    </div>
  )
}

'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

// ── Autocorrelation pitch detection ──────────────────────────────────────────
function autoCorrelate(buf: Float32Array, sampleRate: number): number {
  const SIZE = buf.length

  // RMS check — too quiet = no signal
  let rms = 0
  for (let i = 0; i < SIZE; i++) rms += buf[i] * buf[i]
  rms = Math.sqrt(rms / SIZE)
  if (rms < 0.008) return -1

  // Trim leading/trailing silence
  let r1 = 0, r2 = SIZE - 1
  const thres = 0.2
  for (let i = 0; i < SIZE / 2; i++) { if (Math.abs(buf[i]) > thres) { r1 = i; break } }
  for (let i = 1; i < SIZE / 2; i++) { if (Math.abs(buf[SIZE - i]) > thres) { r2 = SIZE - i; break } }

  const buf2 = buf.slice(r1, r2)
  const len = buf2.length
  if (len < 20) return -1

  // Build autocorrelation
  const c = new Float32Array(len)
  for (let i = 0; i < len; i++)
    for (let j = 0; j < len - i; j++)
      c[i] += buf2[j] * buf2[j + i]

  // Find first dip (d), then highest peak after it
  let d = 0
  while (d < len - 1 && c[d] > c[d + 1]) d++
  let maxval = -1, maxpos = -1
  for (let i = d; i < len; i++) {
    if (c[i] > maxval) { maxval = c[i]; maxpos = i }
  }
  if (maxpos <= 0 || maxpos >= len - 1) return -1

  // Parabolic interpolation for sub-sample accuracy
  const x1 = c[maxpos - 1], x2 = c[maxpos], x3 = c[maxpos + 1]
  const a = (x1 + x3 - 2 * x2) / 2
  const b = (x3 - x1) / 2
  const T0 = a !== 0 ? maxpos - b / (2 * a) : maxpos

  return sampleRate / T0
}

// ── Note math ────────────────────────────────────────────────────────────────
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

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
    Math.abs(s.midi - midi) < Math.abs(best.midi - midi) ? s : best
  )
}

// ── SVG helpers ───────────────────────────────────────────────────────────────
// Convention: angle 0° = top, increases clockwise
// x = cx + r * sin(deg * PI/180)
// y = cy - r * cos(deg * PI/180)
function pt(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180
  return { x: cx + r * Math.sin(rad), y: cy - r * Math.cos(rad) }
}

function arc(cx: number, cy: number, r: number, a1: number, a2: number) {
  const s = pt(cx, cy, r, a1)
  const e = pt(cx, cy, r, a2)
  const large = Math.abs(a2 - a1) > 180 ? 1 : 0
  const sweep = a2 > a1 ? 1 : 0
  return `M ${s.x.toFixed(2)} ${s.y.toFixed(2)} A ${r} ${r} 0 ${large} ${sweep} ${e.x.toFixed(2)} ${e.y.toFixed(2)}`
}

// ── Median helper for note smoothing ─────────────────────────────────────────
function medianFreq(arr: number[]): number {
  const sorted = [...arr].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)]
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Tuner() {
  const [active, setActive]       = useState(false)
  const [note, setNote]           = useState('—')
  const [octave, setOctave]       = useState<number | null>(null)
  const [cents, setCents]         = useState(0)
  const [freq, setFreq]           = useState<number | null>(null)
  const [strNum, setStrNum]       = useState<number | null>(null)
  const [inTune, setInTune]       = useState(false)
  const [hasSignal, setHasSignal] = useState(false)
  const [micError, setMicError]   = useState<string | null>(null)

  const streamRef   = useRef<MediaStream | null>(null)
  const ctxRef      = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef      = useRef<number>(0)
  // Keep last N frequency readings for smoothing
  const freqHistRef = useRef<number[]>([])

  const tick = useCallback(() => {
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

    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const start = async () => {
    setMicError(null)

    if (typeof window !== 'undefined' && !window.isSecureContext) {
      setMicError('El afinador requiere HTTPS. En desarrollo usá http://localhost.')
      return
    }
    if (!navigator?.mediaDevices?.getUserMedia) {
      setMicError('Tu navegador no soporta acceso al micrófono. Usá Chrome, Firefox o Edge actualizado.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false })
      streamRef.current = stream
      const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
      ctxRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 4096   // larger = better low-freq accuracy (E2 = 82 Hz)
      analyser.smoothingTimeConstant = 0
      source.connect(analyser)
      analyserRef.current = analyser
      freqHistRef.current = []
      setActive(true)
      rafRef.current = requestAnimationFrame(tick)
    } catch (err) {
      const name = (err as DOMException)?.name ?? ''
      const messages: Record<string, string> = {
        NotAllowedError:      'Permiso denegado. Hacé clic en el candado de la barra de dirección y permitile el micrófono.',
        PermissionDeniedError:'Permiso denegado. Hacé clic en el candado de la barra de dirección y permitile el micrófono.',
        NotFoundError:        'No se encontró ningún micrófono. Conectá uno e intentá de nuevo.',
        DevicesNotFoundError: 'No se encontró ningún micrófono. Conectá uno e intentá de nuevo.',
        NotReadableError:     'El micrófono está en uso por otra app. Cerrá otras pestañas o aplicaciones.',
        TrackStartError:      'El micrófono está en uso por otra app. Cerrá otras pestañas o aplicaciones.',
        SecurityError:        'Bloqueado por seguridad. Necesitás HTTPS o localhost.',
      }
      setMicError(messages[name] ?? `Error: ${name || 'desconocido'}. Revisá los permisos del navegador.`)
    }
  }

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
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

  useEffect(() => () => stop(), [stop])

  // ── SVG gauge math ──
  // Gauge arc: -120° to +120° (0° = top = in tune)
  const SPAN = 120          // degrees each side
  const CX = 150, CY = 160, R = 120
  const needleDeg = Math.max(-SPAN, Math.min(SPAN, (cents / 50) * SPAN))

  const absCents  = Math.abs(cents)
  const tuneColor = !hasSignal ? '#ffffff15'
    : absCents <= 5  ? '#facc15'
    : absCents <= 20 ? '#fb923c'
    : '#f87171'

  return (
    <div className="flex flex-col items-center gap-6 w-full max-w-sm mx-auto select-none">

      {/* ── String buttons ── */}
      <div className="flex items-stretch gap-1.5">
        {STRINGS.map((s) => {
          const isActive = active && hasSignal && strNum === s.num
          return (
            <div
              key={`${s.note}${s.sub}`}
              className={`flex flex-col items-center justify-center gap-0.5 w-11 py-2.5 rounded-xl border transition-all duration-150 ${
                isActive
                  ? 'border-yellow-400 bg-yellow-400/10'
                  : 'border-white/8 bg-white/3'
              }`}
            >
              <span className={`font-mono font-black text-base leading-none ${isActive ? 'text-yellow-400' : 'text-white/40'}`}>
                {s.note}
              </span>
              <span className={`font-mono text-[9px] ${isActive ? 'text-yellow-400/70' : 'text-white/20'}`}>
                {s.sub}
              </span>
            </div>
          )
        })}
      </div>

      {/* ── SVG Gauge ── */}
      <div className="relative w-full" style={{ aspectRatio: '300/180' }}>
        <svg viewBox="0 0 300 180" className="w-full h-full" aria-hidden>
          {/* Background arc track */}
          <path d={arc(CX, CY, R, -SPAN, SPAN)} fill="none" stroke="#ffffff0a" strokeWidth="20" strokeLinecap="round" />

          {/* Colored zones */}
          <path d={arc(CX, CY, R, -SPAN, -SPAN * 0.4)}  fill="none" stroke="#f8717122" strokeWidth="16" strokeLinecap="round" />
          <path d={arc(CX, CY, R, -SPAN * 0.4, -SPAN * 0.15)} fill="none" stroke="#fb923c22" strokeWidth="16" strokeLinecap="round" />
          <path d={arc(CX, CY, R, -SPAN * 0.15, SPAN * 0.15)} fill="none" stroke="#22c55e28" strokeWidth="16" strokeLinecap="round" />
          <path d={arc(CX, CY, R,  SPAN * 0.15, SPAN * 0.4)}  fill="none" stroke="#fb923c22" strokeWidth="16" strokeLinecap="round" />
          <path d={arc(CX, CY, R,  SPAN * 0.4, SPAN)}  fill="none" stroke="#f8717122" strokeWidth="16" strokeLinecap="round" />

          {/* Tick marks */}
          {([-SPAN, -SPAN/2, 0, SPAN/2, SPAN] as number[]).map((deg) => {
            const inner = pt(CX, CY, R - 14, deg)
            const outer = pt(CX, CY, R + 14, deg)
            return (
              <line key={deg}
                x1={inner.x.toFixed(1)} y1={inner.y.toFixed(1)}
                x2={outer.x.toFixed(1)} y2={outer.y.toFixed(1)}
                stroke={deg === 0 ? '#ffffff35' : '#ffffff12'}
                strokeWidth={deg === 0 ? 2 : 1}
              />
            )
          })}

          {/* Tick labels */}
          {([
            { d: -SPAN,    label: '♭' },
            { d: 0,        label: '♦' },
            { d:  SPAN,    label: '♯' },
          ]).map(({ d, label }) => {
            const p = pt(CX, CY, R + 26, d)
            return (
              <text key={d}
                x={p.x.toFixed(1)} y={p.y.toFixed(1)}
                textAnchor="middle" dominantBaseline="middle"
                fill="#ffffff20" fontSize="13"
              >
                {label}
              </text>
            )
          })}

          {/* Needle shadow */}
          {(() => {
            const tip  = pt(CX, CY, R - 8,  needleDeg)
            const base = pt(CX, CY, 12, needleDeg + 180)
            return (
              <line
                x1={base.x.toFixed(1)} y1={base.y.toFixed(1)}
                x2={tip.x.toFixed(1)}  y2={tip.y.toFixed(1)}
                stroke="#000" strokeWidth="5" strokeLinecap="round" opacity="0.3"
              />
            )
          })()}

          {/* Needle */}
          {(() => {
            const tip  = pt(CX, CY, R - 8,  needleDeg)
            const base = pt(CX, CY, 12, needleDeg + 180)
            return (
              <line
                x1={base.x.toFixed(1)} y1={base.y.toFixed(1)}
                x2={tip.x.toFixed(1)}  y2={tip.y.toFixed(1)}
                stroke={tuneColor} strokeWidth="2.5" strokeLinecap="round"
              />
            )
          })()}

          {/* Pivot dot */}
          <circle cx={CX} cy={CY} r="6" fill={tuneColor} />
          <circle cx={CX} cy={CY} r="2.5" fill="#0d0d0d" />
        </svg>

        {/* Note display centered below pivot */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1 pointer-events-none">
          <span
            className="font-black font-mono text-5xl leading-none"
            style={{ color: hasSignal ? tuneColor : '#ffffff25', transition: 'color 0.15s' }}
          >
            {note}
          </span>
          <span className="text-white/25 text-sm font-mono mt-0.5">
            {octave !== null ? octave : ''}
          </span>
        </div>
      </div>

      {/* ── Data row ── */}
      <div className="flex items-center gap-5 text-center">
        <div className="flex flex-col gap-0.5">
          <span className="text-[9px] text-white/20 uppercase tracking-widest">Hz</span>
          <span className="text-sm font-mono text-white/50">{freq != null ? freq : '—'}</span>
        </div>
        <div className="w-px h-7 bg-white/8" />
        <div className="flex flex-col gap-0.5">
          <span className="text-[9px] text-white/20 uppercase tracking-widest">Cents</span>
          <span className="text-sm font-mono font-bold" style={{ color: hasSignal ? tuneColor : '#ffffff30' }}>
            {hasSignal ? (cents > 0 ? `+${cents}` : cents) : '—'}
          </span>
        </div>
        <div className="w-px h-7 bg-white/8" />
        <div className="flex flex-col gap-0.5">
          <span className="text-[9px] text-white/20 uppercase tracking-widest">Estado</span>
          <span className="text-sm font-mono" style={{ color: hasSignal ? tuneColor : '#ffffff30' }}>
            {!hasSignal ? '—' : inTune ? 'Afinado' : cents < 0 ? 'Sube' : 'Baja'}
          </span>
        </div>
      </div>

      {/* ── In-tune flash ── */}
      <div className={`h-7 flex items-center transition-all duration-200 ${inTune && hasSignal ? 'opacity-100' : 'opacity-0'}`}>
        <div className="flex items-center gap-2 bg-yellow-400/12 border border-yellow-400/25 rounded-full px-4 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
          <span className="text-yellow-400 text-xs font-bold tracking-widest">AFINADO</span>
        </div>
      </div>

      {/* ── Error ── */}
      {micError && (
        <div className="w-full bg-red-950/50 border border-red-800/40 rounded-xl px-4 py-3 flex flex-col gap-1">
          <span className="text-red-400 text-xs font-semibold">Error de micrófono</span>
          <span className="text-red-300/70 text-xs leading-relaxed">{micError}</span>
        </div>
      )}

      {/* ── Button ── */}
      <button
        onClick={active ? stop : start}
        className={`w-full py-3.5 rounded-xl font-bold text-sm tracking-widest transition-all active:scale-95 ${
          active
            ? 'bg-white/6 border border-white/12 text-white/50 hover:bg-white/10'
            : 'bg-yellow-400 text-gray-950 hover:bg-yellow-300'
        }`}
      >
        {active ? 'DETENER MICRÓFONO' : 'ACTIVAR MICRÓFONO'}
      </button>

      <p className="text-white/15 text-xs text-center">A4 = 440 Hz · EADGBE</p>

    </div>
  )
}

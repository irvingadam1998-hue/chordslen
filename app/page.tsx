'use client'

import { useState, useRef } from 'react'
import UrlInput from '@/components/UrlInput'
import ProgressSteps from '@/components/ProgressSteps'
import ChordTimeline from '@/components/ChordTimeline'
import ChordChart from '@/components/ChordChart'
import YoutubePlayer from '@/components/YoutubePlayer'
import AudioPlayer from '@/components/AudioPlayer'
import LyricsDisplay from '@/components/LyricsDisplay'
import TransposePanel from '@/components/TransposePanel'
import ChordProgressBar from '@/components/ChordProgressBar'
import { AnalysisResult } from '@/lib/types'
import { transposeChord } from '@/lib/transpose'

function extractVideoId(url: string): string | null {
  try {
    const parsed = new URL(url)
    if (parsed.hostname === 'youtu.be') return parsed.pathname.slice(1)
    return parsed.searchParams.get('v')
  } catch { return null }
}

function SectionLabel({ number, title }: { number: string; title: string }) {
  return (
    <div className="flex items-center gap-4 mb-6">
      <span className="text-[10px] font-mono text-yellow-400/60 tracking-widest">{number}</span>
      <h2 className="text-xs font-semibold tracking-widest text-white/40 uppercase">{title}</h2>
      <div className="flex-1 h-px bg-white/5" />
    </div>
  )
}

export default function Home() {
  const [url, setUrl] = useState('')
  const [inputMode, setInputMode] = useState<'url' | 'file'>('url')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [analyzedFile, setAnalyzedFile] = useState<File | null>(null)
  const [step, setStep] = useState<1 | 2 | 3 | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [analyzedUrl, setAnalyzedUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentTime, setCurrentTime] = useState(-1)
  const [capo, setCapo] = useState(0)
  const [shift, setShift] = useState(0)
  const seekRef = useRef<((time: number) => void) | null>(null)

  const transposeBy = ((shift - capo) % 12 + 12) % 12
  const videoId = analyzedUrl ? extractVideoId(analyzedUrl) : null
  const hasLyrics = !!(result?.artist && result?.title)

  const handleAnalyze = async () => {
    if (!url.trim()) return
    setError(null)
    setResult(null)
    setAnalyzedUrl(null)
    setCurrentTime(-1)
    setCapo(0)
    setShift(0)
    setStep(1)

    const t2 = setTimeout(() => setStep(2), 2000)
    const t3 = setTimeout(() => setStep(3), 4000)

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      clearTimeout(t2); clearTimeout(t3)
      const data = await res.json()
      if (!res.ok || data.error) { setError(data.error || 'Error desconocido'); setStep(null); return }
      setResult(data)
      setAnalyzedUrl(url)
      setStep(null)
    } catch (err) {
      clearTimeout(t2); clearTimeout(t3)
      setError(err instanceof Error ? err.message : 'Error de red')
      setStep(null)
    }
  }

  const handleAnalyzeFile = async () => {
    if (!selectedFile) return
    setError(null)
    setResult(null)
    setAnalyzedUrl(null)
    setAnalyzedFile(null)
    setCurrentTime(-1)
    setCapo(0)
    setShift(0)
    setStep(1)

    const t2 = setTimeout(() => setStep(2), 2000)
    const t3 = setTimeout(() => setStep(3), 4000)

    try {
      const formData = new FormData()
      formData.append('audio', selectedFile)
      const res = await fetch('/api/analyze-file', { method: 'POST', body: formData })
      clearTimeout(t2); clearTimeout(t3)
      const data = await res.json()
      if (!res.ok || data.error) { setError(data.error || 'Error desconocido'); setStep(null); return }
      setResult(data)
      setAnalyzedFile(selectedFile)
      setStep(null)
    } catch (err) {
      clearTimeout(t2); clearTimeout(t3)
      setError(err instanceof Error ? err.message : 'Error de red')
      setStep(null)
    }
  }

  const resetSearch = () => {
    setResult(null); setAnalyzedUrl(null); setAnalyzedFile(null); setCurrentTime(-1); setError(null); setCapo(0); setShift(0)
  }

  const totalDuration = result && result.chords_timeline.length > 0
    ? result.chords_timeline[result.chords_timeline.length - 1].time + 30
    : 0

  const uniqueChords = result
    ? new Set(result.chords_timeline.map(c => transposeChord(c.chord, transposeBy))).size
    : 0

  return (
    <div className="min-h-screen text-white flex flex-col">

      <main className="flex-1">

        {/* ════════════════════════════════════
            LANDING — sin resultados
        ════════════════════════════════════ */}
        {!result && (
          <>
            {/* Hero */}
            <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 text-center">
              <div className="max-w-3xl mx-auto flex flex-col items-center gap-8">
                <div className="inline-flex items-center gap-2 bg-yellow-400/10 border border-yellow-400/20 rounded-full px-4 py-1.5 text-yellow-400 text-xs font-medium tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
                  Análisis de audio con IA
                </div>

                <h1 className="text-5xl sm:text-7xl font-black tracking-tighter leading-none">
                  Descubre los acordes<br />
                  <span className="text-yellow-400">de cualquier canción</span>
                </h1>

                <p className="text-white/40 text-lg max-w-md leading-relaxed">
                  Pega una URL de YouTube y ChordLens analiza el audio para extraer los acordes reales, sincronizados con el video.
                </p>

                <div className="w-full max-w-xl flex flex-col gap-3">
                  {/* Tab switcher */}
                  <div className="flex rounded-xl bg-white/5 border border-white/10 p-1 gap-1">
                    <button
                      onClick={() => setInputMode('url')}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold tracking-wider transition-all ${inputMode === 'url' ? 'bg-yellow-400 text-gray-950' : 'text-white/40 hover:text-white/70'}`}
                    >
                      URL de YouTube
                    </button>
                    <button
                      onClick={() => setInputMode('file')}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold tracking-wider transition-all ${inputMode === 'file' ? 'bg-yellow-400 text-gray-950' : 'text-white/40 hover:text-white/70'}`}
                    >
                      Subir archivo
                    </button>
                  </div>

                  {inputMode === 'url' ? (
                    <UrlInput url={url} onChange={setUrl} onSubmit={handleAnalyze} disabled={step !== null} />
                  ) : (
                    <div className="flex gap-2 w-full">
                      <label className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/10 cursor-pointer hover:border-yellow-400/40 transition-all text-sm">
                        <span className="text-white/40 shrink-0">MP3 / WAV / FLAC</span>
                        <span className="text-white truncate">{selectedFile ? selectedFile.name : <span className="text-white/20">Selecciona un archivo de audio...</span>}</span>
                        <input
                          type="file"
                          accept="audio/*"
                          className="hidden"
                          disabled={step !== null}
                          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                        />
                      </label>
                      <button
                        onClick={handleAnalyzeFile}
                        disabled={step !== null || !selectedFile}
                        className="px-5 py-3 rounded-xl bg-yellow-400 text-gray-950 font-bold text-sm tracking-widest hover:bg-yellow-300 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        {step !== null ? '...' : 'ANALIZAR'}
                      </button>
                    </div>
                  )}

                  {step !== null && <ProgressSteps currentStep={step} />}
                  {error && (
                    <div className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-xl px-4 py-3 text-left">
                      {error}
                    </div>
                  )}
                </div>

                <p className="text-white/20 text-xs">
                  El análisis tarda entre 30 y 90 segundos · YouTube o archivo local MP3/WAV/FLAC
                </p>
              </div>
            </section>

            {/* Cómo funciona */}
            <section id="como-funciona" className="border-t border-white/5 py-24 px-6">
              <div className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                  <p className="text-yellow-400 text-xs font-mono tracking-widest mb-3">PROCESO</p>
                  <h2 className="text-3xl font-bold">Cómo funciona</h2>
                </div>
                <div className="grid sm:grid-cols-3 gap-8">
                  {[
                    { n: '01', icon: '🔗', title: 'Pega la URL', desc: 'Copia el link de cualquier video de YouTube y pégalo en el campo de búsqueda.' },
                    { n: '02', icon: '🎵', title: 'Análisis de audio', desc: 'Descargamos el audio y usamos análisis de frecuencia para detectar las notas y acordes presentes.' },
                    { n: '03', icon: '🎸', title: 'Visualiza los acordes', desc: 'Obtén un timeline sincronizado, mapa de acordes, transposición con capo y mucho más.' },
                  ].map(({ n, icon, title, desc }) => (
                    <div key={n} className="flex flex-col gap-4 p-6 rounded-2xl bg-white/3 border border-white/8 hover:border-white/15 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="text-3xl">{icon}</span>
                        <span className="text-white/15 font-mono text-sm">{n}</span>
                      </div>
                      <div>
                        <h3 className="font-bold text-white mb-1">{title}</h3>
                        <p className="text-white/40 text-sm leading-relaxed">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Features */}
            <section className="border-t border-white/5 py-24 px-6">
              <div className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                  <p className="text-yellow-400 text-xs font-mono tracking-widest mb-3">FUNCIONALIDADES</p>
                  <h2 className="text-3xl font-bold">Todo lo que necesitas</h2>
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { icon: '🎹', title: 'Acordes reales', desc: 'Detecta los acordes del audio, no de la partitura. Lo que suena, no lo que está escrito.' },
                    { icon: '🎸', title: 'Capo y transposición', desc: 'Selecciona el traste del capo y los acordes se adaptan automáticamente a las posiciones que tienes que tocar.' },
                    { icon: '📊', title: 'Mapa visual', desc: 'Visualiza toda la canción en una barra de colores que muestra qué acorde suena en cada momento.' },
                    { icon: '▶️', title: 'Sincronizado con video', desc: 'El acorde activo se resalta en tiempo real mientras el video se reproduce.' },
                    { icon: '📝', title: 'Letra incluida', desc: 'Si está disponible, la letra de la canción aparece al lado del video para que puedas cantar.' },
                    { icon: '⚡', title: 'Sin registro', desc: 'No hace falta cuenta, login ni pago. Solo pega la URL y listo.' },
                  ].map(({ icon, title, desc }) => (
                    <div key={title} className="flex gap-4 p-5 rounded-xl bg-white/3 border border-white/8">
                      <span className="text-2xl shrink-0">{icon}</span>
                      <div>
                        <h3 className="font-semibold text-sm text-white mb-1">{title}</h3>
                        <p className="text-white/40 text-xs leading-relaxed">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* CTA bottom */}
            <section className="border-t border-white/5 py-24 px-6 text-center">
              <div className="max-w-xl mx-auto flex flex-col items-center gap-6">
                <h2 className="text-3xl font-bold">¿Listo para empezar?</h2>
                <p className="text-white/40 text-sm">Pega cualquier link de YouTube y descubre los acordes en segundos.</p>
                <UrlInput url={url} onChange={setUrl} onSubmit={handleAnalyze} disabled={step !== null} />
              </div>
            </section>
          </>
        )}

        {/* ════════════════════════════════════
            RESULTADOS
        ════════════════════════════════════ */}
        {result && result.chords_timeline.length > 0 && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col gap-14">

            {/* Song header */}
            <div className="flex items-start gap-4 justify-between">
              <div>
                <p className="text-white/30 text-xs font-mono tracking-widest uppercase mb-1">Resultado del análisis</p>
                {result.title && <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight">{result.title}</h1>}
                {result.artist && <p className="text-white/40 text-base mt-1">{result.artist}</p>}
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Acordes detectados', value: result.chords_timeline.length, mono: true },
                { label: 'Acordes únicos', value: uniqueChords, mono: true },
                { label: 'Capo activo', value: capo === 0 ? 'Sin capo' : `Traste ${capo}`, mono: false },
                { label: 'Transposición', value: transposeBy === 0 ? 'Original' : `${transposeBy > 6 ? `−${12 - transposeBy}` : `+${transposeBy}`} semitonos`, mono: false },
              ].map(({ label, value, mono }) => (
                <div key={label} className="bg-white/3 border border-white/8 rounded-xl p-4 flex flex-col gap-2">
                  <span className="text-[10px] text-white/30 uppercase tracking-wider">{label}</span>
                  <span className={`text-xl font-bold text-white ${mono ? 'font-mono' : ''}`}>{value}</span>
                </div>
              ))}
            </div>

            {/* 01 — Reproducción */}
            <section className="flex flex-col gap-0">
              <SectionLabel number="01" title="Reproducción" />
              <div className={`grid gap-6 ${hasLyrics && videoId ? 'lg:grid-cols-[3fr_2fr]' : 'grid-cols-1 max-w-4xl'}`}>
                {videoId && (
                  <YoutubePlayer key={videoId} videoId={videoId} onTimeUpdate={setCurrentTime} seekRef={seekRef} />
                )}
                {analyzedFile && !videoId && (
                  <AudioPlayer key={analyzedFile.name} file={analyzedFile} onTimeUpdate={setCurrentTime} seekRef={seekRef} />
                )}
                {hasLyrics && videoId && (
                  <LyricsDisplay artist={result.artist!} title={result.title!} />
                )}
              </div>
            </section>

            {/* 02 — Mapa de acordes */}
            <section className="flex flex-col gap-0">
              <SectionLabel number="02" title="Mapa de acordes" />
              <ChordProgressBar
                chords={result.chords_timeline}
                totalDuration={totalDuration}
                currentTime={currentTime}
                transposeBy={transposeBy}
                onSeek={(t) => seekRef.current?.(t)}
              />
              <p className="text-xs text-white/20 mt-2">
                Cada segmento representa un acorde. Hacé click para saltar a esa parte.
              </p>
            </section>

            {/* 03 — Transposición y acordes */}
            <section className="flex flex-col gap-0">
              <SectionLabel number="03" title="Transposición y acordes" />
              <div className="grid lg:grid-cols-[300px_1fr] gap-6 items-start">
                <TransposePanel capo={capo} shift={shift} onCapoChange={setCapo} onShiftChange={setShift} />
                <div className="bg-white/3 border border-white/8 rounded-2xl p-6">
                  <ChordTimeline
                    chords={result.chords_timeline}
                    currentTime={currentTime}
                    transposeBy={transposeBy}
                    totalDuration={totalDuration}
                    onSeek={(t) => seekRef.current?.(t)}
                  />
                </div>
              </div>
            </section>

            {/* 04 — Distribución */}
            <section className="flex flex-col gap-0">
              <SectionLabel number="04" title="Distribución de acordes" />
              <div className="bg-white/3 border border-white/8 rounded-2xl p-6">
                <ChordChart chords={result.chords_timeline} transposeBy={transposeBy} />
              </div>
            </section>

            {/* Nueva búsqueda */}
            <section className="flex flex-col gap-0 pb-8">
              <SectionLabel number="05" title="Analizar otra canción" />
              <div className="max-w-xl flex flex-col gap-3">
                <UrlInput url={url} onChange={setUrl} onSubmit={handleAnalyze} disabled={step !== null} />
                {step !== null && <ProgressSteps currentStep={step} />}
                {error && (
                  <div className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-xl px-4 py-3">
                    {error}
                  </div>
                )}
              </div>
            </section>

          </div>
        )}

        {result && result.chords_timeline.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-6 text-center">
            <p className="text-white/20 text-lg">No se detectaron acordes en este audio.</p>
            <p className="text-white/10 text-sm">Probá con otro video o una canción con más instrumentos melódicos.</p>
            <button onClick={resetSearch} className="mt-4 text-sm text-yellow-400 border border-yellow-400/30 rounded-lg px-4 py-2 hover:bg-yellow-400/10 transition-colors">
              Intentar con otra canción
            </button>
          </div>
        )}
      </main>

    </div>
  )
}

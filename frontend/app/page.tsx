"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  AudioLines,
  BookOpen,
  Check,
  Clock3,
  Download,
  FileAudio,
  Guitar,
  Headphones,
  Info,
  Link2,
  ListMusic,
  Music2,
  Upload,
  TriangleAlert,
} from "lucide-react";
import UrlInput from "@/components/UrlInput";
import ProgressSteps from "@/components/ProgressSteps";
import ChordChart from "@/components/ChordChart";
import YoutubePlayer from "@/components/YoutubePlayer";
import AudioPlayer from "@/components/AudioPlayer";
import LyricsDisplay from "@/components/LyricsDisplay";
import TransposePanel from "@/components/TransposePanel";
import ChordProgressBar from "@/components/ChordProgressBar";
import ChordDiagram from "@/components/ChordDiagram";
import { AnalysisResult } from "@/lib/types";
import { transposeChord } from "@/lib/transpose";

class AnalysisError extends Error {
  constructor(
    message: string,
    public fallback?: string,
    public code?: string,
  ) {
    super(message);
  }
}
function extractVideoId(url: string) {
  try {
    const u = new URL(url);
    return u.hostname === "youtu.be"
      ? u.pathname.slice(1)
      : u.searchParams.get("v") ||
          u.pathname.match(/^\/(?:shorts|embed|live)\/([\w-]{11})/)?.[1] ||
          null;
  } catch {
    return null;
  }
}
function timeLabel(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}
const example: AnalysisResult = {
  success: true,
  notes_count: 0,
  title: "Una progresión para empezar",
  duration: 16,
  key: "C major",
  chords_timeline: ["C", "Am", "F", "G", "Cmaj7", "Am7", "Fsus2", "G7"].map(
    (chord, i) => ({
      chord,
      time: i * 2,
      end: i * 2 + 2,
      time_str: timeLabel(i * 2),
      measure: i + 1,
    }),
  ),
};

export default function Home() {
  const [url, setUrl] = useState("");
  const [inputMode, setInputMode] = useState<"url" | "file">("url");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analyzedFile, setAnalyzedFile] = useState<File | null>(null);
  const [analyzedUrl, setAnalyzedUrl] = useState<string | null>(null);
  const [step, setStep] = useState<1 | 2 | 3 | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<AnalysisError | null>(null);
  const [currentTime, setCurrentTime] = useState(-1);
  const [playerDuration, setPlayerDuration] = useState(0);
  const [capo, setCapo] = useState(0);
  const [shift, setShift] = useState(0);
  const [demo, setDemo] = useState(false);
  const [lyricsOpen, setLyricsOpen] = useState(false);
  const seekRef = useRef<((time: number) => void) | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  useEffect(() => () => requestRef.current?.abort(), []);
  const transposeBy = (((shift - capo) % 12) + 12) % 12;
  const videoId = analyzedUrl ? extractVideoId(analyzedUrl) : null;
  const duration =
    result?.duration ||
    playerDuration ||
    result?.chords_timeline.at(-1)?.end ||
    0;
  const chords = result?.chords_timeline ?? [];
  const unique = new Set(
    chords.filter((c) => c.chord !== "N").map((c) => c.chord),
  ).size;

  function reset() {
    requestRef.current?.abort();
    setResult(null);
    setError(null);
    setAnalyzedUrl(null);
    setAnalyzedFile(null);
    setCurrentTime(-1);
    setPlayerDuration(0);
    setCapo(0);
    setShift(0);
    setDemo(false);
    setLyricsOpen(false);
    setStep(null);
  }
  async function waitForJob(endpoint: string, signal: AbortSignal) {
    const started = Date.now();
    while (Date.now() - started < 10 * 60 * 1000) {
      const response = await fetch(endpoint, { signal });
      const data = await response.json();
      if (!response.ok || data.status === "failed" || data.success === false)
        throw new AnalysisError(
          data.error || "No se pudo completar el análisis.",
          data.fallback,
          data.code,
        );
      if (data.status === "done") return data;
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    throw new AnalysisError(
      "El análisis tardó más de lo esperado. Inténtalo de nuevo en unos minutos.",
    );
  }
  async function analyze() {
    if (
      step ||
      (inputMode === "url" && !url.trim()) ||
      (inputMode === "file" && !selectedFile)
    )
      return;
    reset();
    const controller = new AbortController();
    requestRef.current = controller;
    setStep(1);
    try {
      let response: Response;
      if (inputMode === "url") {
        response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
          signal: controller.signal,
        });
      } else {
        const ticketResponse = await fetch("/api/analyze-file", {
          method: "POST",
          signal: controller.signal,
        });
        const ticket = await ticketResponse.json();
        if (!ticketResponse.ok)
          throw new AnalysisError(
            ticket.error || "No se pudo iniciar la subida.",
          );
        if (!selectedFile || selectedFile.size > ticket.maxBytes)
          throw new AnalysisError(
            `El archivo supera el límite de ${Math.floor(ticket.maxBytes / 1024 / 1024)} MB.`,
          );
        const form = new FormData();
        form.append("audio", selectedFile);
        response = await fetch(ticket.uploadUrl, {
          method: "POST",
          headers: { "X-Upload-Token": ticket.token },
          body: form,
          signal: controller.signal,
        });
      }
      let data = await response.json();
      if (!response.ok || data.error || data.success === false)
        throw new AnalysisError(
          data.error || "No se pudo analizar el audio.",
          data.fallback,
          data.code,
        );
      const job = data.jobId || data.job_id;
      if (response.status === 202 && job) {
        setStep(2);
        data = await waitForJob(
          `/api/analyze/status/${job}`,
          controller.signal,
        );
      }
      if (!data || !Array.isArray(data.chords_timeline))
        throw new AnalysisError(
          "El servicio no devolvió una secuencia de acordes válida.",
        );
      setResult(data);
      if (inputMode === "url") setAnalyzedUrl(url);
      else setAnalyzedFile(selectedFile);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(
        err instanceof AnalysisError
          ? err
          : new AnalysisError(
              err instanceof Error
                ? err.message
                : "No se pudo conectar con el servidor.",
            ),
      );
    } finally {
      if (!controller.signal.aborted) setStep(null);
    }
  }
  function seek(time: number) {
    seekRef.current?.(time);
    setCurrentTime(time);
  }
  function exportChords() {
    const content = [
      `${result?.title || "ChordLens"}`,
      `Capo: ${capo} · Transposición: ${shift} semitonos`,
      "",
      ...chords.map(
        (c) => `${c.time_str}\t${transposeChord(c.chord, transposeBy)}`,
      ),
    ].join("\n");
    const href = URL.createObjectURL(
      new Blob([content], { type: "text/plain;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = href;
    link.download = "chordlens-acordes.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  }

  return (
    <main className="shell py-8 sm:py-12">
      {!result ? (
        <>
          <section className="arrival grid items-center gap-12 py-4 lg:grid-cols-[1.05fr_1fr] lg:gap-20 lg:py-10">
            <div>
              <p className="eyebrow mb-6 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[#537548]" /> Tu
                espacio para entender la música
              </p>
              <h1 className="max-w-xl text-[44px] font-extrabold leading-[1.07] tracking-[-.055em] sm:text-6xl lg:text-[68px]">
                De escucharla
                <br />a{" "}
                <span className="relative inline-block text-[#68874d]">
                  poder tocarla.
                </span>
              </h1>
              <p className="muted mt-6 max-w-md text-base leading-7">
                Encuentra los acordes de tu canción, sigue cada cambio y llévala
                a tu instrumento. A tu ritmo.
              </p>
              <div id="analizar" className="panel mt-8 scroll-mt-28 p-5 sm:p-6">
                <div
                  className="mb-6 flex gap-1 rounded-xl bg-[#eff2e9] p-1"
                  aria-label="Fuente de audio"
                >
                  <button
                    disabled={!!step}
                    aria-pressed={inputMode === "url"}
                    onClick={() => setInputMode("url")}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold ${inputMode === "url" ? "bg-white shadow-sm" : "muted"}`}
                  >
                    <Link2 size={16} /> YouTube
                  </button>
                  <button
                    disabled={!!step}
                    aria-pressed={inputMode === "file"}
                    onClick={() => setInputMode("file")}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold ${inputMode === "file" ? "bg-white shadow-sm" : "muted"}`}
                  >
                    <Upload size={16} /> Archivo de audio
                  </button>
                </div>
                {inputMode === "url" ? (
                  <UrlInput
                    url={url}
                    onChange={setUrl}
                    onSubmit={analyze}
                    disabled={!!step}
                  />
                ) : (
                  <div className="flex flex-col gap-3">
                    <label
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        if (!step)
                          setSelectedFile(e.dataTransfer.files[0] ?? null);
                      }}
                      className="relative flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-[#9aaf8f] bg-[#f7f9f2] px-4 py-6 text-center focus-within:outline focus-within:outline-2 focus-within:outline-[#4c856c]"
                    >
                      <FileAudio size={25} className="mb-1 text-[#66824e]" />
                      <span className="max-w-full truncate text-sm font-semibold">
                        {selectedFile?.name || "Elige o arrastra tu archivo"}
                      </span>
                      <span className="muted text-[11px]">
                        MP3, WAV, FLAC, M4A u OGG · hasta 50 MB
                      </span>
                      <input
                        type="file"
                        aria-label="Seleccionar archivo de audio"
                        accept="audio/*,.m4a,.flac,.webm"
                        disabled={!!step}
                        onChange={(e) =>
                          setSelectedFile(e.target.files?.[0] ?? null)
                        }
                        className="sr-only"
                      />
                    </label>
                    <button
                      disabled={!!step || !selectedFile}
                      onClick={analyze}
                      className="btn-primary"
                    >
                      Encontrar acordes <ArrowRight size={17} />
                    </button>
                  </div>
                )}
                {step && (
                  <div className="mt-4">
                    <ProgressSteps currentStep={step} />
                  </div>
                )}
                {error && (
                  <div
                    role="alert"
                    className="mt-4 flex items-start gap-3 rounded-xl border border-[#e6bfb1] bg-[#fff3ed] p-4 text-sm text-[#8b442d]"
                  >
                    <TriangleAlert size={18} className="mt-0.5" />
                    <div className="min-w-0 break-words">
                      <p className="mb-1 font-bold">
                        {error.code?.startsWith("YOUTUBE_COOKIES_")
                          ? "Actualizar cookies de YouTube"
                          : "No pudimos completar el análisis"}
                      </p>
                      <p className="text-xs leading-relaxed">{error.message}</p>
                      {error.code?.startsWith("YOUTUBE_COOKIES_") && (
                        <Link
                          href="/ayuda#cookies"
                          className="mt-3 block text-xs font-bold underline"
                        >
                          Qué significa este aviso
                        </Link>
                      )}
                      {error.fallback === "upload" && (
                        <button
                          className="mt-3 text-xs font-bold underline"
                          onClick={() => {
                            setInputMode("file");
                            setError(null);
                          }}
                        >
                          Continuar subiendo un archivo
                        </button>
                      )}
                    </div>
                  </div>
                )}
                <p className="muted mt-4 flex items-center justify-center gap-1.5 text-[10px]">
                  <Check size={12} /> Sin registro{" "}
                  <span className="mx-2 opacity-40">/</span> Estimaciones para
                  practicar
                </p>
              </div>
            </div>
            <div className="hero-grid relative rounded-[32px] border border-[#dce2d8] bg-[#edf1e7] p-6 sm:p-9">
              <div className="mb-6 flex items-center justify-between">
                <span className="eyebrow">Del audio a los acordes</span>
                <span className="rounded-full border border-[#ccd8c3] px-2 py-1 text-[9px] font-bold uppercase tracking-widest">
                  Ejemplo visual
                </span>
              </div>
              <div className="rounded-2xl bg-[#284e3e] p-6 text-[#f4f6ee] shadow-[0_20px_45px_-25px_#173c2980]">
                <p className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-widest text-[#d9f58a]">
                  <Headphones size={14} /> Una canción. Muchas posibilidades.
                </p>
                <div className="my-7 flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[#c4d2c4]">Acorde actual</p>
                    <p className="mt-2 font-mono text-7xl font-medium tracking-tighter">
                      Am
                    </p>
                    <p className="mt-2 text-xs text-[#c4d2c4]">La menor</p>
                  </div>
                  <div className="rounded-xl bg-[#d9f58a] p-3 text-[#284e3e]">
                    <ChordDiagram chord="Am" />
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  {["C", "Am", "F", "G"].map((c, i) => (
                    <div
                      key={c}
                      className={`rounded-lg border p-3 ${i === 1 ? "border-[#d9f58a] bg-[#d9f58a] text-[#284e3e]" : "border-[#50705a] bg-[#355943]"}`}
                    >
                      <p className="mb-2 font-mono text-[9px] opacity-70">
                        00:0{i * 2}
                      </p>
                      <p className="font-mono text-lg">{c}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-5 flex items-center justify-between gap-4">
                <p className="muted max-w-52 text-xs leading-relaxed">
                  Una vista clara para saber qué tocar ahora y qué viene
                  después.
                </p>
                <button
                  disabled={!!step}
                  onClick={() => {
                    reset();
                    setDemo(true);
                    setResult(example);
                  }}
                  className="flex shrink-0 items-center gap-2 text-xs font-bold"
                >
                  Explorar <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </section>
          <section className="mt-10 grid gap-6 border-t border-[#dce2d8] py-10 sm:grid-cols-3">
            {[
              {
                icon: AudioLines,
                title: "Escucha los cambios",
                text: "Recorre la canción y salta al momento que quieras practicar.",
              },
              {
                icon: Guitar,
                title: "Encuentra tu posición",
                text: "Consulta diagramas, ajusta el capo y transporta los acordes.",
              },
              {
                icon: ListMusic,
                title: "Entiende la progresión",
                text: "Mira la secuencia completa o céntrate en el acorde que está sonando.",
              },
            ].map(({ icon: Icon, title, text }) => (
              <article key={title} className="flex items-start gap-4">
                <span className="rounded-xl border border-[#dce2d8] bg-white p-3">
                  <Icon size={21} />
                </span>
                <div>
                  <h2 className="mb-2 text-sm font-extrabold">{title}</h2>
                  <p className="muted text-xs leading-6">{text}</p>
                </div>
              </article>
            ))}
          </section>
        </>
      ) : (
        <div className="arrival">
          <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
            <button
              onClick={reset}
              className="muted flex items-center gap-2 text-xs font-semibold"
            >
              <ArrowLeft size={15} /> Otra canción
            </button>
            <div className="flex items-center gap-2">
              {demo && <span className="chip">Ejemplo visual · sin audio</span>}
              <button
                className="btn-soft !min-h-9 !px-3 !py-2 !text-xs"
                onClick={exportChords}
              >
                <Download size={14} /> Exportar TXT
              </button>
            </div>
          </div>
          <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="eyebrow mb-3">Tu estudio de práctica</p>
              <h1 className="max-w-3xl break-words text-3xl font-extrabold tracking-[-.04em] sm:text-4xl">
                {result.title || "Tu canción"}
              </h1>
              <p className="muted mt-2 text-sm">
                {result.artist ||
                  (demo
                    ? "Explora los diagramas y la transposición"
                    : "Análisis de acordes")}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.key && (
                <span className="chip">
                  <Music2 size={13} />{" "}
                  {result.key
                    .replace("major", "mayor")
                    .replace("minor", "menor")}
                </span>
              )}
              {duration > 0 && (
                <span className="chip">
                  <Clock3 size={13} /> {timeLabel(duration)}
                </span>
              )}
              <span className="chip">{unique} acordes</span>
            </div>
          </div>
          {result.warnings?.map((warning, i) => (
            <div
              key={`${warning.code}-${i}`}
              role="alert"
              className="notice mb-5"
            >
              <TriangleAlert size={18} />
              <div>
                <p className="font-bold">
                  {warning.code.startsWith("YOUTUBE_COOKIES_")
                    ? "Actualizar cookies de YouTube"
                    : "Información del análisis"}
                </p>
                <p>{warning.message}</p>
              </div>
            </div>
          ))}
          {result.model?.experimental && (
            <div className="notice mb-5">
              <Info size={18} />
              <p>
                Este análisis usa un modelo experimental. Revisa los acordes
                escuchando la grabación.
              </p>
            </div>
          )}
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_350px]">
            <div className="flex min-w-0 flex-col gap-6">
              {chords.length > 0 ? (
                <>
                  <ChordProgressBar
                    chords={chords}
                    totalDuration={duration}
                    currentTime={currentTime}
                    transposeBy={transposeBy}
                    onSeek={seek}
                  />
                </>
              ) : (
                <div className="panel p-10 text-center">
                  <AudioLines className="mx-auto mb-4" />
                  <h2 className="section-title">
                    No encontramos acordes claros
                  </h2>
                  <p className="muted mt-3 text-sm">
                    Prueba una grabación donde los instrumentos se escuchen
                    mejor.
                  </p>
                </div>
              )}
              <p className="muted flex items-start gap-2 text-xs leading-relaxed">
                <Info size={14} className="mt-0.5" /> La secuencia es una
                estimación del audio. Los números identifican cambios, no
                compases.
              </p>
            </div>
            <aside className="contents lg:sticky lg:top-24 lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
              {(videoId || analyzedFile) && (
                <section className="panel -order-1 overflow-hidden lg:order-none">
                  <div className="flex items-center gap-2 p-4 text-xs font-bold">
                    <Headphones size={16} /> Escucha y acompaña
                  </div>
                  {videoId ? (
                    <YoutubePlayer
                      videoId={videoId}
                      onTimeUpdate={setCurrentTime}
                      onDuration={setPlayerDuration}
                      seekRef={seekRef}
                    />
                  ) : analyzedFile ? (
                    <AudioPlayer
                      file={analyzedFile}
                      onTimeUpdate={setCurrentTime}
                      onDuration={setPlayerDuration}
                      seekRef={seekRef}
                    />
                  ) : null}
                </section>
              )}
              <TransposePanel
                capo={capo}
                shift={shift}
                onCapoChange={setCapo}
                onShiftChange={setShift}
              />
              <ChordChart
                chords={chords}
                transposeBy={transposeBy}
                totalDuration={duration}
              />
              {result.artist && result.title && (
                <section className="panel p-5">
                  <button
                    onClick={() => setLyricsOpen(!lyricsOpen)}
                    aria-expanded={lyricsOpen}
                    className="flex w-full items-center justify-between text-sm font-bold"
                  >
                    <span className="flex items-center gap-2">
                      <BookOpen size={16} /> Letra de la canción
                    </span>
                    <ArrowRight
                      size={15}
                      className={lyricsOpen ? "rotate-90" : ""}
                    />
                  </button>
                  {lyricsOpen && (
                    <div className="mt-4">
                      <LyricsDisplay
                        key={`${result.artist}-${result.title}`}
                        artist={result.artist}
                        title={result.title}
                      />
                    </div>
                  )}
                </section>
              )}
            </aside>
          </div>
        </div>
      )}
    </main>
  );
}

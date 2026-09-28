"use client";
import { memo, useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Guitar,
  Grid2X2,
  LocateFixed,
  ListMusic,
  Radio,
} from "lucide-react";
import type { ChordEvent } from "@/lib/types";
import { transposeChord } from "@/lib/transpose";
import {
  activeChordIndex,
  chordEnd,
  chordProgress,
  chordTimeLabel,
} from "@/lib/chord-timing";
import ChordDiagram from "./ChordDiagram";
import ChordSymbol, { type ChordNotation } from "./ChordSymbol";
import ChordTimeline from "./ChordTimeline";

const Diagram = memo(ChordDiagram);

export default function ChordProgressBar({
  chords,
  totalDuration,
  currentTime,
  transposeBy,
  onSeek,
}: {
  chords: ChordEvent[];
  totalDuration: number;
  currentTime: number;
  transposeBy: number;
  onSeek?: (time: number) => void;
}) {
  const [view, setView] = useState<"diagrams" | "grid">("diagrams");
  const [mode, setMode] = useState<"animated" | "summary">("animated");
  const [notation, setNotation] = useState<ChordNotation>("letters");
  const [follow, setFollow] = useState(true);
  const strip = useRef<HTMLDivElement>(null);
  const activeDiagram = useRef<HTMLButtonElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const activeMarker = useRef<HTMLButtonElement>(null);
  const active = activeChordIndex(chords, currentTime, totalDuration);
  const nextIndex = chords.findIndex((chord) => chord.time > currentTime);
  const previousIndex =
    active >= 0 ? active - 1 : nextIndex >= 0 ? nextIndex - 1 : chords.length - 1;
  const currentName =
    active >= 0 ? transposeChord(chords[active].chord, transposeBy) : null;
  const unique = Array.from(
    new Set(chords.map((chord) => transposeChord(chord.chord, transposeBy))),
  );
  const entries =
    mode === "animated"
      ? chords.map((event, index) => ({
          event,
          index,
          name: transposeChord(event.chord, transposeBy),
        }))
      : unique.map((name) => {
          const first = chords.findIndex(
            (event) => transposeChord(event.chord, transposeBy) === name,
          );
          return { event: chords[first], index: first, name };
        });

  useEffect(() => {
    if (!follow || active < 0) return;
    const pairs = [
      [track.current, activeMarker.current],
      [strip.current, activeDiagram.current],
    ] as const;
    for (const [frame, cell] of pairs) {
      if (!frame || !cell) continue;
      if (frame === strip.current && mode === "summary") continue;
      const outer = frame.getBoundingClientRect();
      const inner = cell.getBoundingClientRect();
      frame.scrollTo({
        left: Math.max(
          0,
          frame.scrollLeft +
            inner.left -
            outer.left -
            (frame.clientWidth - inner.width) * 0.38,
        ),
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
    }
  }, [active, follow, mode, view, transposeBy]);

  if (!chords.length) return null;
  function navigate(index: number) {
    if (index < 0 || index >= chords.length) return;
    setFollow(true);
    onSeek?.(chords[index].time);
  }

  return (
    <section
      className="practice-player"
      aria-label="Reproductor visual de acordes"
    >
      <div className="practice-heading">
        <div className="flex items-center gap-2.5">
          <span className="practice-live-dot" />
          <h2 className="text-sm font-extrabold">Toca con la canción</h2>
        </div>
        <span className="font-mono text-[11px] opacity-70">
          {chordTimeLabel(Math.max(0, currentTime))}
          {totalDuration > 0 ? ` / ${chordTimeLabel(totalDuration)}` : ""}
        </span>
      </div>
      <div className="practice-track-frame">
        <button
          className="practice-track-arrow"
          onClick={() => navigate(previousIndex)}
          disabled={previousIndex < 0}
          aria-label="Acorde anterior"
        >
          <ChevronLeft size={18} />
        </button>
        <div
          ref={track}
          className="practice-track"
          onWheel={() => setFollow(false)}
          onTouchMove={() => setFollow(false)}
        >
          {chords.map((event, index) => (
            <button
              key={`${event.time}-${index}`}
              ref={index === active ? activeMarker : undefined}
              aria-current={index === active ? "true" : undefined}
              aria-label={`${transposeChord(event.chord, transposeBy)}, ${chordTimeLabel(event.time, true)}`}
              className={`practice-marker ${index === active ? "is-active" : ""}`}
              onClick={() => navigate(index)}
            >
              <ChordSymbol
                chord={transposeChord(event.chord, transposeBy)}
                notation={notation}
                className="text-[23px] font-semibold"
              />
              <span className="mt-1 font-mono text-[9px] opacity-55">
                {chordTimeLabel(event.time, true)}
              </span>
              {index === active && (
                <span
                  className="practice-marker-progress"
                  style={{
                    transform: `scaleX(${chordProgress(chords, index, currentTime, totalDuration)})`,
                  }}
                />
              )}
            </button>
          ))}
        </div>
        <button
          className="practice-track-arrow"
          onClick={() => navigate(nextIndex)}
          disabled={nextIndex < 0}
          aria-label="Siguiente acorde"
        >
          <ChevronRight size={18} />
        </button>
      </div>
      <div className="practice-toolbar">
        <div
          className="practice-tabs"
          role="group"
          aria-label="Vista de práctica"
        >
          <button
            onClick={() => setView("diagrams")}
            aria-pressed={view === "diagrams"}
          >
            <Guitar size={16} /> Diagramas
          </button>
          <button
            onClick={() => setView("grid")}
            aria-pressed={view === "grid"}
          >
            <Grid2X2 size={16} /> Cuadrícula
          </button>
        </div>
        {view === "diagrams" && (
          <div
            className="practice-mode"
            role="group"
            aria-label="Modo de diagramas"
          >
            <button
              onClick={() => setMode("animated")}
              aria-pressed={mode === "animated"}
            >
              <Radio size={14} /> Animado
            </button>
            <button
              onClick={() => setMode("summary")}
              aria-pressed={mode === "summary"}
            >
              <ListMusic size={14} /> Resumen
            </button>
          </div>
        )}
      </div>
      {view === "diagrams" ? (
        <>
          <div className="practice-diagram-caption">
            <span>
              Guitarra ·{" "}
              {mode === "animated"
                ? "Acorde actual y próximos cambios"
                : `${unique.length} acordes en esta canción`}
            </span>
            <label className="flex items-center gap-2">
              <span className="sr-only">Notación de acordes</span>
              <select
                aria-label="Notación de acordes"
                value={notation}
                onChange={(event) =>
                  setNotation(event.target.value as ChordNotation)
                }
              >
                <option value="letters">C, D, E</option>
                <option value="solfege">Do, Re, Mi</option>
              </select>
            </label>
          </div>
          <div
            ref={strip}
            className={`practice-diagrams ${mode === "summary" ? "is-summary" : ""}`}
            onWheel={() => setFollow(false)}
            onTouchMove={() => setFollow(false)}
          >
            {entries.map(({ event, index, name }) => {
              const isActive =
                mode === "animated" ? index === active : currentName === name;
              const played =
                mode === "animated" &&
                currentTime >= chordEnd(chords, index, totalDuration);
              const occurrences =
                mode === "summary"
                  ? chords.filter(
                      (chord) =>
                        transposeChord(chord.chord, transposeBy) === name,
                    ).length
                  : 0;
              return (
                <button
                  key={`${mode}-${index}`}
                  ref={isActive ? activeDiagram : undefined}
                  onClick={() => navigate(index)}
                  aria-current={isActive ? "true" : undefined}
                  aria-label={`Diagrama de ${name === "N" ? "sin acorde" : name}. Ir a ${chordTimeLabel(event.time, true)}`}
                  className={`practice-diagram ${isActive ? "is-active" : ""} ${played ? "is-played" : ""}`}
                >
                  <span className="practice-diagram-meta">
                    {isActive
                      ? "Actual"
                      : mode === "summary"
                        ? `${occurrences} ${occurrences === 1 ? "vez" : "veces"}`
                        : chordTimeLabel(event.time, true)}
                  </span>
                  <div className="practice-fretboard">
                    <Diagram chord={name} />
                  </div>
                  <ChordSymbol
                    chord={name}
                    notation={notation}
                    className="practice-chord-label"
                  />
                  {isActive && mode === "animated" && (
                    <span
                      className="practice-diagram-progress"
                      style={{
                        transform: `scaleX(${chordProgress(chords, active, currentTime, totalDuration)})`,
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <ChordTimeline
          chords={chords}
          currentTime={currentTime}
          transposeBy={transposeBy}
          onSeek={onSeek}
          totalDuration={totalDuration}
          notation={notation}
          embedded
          followPlayback={follow}
          onFollowChange={setFollow}
        />
      )}
      <div className="practice-footer">
        <p>Selecciona un acorde para ir a ese momento.</p>
        <button
          onClick={() => setFollow(!follow)}
          aria-pressed={follow}
          className={follow ? "is-following" : ""}
        >
          <LocateFixed size={14} />{" "}
          {follow ? "Siguiendo la canción" : "Reanudar seguimiento"}
        </button>
      </div>
      {totalDuration > 0 && (
        <div className="practice-scrubber">
          <input
            aria-label="Posición en la canción"
            type="range"
            min={0}
            max={totalDuration}
            step={0.05}
            value={Math.max(0, Math.min(currentTime, totalDuration))}
            onChange={(event) => onSeek?.(Number(event.target.value))}
          />
        </div>
      )}
    </section>
  );
}

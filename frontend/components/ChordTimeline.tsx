"use client";
import { useEffect, useRef, useState } from "react";
import { LocateFixed } from "lucide-react";
import type { ChordEvent } from "@/lib/types";
import { transposeChord } from "@/lib/transpose";
import {
  activeChordIndex,
  chordEnd,
  chordProgress,
  chordTimeLabel,
} from "@/lib/chord-timing";
import ChordSymbol, { type ChordNotation } from "./ChordSymbol";

export default function ChordTimeline({
  chords,
  currentTime = -1,
  transposeBy = 0,
  onSeek,
  totalDuration = 0,
  notation = "letters",
  embedded = false,
  followPlayback,
  onFollowChange,
}: {
  chords: ChordEvent[];
  currentTime?: number;
  transposeBy?: number;
  onSeek?: (time: number) => void;
  totalDuration?: number;
  notation?: ChordNotation;
  embedded?: boolean;
  followPlayback?: boolean;
  onFollowChange?: (follow: boolean) => void;
}) {
  const [localFollow, setLocalFollow] = useState(true);
  const follow = followPlayback ?? localFollow;
  const setFollow = onFollowChange ?? setLocalFollow;
  const container = useRef<HTMLDivElement>(null);
  const activeCell = useRef<HTMLButtonElement>(null);
  const active = activeChordIndex(chords, currentTime, totalDuration);
  useEffect(() => {
    if (!follow || active < 0) return;
    const frame = container.current,
      cell = activeCell.current;
    if (!frame || !cell) return;
    const outer = frame.getBoundingClientRect(),
      inner = cell.getBoundingClientRect();
    if (inner.top < outer.top + 16 || inner.bottom > outer.bottom - 16) {
      frame.scrollTo({
        top: Math.max(
          0,
          frame.scrollTop + inner.top - outer.top - frame.clientHeight / 3,
        ),
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
    }
  }, [active, follow]);
  return (
    <section
      className={embedded ? "" : "panel overflow-hidden"}
      aria-label="Cuadrícula de acordes"
    >
      <div className="practice-diagram-caption">
        <span>{chords.length} cambios · tiempos de la grabación</span>
        {!embedded && (
          <button
            className="flex items-center gap-1.5"
            onClick={() => setFollow(!follow)}
            aria-pressed={follow}
          >
            <LocateFixed size={14} />
            {follow ? "Seguir" : "Reanudar"}
          </button>
        )}
      </div>
      <div
        ref={container}
        className="score-viewport"
        onWheel={() => setFollow(false)}
        onTouchMove={() => setFollow(false)}
      >
        <div className="chord-score-grid">
          {chords.map((event, index) => {
            const name = transposeChord(event.chord, transposeBy),
              isActive = index === active;
            return (
              <button
                key={`${event.time}-${index}`}
                ref={isActive ? activeCell : undefined}
                onClick={() => onSeek?.(event.time)}
                aria-current={isActive ? "true" : undefined}
                aria-label={`${name === "N" ? "Sin acorde" : name}, ${chordTimeLabel(event.time, true)}. Ir a este momento.`}
                className={`score-cell ${isActive ? "is-active" : currentTime >= chordEnd(chords, index, totalDuration) ? "is-played" : ""}`}
              >
                <span className="score-cell-number" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <ChordSymbol
                  chord={name}
                  notation={notation}
                  className="score-chord-name"
                />
                <span className="score-cell-time">
                  {chordTimeLabel(event.time, true)}
                </span>
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="score-cell-progress"
                    style={{
                      transform: `scaleX(${chordProgress(chords, index, currentTime, totalDuration)})`,
                    }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

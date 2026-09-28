import type { ChordEvent } from "./types";

export function chordEnd(chords: ChordEvent[], index: number, duration = 0) {
  const event = chords[index];
  if (!event) return 0;
  return Math.max(
    event.time,
    Math.min(
      chords[index + 1]?.time ?? Infinity,
      event.end ?? Infinity,
      duration > 0 ? duration : Infinity,
    ),
  );
}

export function activeChordIndex(
  chords: ChordEvent[],
  time: number,
  duration = 0,
) {
  if (!Number.isFinite(time) || time < 0) return -1;
  let index = -1;
  for (let i = 0; i < chords.length && chords[i].time <= time; i++) index = i;
  return index >= 0 && time < chordEnd(chords, index, duration) ? index : -1;
}

export function chordProgress(
  chords: ChordEvent[],
  index: number,
  time: number,
  duration = 0,
) {
  const start = chords[index]?.time ?? 0;
  const end = chordEnd(chords, index, duration);
  return end > start && Number.isFinite(end)
    ? Math.max(0, Math.min(1, (time - start) / (end - start)))
    : 0;
}

export function chordTimeLabel(seconds: number, precise = false) {
  // Floor before formatting: never display an impossible 0:60.0 at a boundary.
  const value = Math.max(
    0,
    precise ? Math.floor(seconds * 10) / 10 : Math.floor(seconds),
  );
  const minutes = Math.floor(value / 60);
  const rest = precise
    ? (value % 60).toFixed(1).padStart(4, "0")
    : String(value % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

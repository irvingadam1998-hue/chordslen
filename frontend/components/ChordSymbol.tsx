export type ChordNotation = "letters" | "solfege";
const names: Record<string, string> = {
  C: "Do",
  D: "Re",
  E: "Mi",
  F: "Fa",
  G: "Sol",
  A: "La",
  B: "Si",
};

export default function ChordSymbol({
  chord,
  className = "",
  notation = "letters",
}: {
  chord: string;
  className?: string;
  notation?: ChordNotation;
}) {
  const match = chord.match(/^([A-G])([#b]?)([^/]*)(?:\/([A-G][#b]?))?$/);
  if (!match)
    return <span className={className}>{chord === "N" ? "—" : chord}</span>;
  const root = notation === "solfege" ? names[match[1]] : match[1];
  const quality = match[3].replace(/^min/, "m");
  const bass =
    match[4] &&
    (notation === "solfege"
      ? names[match[4][0]] + match[4].slice(1)
      : match[4]);
  return (
    <span className={`chord-symbol ${className}`} aria-label={chord}>
      <span aria-hidden="true">{root}</span>
      {match[2] && (
        <span aria-hidden="true" className="chord-accidental">
          {match[2]}
        </span>
      )}
      {quality && (
        <span aria-hidden="true" className="chord-quality">
          {quality}
        </span>
      )}
      {bass && (
        <span aria-hidden="true" className="chord-bass">
          /{bass}
        </span>
      )}
    </span>
  );
}

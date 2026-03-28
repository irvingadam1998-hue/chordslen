export interface ChordDiagram {
    name: string
    // fingers[0..5] = cuerdas E A D G B e
    // -1 = muted, 0 = open, N = traste
    fingers: number[]
    barre?: number       // traste del cejilla (0 = sin cejilla)
    startFret?: number   // primer traste visible (default 1)
}

export const CHORD_DIAGRAMS: Record<string, ChordDiagram> = {
    'C': { name: 'C mayor', fingers: [-1, 3, 2, 0, 1, 0], startFret: 1 },
    'Cm': { name: 'Do menor', fingers: [-1, 3, 5, 5, 4, 3], barre: 3, startFret: 3 },
    'D': { name: 'Re mayor', fingers: [-1, -1, 0, 2, 3, 2], startFret: 1 },
    'Dm': { name: 'Re menor', fingers: [-1, -1, 0, 2, 3, 1], startFret: 1 },
    'E': { name: 'Mi mayor', fingers: [0, 2, 2, 1, 0, 0], startFret: 1 },
    'Em': { name: 'Mi menor', fingers: [0, 2, 2, 0, 0, 0], startFret: 1 },
    'F': { name: 'Fa mayor', fingers: [1, 3, 3, 2, 1, 1], barre: 1, startFret: 1 },
    'G': { name: 'Sol mayor', fingers: [3, 2, 0, 0, 0, 3], startFret: 1 },
    'Am': { name: 'La menor', fingers: [-1, 0, 2, 2, 1, 0], startFret: 1 },
    'A': { name: 'La mayor', fingers: [-1, 0, 2, 2, 2, 0], startFret: 1 },
    'Bm': { name: 'Si menor', fingers: [-1, 2, 4, 4, 3, 2], barre: 2, startFret: 2 },
    'B': { name: 'Si mayor', fingers: [-1, 2, 4, 4, 4, 2], barre: 2, startFret: 2 },
    'E7': { name: 'Mi 7', fingers: [0, 2, 0, 1, 0, 0], startFret: 1 },
    'A7': { name: 'La 7', fingers: [-1, 0, 2, 0, 2, 0], startFret: 1 },
    'D7': { name: 'Re 7', fingers: [-1, -1, 0, 2, 1, 2], startFret: 1 },
    'G7': { name: 'Sol 7', fingers: [3, 2, 0, 0, 0, 1], startFret: 1 },
    'F#m': { name: 'F#m', fingers: [2, 4, 4, 3, 2, 2], barre: 2, startFret: 2 },
    'C#m': { name: 'C#m', fingers: [-1, 4, 6, 6, 5, 4], barre: 4, startFret: 4 },
    'Ab': { name: 'Lab mayor', fingers: [4, 6, 6, 5, 4, 4], barre: 4, startFret: 4 },
    'Bb': { name: 'Sib mayor', fingers: [-1, 1, 3, 3, 3, 1], barre: 1, startFret: 1 },
}
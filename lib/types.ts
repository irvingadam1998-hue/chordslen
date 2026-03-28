export interface ChordEvent {
  time: number
  time_str: string
  chord: string
  measure: number
}

export interface TranscriptionNote {
  time: number
  midi: number
  note: string
  duration: number
  confidence: number
  string: number
  fret: number
}

export interface TranscriptionResult {
  notes: TranscriptionNote[]
  tab: {
    e: string
    B: string
    G: string
    D: string
    A: string
    E: string
  }
  duration: number
  bpm: number | null
}

export interface AnalysisResult {
  success: boolean
  notes_count: number
  chords_timeline: ChordEvent[]
  title?: string
  artist?: string
  error?: string
}

export interface ChordEvent {
  time: number
  time_str: string
  chord: string
  measure: number
}

export interface AnalysisResult {
  success: boolean
  notes_count: number
  chords_timeline: ChordEvent[]
  title?: string
  artist?: string
  error?: string
}

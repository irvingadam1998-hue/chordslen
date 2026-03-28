# Feature: Selector de rango para transcripción de solos

## Contexto
App web Next.js que analiza acordes de canciones desde YouTube.
Ya existe: análisis de acordes, timeline sincronizado, reproductor de YouTube.
Stack: Next.js 14 (App Router), TypeScript, Tailwind CSS, Python backend.

## Feature a implementar
El usuario selecciona manualmente un fragmento del video (ej: el solo de guitarra)
y el sistema transcribe las notas individuales y genera la tablatura.

## Flujo completo

1. Usuario pega URL → video carga con YoutubePlayer existente
2. Aparece un **selector de rango draggable** sobre el timeline
3. Usuario arrastra para marcar inicio y fin del fragmento (máx 60s)
4. Click en "Transcribir fragmento"
5. Backend descarga solo ese fragmento de audio
6. Corre **Basic Pitch** (Spotify) para detectar notas MIDI
7. Mapea las notas MIDI a posiciones en el mástil de guitarra
8. Devuelve tablatura en formato ASCII + datos estructurados
9. Se renderiza la tablatura sincronizada con el video

---

## Componentes a crear

### Frontend

#### `RangeSelector.tsx`
- Barra horizontal draggable sobre el timeline existente
- Dos handles (inicio y fin) + región seleccionada arrastrable
- Muestra tiempo de inicio, fin y duración del fragmento seleccionado
- Límite máximo de 60 segundos seleccionables
- Al soltar emite `onConfirm(start: number, end: number)`
- Estilo consistente con el resto de la app (dark, Tailwind)

#### `TranscriptionPanel.tsx`
- Recibe el resultado de la transcripción
- Muestra la tablatura ASCII renderizada en fuente monospace
- Muestra las notas detectadas como pills coloreados por cuerda
- Botón para copiar la tablatura al portapapeles
- Estado de loading con skeleton mientras procesa

#### `TabDisplay.tsx`
- Renderiza la tablatura sincronizada con `currentTime`
- Resalta la nota/posición activa mientras el video avanza
- 6 cuerdas: e B G D A E
- Cada nota muestra el traste como número

---

### Backend (Python / API Route Next.js)

#### `POST /api/transcribe`
```typescript
// Request
{
  url: string        // URL de YouTube
  start: number      // segundos
  end: number        // segundos (máx start + 60)
}

// Response
{
  notes: Array<{
    time: number        // segundos desde el inicio del fragmento
    midi: number        // nota MIDI (0-127)
    note: string        // "E4", "G#3", etc.
    duration: number    // segundos
    confidence: number  // 0-1
    string: number      // cuerda de guitarra (1-6)
    fret: number        // traste
  }>
  tab: {
    e: string   // "---12-15-12---"
    B: string
    G: string
    D: string
    A: string
    E: string
  }
  duration: number    // duración total del fragmento
  bpm: number | null  // tempo detectado si es posible
}
```

#### Script Python `transcribe.py`
```python
# Pasos:
# 1. yt-dlp → descarga solo el fragmento (--download-sections)
# 2. basic-pitch → genera notas MIDI
# 3. midi_to_tab() → mapea notas a cuerdas/trastes
# 4. Devuelve JSON
```

---

## Lógica de mapeo MIDI → tablatura
```
Afinación estándar (MIDI):
  e (1ra) → Mi4  = 64
  B (2da) → Si3  = 59
  G (3ra) → Sol3 = 55
  D (4ta) → Re3  = 50
  A (5ta) → La2  = 45
  E (6ta) → Mi2  = 40

Algoritmo:
  Para cada nota MIDI detectada:
    1. Encontrar todas las posiciones posibles (cuerda + traste)
    2. Preferir trastes bajos (< 12) y cuerdas medias (2da, 3ra, 4ta)
    3. Considerar la nota anterior para minimizar saltos de posición
    4. Asignar a la cuerda óptima
```

---

## Restricciones y edge cases

- Máximo 60 segundos por transcripción
- Si el fragmento tiene mucho ruido o es rítmico (no melódico), avisar al usuario
- Basic Pitch puede devolver muchas notas falsas con baja confidence → filtrar < 0.5
- Si dos notas se superponen en la misma cuerda, resolver el conflicto
- Mostrar advertencia si el fragmento no parece contener melodía solista

---

## Archivos existentes relevantes

- `components/YoutubePlayer.tsx` — player con `onTimeUpdate` y `seekRef`
- `components/ChordTimeline.tsx` — timeline con bloques de acordes por fila
- `components/ChordProgressBar.tsx` — barra de progreso con diagramas
- `lib/types.ts` — tipos existentes (`ChordEvent`, `AnalysisResult`)
- `app/api/analyze/route.ts` — endpoint existente de análisis de acordes
- `app/page.tsx` — página principal con toda la lógica de estado

---

## Integración en `page.tsx`
```tsx
// Nuevo estado
const [soloRange, setSoloRange] = useState<{ start: number; end: number } | null>(null)
const [transcription, setTranscription] = useState<TranscriptionResult | null>(null)
const [transcribing, setTranscribing] = useState(false)

// Nueva sección entre 02 y 03
<section>
  <SectionLabel number="02b" title="Transcribir fragmento" />
  <RangeSelector
    totalDuration={totalDuration}
    currentTime={currentTime}
    onConfirm={setSoloRange}
  />
  {soloRange && (
    <button onClick={handleTranscribe}>
      Transcribir {soloRange.end - soloRange.start}s
    </button>
  )}
  {transcription && (
    <TranscriptionPanel
      data={transcription}
      currentTime={currentTime}
    />
  )}
</section>
```

---

## Dependencias a instalar
```bash
# Frontend
# (ninguna nueva, usa componentes existentes)

# Backend Python
pip install basic-pitch yt-dlp numpy

# O como script standalone
python transcribe.py --url "..." --start 45 --end 90
```

---

## Notas de diseño UI

- El selector de rango debe usar los mismos colores del acorde activo en ese momento
- La región seleccionada se muestra semitransparente sobre el timeline existente
- El loading state muestra las 6 cuerdas vacías animadas (skeleton)
- La tablatura usa `font-mono` con los mismos colores por nota que el timeline
- En mobile: los handles del selector son más grandes (44px touch target)
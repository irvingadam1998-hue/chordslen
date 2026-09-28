import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import vm from 'node:vm'

// Exercise actual TS components without a browser or an extra test dependency.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const packages = createRequire(import.meta.url)
const ts = packages('typescript')
const React = packages('react')
const { renderToStaticMarkup } = packages('react-dom/server')
const modules = new Map()
function load(file) {
  if (modules.has(file)) return modules.get(file)
  const exports = {}
  modules.set(file, exports)
  const code = ts.transpileModule(readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText
  vm.runInNewContext(code, {
    exports, console,
    require: (name) => {
      if (name.startsWith('@/') || name.startsWith('.')) {
        const base = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name)
        const target = [base, `${base}.ts`, `${base}.tsx`].find(existsSync)
        if (!target) throw new Error(`Missing ${name}`)
        return load(target)
      }
      return packages(name)
    },
  }, { filename: file })
  return exports
}
const timing = load(path.join(root, 'lib/chord-timing.ts'))
const Player = load(path.join(root, 'components/ChordProgressBar.tsx')).default
const Symbol = load(path.join(root, 'components/ChordSymbol.tsx')).default
const chords = [
  { time: 1, end: 1.12, chord: 'C', time_str: '0:01', measure: 1 },
  { time: 1.12, end: 2, chord: 'Am7', time_str: '0:01', measure: 2 },
  { time: 3, end: 5, chord: 'F', time_str: '0:03', measure: 3 },
]

test('preserves a real short chord and changes precisely at its boundary', () => {
  assert.equal(timing.activeChordIndex(chords, 1.1, 5), 0)
  assert.equal(timing.activeChordIndex(chords, 1.12, 5), 1)
  assert.equal(timing.activeChordIndex(chords, .9, 5), -1)
})
test('does not invent a sounding chord in a gap or after the recording', () => {
  assert.equal(timing.activeChordIndex(chords, 2.4, 5), -1)
  assert.equal(timing.activeChordIndex(chords, 5, 5), -1)
  assert.equal(timing.activeChordIndex(chords, NaN, 5), -1)
})
test('supports older API responses without explicit event ends', () => {
  const legacy = chords.map(({ time, chord, time_str, measure }) => ({ time, chord, time_str, measure }))
  assert.equal(timing.chordEnd(legacy, 1, 5), 3)
  assert.equal(timing.chordEnd(legacy, 2, 5), 5)
  assert.equal(timing.chordProgress(legacy, 2, 9, 5), 1)
})
test('timestamps distinguish subsecond changes without displaying 0:60.0', () => {
  assert.equal(timing.chordTimeLabel(59.999, true), '0:59.9')
  assert.equal(timing.chordTimeLabel(60, true), '1:00.0')
  assert.notEqual(timing.chordTimeLabel(1, true), timing.chordTimeLabel(1.12, true))
})
test('diagram and navigation strip agree on the active chord', () => {
  const markup = renderToStaticMarkup(React.createElement(Player, { chords, totalDuration: 5, currentTime: 1.2, transposeBy: 0 }))
  assert.equal((markup.match(/aria-current="true"/g) || []).length, 2)
  assert.match(markup, /Diagrama de Am7/)
  assert.match(markup, /Animado/)
  assert.match(markup, /Resumen/)
})
test('finished playback has no active diagram or active navigation marker', () => {
  const markup = renderToStaticMarkup(React.createElement(Player, { chords, totalDuration: 5, currentTime: 5, transposeBy: 0 }))
  assert.doesNotMatch(markup, /aria-current="true"/)
})
test('previous navigation remains available during an unannotated gap', () => {
  const markup = renderToStaticMarkup(React.createElement(Player, { chords, totalDuration: 5, currentTime: 2.4, transposeBy: 0 }))
  const previous = markup.match(/<button[^>]*aria-label="Acorde anterior"[^>]*>/)?.[0]
  assert.ok(previous)
  assert.doesNotMatch(previous, /disabled/)
})
test('solfege preserves chord quality, accidentals and bass', () => {
  const markup = renderToStaticMarkup(React.createElement(Symbol, { chord: 'F#m7/A', notation: 'solfege' }))
  assert.match(markup, />Fa</)
  assert.match(markup, />#</)
  assert.match(markup, />m7</)
  assert.match(markup, />\/La</)
})

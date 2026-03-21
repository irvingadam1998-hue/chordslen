'use client'

import { useState } from 'react'

type ChordType = 'Mayor' | 'Menor' | 'Con séptima' | 'Menor séptima' | 'Mayor séptima' | 'Disminuido' | 'Aumentado' | 'Suspendido'

interface ChordEntry {
  name: string
  symbol: string
  intervals: string
  notes: string
  description: string
  type: ChordType
  hue: number
}

const chords: ChordEntry[] = [
  // Major
  { name: 'Do Mayor', symbol: 'C', intervals: '1 - 3 - 5', notes: 'Do - Mi - Sol', description: 'Acorde fundamental de la tonalidad de Do. Brillante y estable, es uno de los más usados en todos los géneros.', type: 'Mayor', hue: 210 },
  { name: 'Re Mayor', symbol: 'D', intervals: '1 - 3 - 5', notes: 'Re - Fa# - La', description: 'Con carácter luminoso y enérgico. Muy presente en rock y pop. Requiere Fa sostenido.', type: 'Mayor', hue: 40 },
  { name: 'Mi Mayor', symbol: 'E', intervals: '1 - 3 - 5', notes: 'Mi - Sol# - Si', description: 'Brillante y vibrante. Muy natural en guitarra eléctrica. Acorde abierto muy utilizado en rock.', type: 'Mayor', hue: 80 },
  { name: 'Fa Mayor', symbol: 'F', intervals: '1 - 3 - 5', notes: 'Fa - La - Do', description: 'Requiere cejilla en guitarra, lo que lo hace un desafío para principiantes. Suave y cálido.', type: 'Mayor', hue: 280 },
  { name: 'Sol Mayor', symbol: 'G', intervals: '1 - 3 - 5', notes: 'Sol - Si - Re', description: 'Uno de los acordes más usados en folk y pop. Abierto, resonante y fácil de tocar en guitarra.', type: 'Mayor', hue: 160 },
  { name: 'La Mayor', symbol: 'A', intervals: '1 - 3 - 5', notes: 'La - Do# - Mi', description: 'Amplio y enérgico. Muy usado en rock y blues. En guitarra se toca con los dedos apilados en el traste 2.', type: 'Mayor', hue: 20 },
  { name: 'Si Mayor', symbol: 'B', intervals: '1 - 3 - 5', notes: 'Si - Re# - Fa#', description: 'Brillante pero requiere cejilla. Aparece frecuentemente como acorde de dominante en canciones en Mi.', type: 'Mayor', hue: 320 },
  // Minor
  { name: 'Do Menor', symbol: 'Cm', intervals: '1 - 3b - 5', notes: 'Do - Mib - Sol', description: 'Oscuro y dramático. Muy utilizado en música clásica y baladas. Requiere cejilla en guitarra.', type: 'Menor', hue: 200 },
  { name: 'Re Menor', symbol: 'Dm', intervals: '1 - 3b - 5', notes: 'Re - Fa - La', description: 'Melancólico y expresivo. Fácil de tocar en guitarra sin cejilla. Muy común en flamenco y pop.', type: 'Menor', hue: 30 },
  { name: 'Mi Menor', symbol: 'Em', intervals: '1 - 3b - 5', notes: 'Mi - Sol - Si', description: 'El acorde menor más fácil en guitarra. Solo dos dedos. Oscuro y poderoso, omnipresente en rock.', type: 'Menor', hue: 70 },
  { name: 'Fa Menor', symbol: 'Fm', intervals: '1 - 3b - 5', notes: 'Fa - Lab - Do', description: 'Tenso y emotivo. Común en baladas y música clásica. Requiere cejilla al traste 1 en guitarra.', type: 'Menor', hue: 270 },
  { name: 'Sol Menor', symbol: 'Gm', intervals: '1 - 3b - 5', notes: 'Sol - Sib - Re', description: 'Sombrío y melancólico. Aparece mucho en música latina y flamenca. Cejilla en traste 3.', type: 'Menor', hue: 150 },
  { name: 'La Menor', symbol: 'Am', intervals: '1 - 3b - 5', notes: 'La - Do - Mi', description: 'El acorde menor por excelencia. Fácil, oscuro y melancólico. Imprescindible en cualquier estilo.', type: 'Menor', hue: 10 },
  { name: 'Si Menor', symbol: 'Bm', intervals: '1 - 3b - 5', notes: 'Si - Re - Fa#', description: 'Sombrío y tenso. Requiere cejilla al traste 2. Muy usado en rock y baladas en tonalidad de Re.', type: 'Menor', hue: 310 },
  // Seventh
  { name: 'Do con séptima', symbol: 'C7', intervals: '1 - 3 - 5 - 7b', notes: 'Do - Mi - Sol - Sib', description: 'Séptima dominante de Do. Crea tensión que resuelve naturalmente hacia Fa. Muy usado en blues.', type: 'Con séptima', hue: 210 },
  { name: 'Sol con séptima', symbol: 'G7', intervals: '1 - 3 - 5 - 7b', notes: 'Sol - Si - Re - Fa', description: 'El acorde de dominante más común. Resuelve hacia Do. Imprescindible en rock, pop y blues.', type: 'Con séptima', hue: 160 },
  { name: 'Re con séptima', symbol: 'D7', intervals: '1 - 3 - 5 - 7b', notes: 'Re - Fa# - La - Do', description: 'Acorde de dominante en Sol. Crea gran tensión armónica. Muy usado en blues y música country.', type: 'Con séptima', hue: 40 },
  { name: 'La con séptima', symbol: 'A7', intervals: '1 - 3 - 5 - 7b', notes: 'La - Do# - Mi - Sol', description: 'Dominante en Re. Suena muy blues y country. Fácil de tocar y con mucho carácter.', type: 'Con séptima', hue: 20 },
  // Minor seventh
  { name: 'La Menor séptima', symbol: 'Am7', intervals: '1 - 3b - 5 - 7b', notes: 'La - Do - Mi - Sol', description: 'Suave y jazzístico. Más cálido que Am. Muy usado en pop moderno, R&B y bossa nova.', type: 'Menor séptima', hue: 10 },
  { name: 'Re Menor séptima', symbol: 'Dm7', intervals: '1 - 3b - 5 - 7b', notes: 'Re - Fa - La - Do', description: 'Melancólico y rico. Clásico del jazz y la bossa nova. Agrega profundidad a progresiones en Do.', type: 'Menor séptima', hue: 30 },
  { name: 'Mi Menor séptima', symbol: 'Em7', intervals: '1 - 3b - 5 - 7b', notes: 'Mi - Sol - Si - Re', description: 'Suave y flotante. Muy popular en pop, indie y soul. Fácil de tocar, añade sofisticación.', type: 'Menor séptima', hue: 70 },
  // Major seventh
  { name: 'Do Mayor séptima', symbol: 'Cmaj7', intervals: '1 - 3 - 5 - 7', notes: 'Do - Mi - Sol - Si', description: 'Soñador y romántico. Característico del jazz y el pop sofisticado. Suena moderno y refinado.', type: 'Mayor séptima', hue: 210 },
  { name: 'Fa Mayor séptima', symbol: 'Fmaj7', intervals: '1 - 3 - 5 - 7', notes: 'Fa - La - Do - Mi', description: 'Luminoso y etéreo. Muy usado en bossa nova y jazz. Crea una sensación de tranquilidad y apertura.', type: 'Mayor séptima', hue: 280 },
  // Diminished
  { name: 'Si Disminuido', symbol: 'Bdim', intervals: '1 - 3b - 5b', notes: 'Si - Re - Fa', description: 'Tenso e inestable. Busca resolución. Aparece como acorde de paso en música clásica y jazz.', type: 'Disminuido', hue: 340 },
  { name: 'Do Disminuido', symbol: 'Cdim', intervals: '1 - 3b - 5b', notes: 'Do - Mib - Solb', description: 'Oscuro y dramático. Crea una tensión extrema que pide resolución. Común en música dramática.', type: 'Disminuido', hue: 350 },
  // Augmented
  { name: 'Do Aumentado', symbol: 'Caug', intervals: '1 - 3 - 5#', notes: 'Do - Mi - Sol#', description: 'Ambiguo y tenso. Ni estable ni inestable, suena flotante. Muy usado en jazz y música impresionista.', type: 'Aumentado', hue: 180 },
  // Suspended
  { name: 'Do Suspendido 2', symbol: 'Csus2', intervals: '1 - 2 - 5', notes: 'Do - Re - Sol', description: 'Abierto y etéreo. Sin tercera, no es mayor ni menor. Da sensación de suspenso y espacio.', type: 'Suspendido', hue: 230 },
  { name: 'Do Suspendido 4', symbol: 'Csus4', intervals: '1 - 4 - 5', notes: 'Do - Fa - Sol', description: 'Tenso y suspendido. Clásico en rock (The Who, Pink Floyd). Resuelve naturalmente hacia Do Mayor.', type: 'Suspendido', hue: 250 },
]

const filterTypes = ['Todos', 'Mayor', 'Menor', 'Con séptima', 'Menor séptima', 'Mayor séptima', 'Disminuido', 'Aumentado', 'Suspendido'] as const
type FilterType = typeof filterTypes[number]

export default function GlosarioPage() {
  const [filter, setFilter] = useState<FilterType>('Todos')

  const filtered = filter === 'Todos' ? chords : chords.filter((c) => c.type === filter)

  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="border-b border-white/5 py-16 px-6 text-center">
        <div className="max-w-2xl mx-auto flex flex-col items-center gap-4">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">REFERENCIA</p>
          <h1 className="text-4xl font-black tracking-tighter">Glosario de Acordes</h1>
          <p className="text-white/40 text-sm leading-relaxed max-w-xl">
            Referencia completa de acordes musicales: nombre, símbolo, intervalos, notas y descripción.
            Usá los filtros para encontrar el tipo de acorde que necesitás.
          </p>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-6 py-12 flex flex-col gap-10">
        {/* Filter buttons */}
        <div className="flex flex-wrap gap-2">
          {filterTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`text-xs font-medium px-4 py-1.5 rounded-full border transition-colors ${
                filter === type
                  ? 'bg-yellow-400 text-gray-950 border-yellow-400'
                  : 'border-white/10 text-white/50 hover:border-white/30 hover:text-white/80'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Count */}
        <p className="text-white/25 text-xs font-mono">
          {filtered.length} acorde{filtered.length !== 1 ? 's' : ''} mostrado{filtered.length !== 1 ? 's' : ''}
        </p>

        {/* Chord grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((chord) => (
            <div
              key={chord.symbol}
              className="bg-white/3 border border-white/8 rounded-2xl p-5 flex flex-col gap-3 hover:border-white/20 transition-colors"
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[10px] text-white/30 font-mono tracking-wider uppercase">
                    {chord.type}
                  </p>
                  <p className="text-white/70 text-sm font-medium mt-0.5">{chord.name}</p>
                </div>
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ backgroundColor: `hsl(${chord.hue}, 70%, 20%)`, border: `1px solid hsl(${chord.hue}, 70%, 30%)` }}
                >
                  <span
                    className="font-black text-sm font-mono"
                    style={{ color: `hsl(${chord.hue}, 80%, 65%)` }}
                  >
                    {chord.symbol}
                  </span>
                </div>
              </div>

              {/* Intervals & notes */}
              <div className="flex flex-col gap-1.5 bg-white/4 rounded-xl p-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-white/25 uppercase tracking-wider">Intervalos</span>
                  <span className="text-xs font-mono text-white/60">{chord.intervals}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-white/25 uppercase tracking-wider">Notas</span>
                  <span className="text-xs font-mono text-white/60">{chord.notes}</span>
                </div>
              </div>

              {/* Description */}
              <p className="text-white/35 text-xs leading-relaxed">{chord.description}</p>
            </div>
          ))}
        </div>

        {/* Theory section */}
        <div className="border-t border-white/5 pt-12 flex flex-col gap-8">
          <div className="text-center flex flex-col gap-3">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">TEORÍA</p>
            <h2 className="text-2xl font-bold">¿Qué es un acorde?</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto w-full">
            {[
              {
                title: 'Definición',
                text: 'Un acorde es la combinación de tres o más notas tocadas simultáneamente. La base de cualquier acorde es la tríada: la nota raíz (1), la tercera (3) y la quinta (5). Según la distancia entre estas notas —medida en semitonos— el acorde puede ser mayor, menor, disminuido o aumentado.',
              },
              {
                title: 'Intervalos',
                text: 'Los intervalos son las distancias entre notas. Un semitono es la distancia más pequeña (entre teclas adyacentes en el piano). Una tercera mayor son 4 semitonos, una tercera menor son 3 semitonos. Estas pequeñas diferencias son las que determinan si un acorde suena alegre o triste.',
              },
              {
                title: 'Acordes mayores vs menores',
                text: 'La diferencia entre un acorde mayor y uno menor es un solo semitono: la tercera. En un acorde mayor, la tercera está a 4 semitonos de la raíz. En uno menor, está a 3 semitonos. Por eso Do Mayor tiene Mi natural, pero Do Menor tiene Mib (un semitono más bajo).',
              },
              {
                title: 'Acordes extendidos',
                text: 'Los acordes de séptima, novena y otros acordes extendidos añaden más notas a la tríada básica. La séptima dominante (7) agrega una séptima menor, creando tensión que resuelve. La séptima mayor (maj7) agrega una séptima natural, creando un sonido más suave y jazzístico.',
              },
            ].map(({ title, text }) => (
              <div key={title} className="bg-white/3 border border-white/8 rounded-2xl p-6 flex flex-col gap-3">
                <h3 className="font-bold text-white text-sm">{title}</h3>
                <p className="text-white/40 text-xs leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Blog — ChordLens',
  description:
    'Artículos sobre acordes, teoría musical, guitarra y tecnología de análisis de audio.',
}

const categories = ['Todos', 'Tecnología', 'Teoría musical', 'Guitarra', 'Principiantes']

const featuredPost = {
  slug: 'como-detectamos-acordes',
  title: 'Cómo detectamos acordes con inteligencia artificial',
  date: '15 de marzo, 2025',
  category: 'Tecnología',
  description:
    'El análisis armónico de audio es uno de los problemas más desafiantes en el procesamiento de señales musicales. En este artículo explicamos en detalle el pipeline técnico detrás de ChordLens: desde la descarga del audio hasta la clasificación del acorde final, pasando por la transformada de Fourier y los modelos de detección de notas.',
}

const posts = [
  {
    slug: 'los-10-acordes-mas-usados-en-pop',
    title: 'Los 10 acordes más usados en la música pop',
    category: 'Teoría musical',
    date: '10 mar 2025',
    description: 'Do, Sol, La menor y Fa. Con solo cuatro acordes podés tocar miles de canciones. Descubrí los acordes más frecuentes en el pop y entendé por qué suenan tan bien juntos.',
  },
  {
    slug: 'que-es-el-capo',
    title: 'Qué es el capo y cómo usarlo para tocar cualquier canción',
    category: 'Guitarra',
    date: '8 mar 2025',
    description: 'El capo es el accesorio más útil para guitarristas principiantes. Te permite tocar canciones en tonalidades difíciles usando acordes sencillos. Guía completa con ejemplos prácticos.',
  },
  {
    slug: 'progresion-i-iv-v',
    title: 'Progresión I-IV-V: la fórmula secreta del rock',
    category: 'Teoría musical',
    date: '5 mar 2025',
    description: 'Detrás de miles de canciones de rock, blues y country hay una sola progresión de acordes. Aprendé a identificarla, usarla y variarla para componer tu propia música.',
  },
  {
    slug: 'como-leer-diagrama-de-acordes',
    title: 'Cómo leer un diagrama de acordes',
    category: 'Principiantes',
    date: '2 mar 2025',
    description: 'Los diagramas de acordes son el lenguaje universal de la guitarra. Aprendé a leerlos en menos de 5 minutos, desde las líneas y puntos hasta los indicadores de dedo y cejilla.',
  },
  {
    slug: 'circle-of-fifths',
    title: 'Circle of Fifths: tu mejor aliado para componer',
    category: 'Teoría musical',
    date: '28 feb 2025',
    description: 'El círculo de quintas es la herramienta más poderosa de la teoría musical. Te dice qué acordes suenan bien juntos, cómo modular entre tonalidades y cómo construir progresiones que funcionan.',
  },
  {
    slug: 'acorde-mayor-vs-menor',
    title: 'Diferencia entre acorde mayor y menor',
    category: 'Principiantes',
    date: '25 feb 2025',
    description: '¿Por qué los acordes mayores suenan alegres y los menores tristes? La respuesta está en los intervalos. Una explicación clara con ejemplos en guitarra y piano para entender la diferencia de una vez.',
  },
]

export default function BlogPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="border-b border-white/5 py-16 px-6 text-center">
        <div className="max-w-2xl mx-auto flex flex-col items-center gap-4">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">BLOG</p>
          <h1 className="text-4xl font-black tracking-tighter">Artículos sobre música</h1>
          <p className="text-white/40 text-sm">
            Teoría musical, técnica de guitarra y tecnología de análisis de audio.
          </p>
        </div>
      </section>

      <div className="max-w-5xl mx-auto px-6 py-12 flex flex-col gap-12">
        {/* Category filter */}
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`text-xs font-medium px-4 py-1.5 rounded-full border transition-colors ${
                cat === 'Todos'
                  ? 'bg-yellow-400 text-gray-950 border-yellow-400'
                  : 'border-white/10 text-white/50 hover:border-white/30 hover:text-white/80'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Featured post */}
        <Link
          href={`/blog/${featuredPost.slug}`}
          className="block bg-white/3 border border-white/8 rounded-2xl p-8 hover:border-yellow-400/25 transition-colors group"
        >
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium bg-yellow-400/15 text-yellow-400 px-3 py-1 rounded-full border border-yellow-400/20">
                {featuredPost.category}
              </span>
              <span className="text-xs text-white/30">{featuredPost.date}</span>
              <span className="text-xs text-white/20 ml-auto">Artículo destacado</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white group-hover:text-yellow-400 transition-colors leading-tight">
              {featuredPost.title}
            </h2>
            <p className="text-white/50 text-sm leading-relaxed max-w-3xl">
              {featuredPost.description}
            </p>
            <span className="text-yellow-400 text-sm font-medium mt-2 group-hover:translate-x-1 inline-block transition-transform">
              Leer más →
            </span>
          </div>
        </Link>

        {/* Post grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="flex flex-col gap-3 bg-white/3 border border-white/8 rounded-2xl p-5 hover:border-white/20 transition-colors group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-white/40 bg-white/5 px-2.5 py-1 rounded-full">
                  {post.category}
                </span>
                <span className="text-[10px] text-white/25 font-mono">{post.date}</span>
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-yellow-400 transition-colors leading-snug">
                {post.title}
              </h3>
              <p className="text-white/35 text-xs leading-relaxed flex-1">{post.description}</p>
              <span className="text-yellow-400/70 text-xs font-medium group-hover:text-yellow-400 transition-colors">
                Leer más →
              </span>
            </Link>
          ))}
        </div>

        {/* Newsletter CTA */}
        <div className="border-t border-white/5 pt-12">
          <div className="bg-white/3 border border-white/8 rounded-2xl p-8 text-center flex flex-col items-center gap-5">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">NEWSLETTER</p>
            <h2 className="text-2xl font-bold">Nuevos artículos cada semana</h2>
            <p className="text-white/40 text-sm max-w-md leading-relaxed">
              Suscribite y recibí artículos sobre teoría musical, técnicas de guitarra y novedades de
              ChordLens directamente en tu casilla.
            </p>
            <div className="flex w-full max-w-sm gap-2">
              <input
                type="email"
                placeholder="tu@email.com"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-yellow-400/40 transition-colors"
              />
              <button className="bg-yellow-400 text-gray-950 text-xs font-bold px-4 py-2.5 rounded-lg hover:bg-yellow-300 transition-colors whitespace-nowrap">
                SUSCRIBIRSE
              </button>
            </div>
            <p className="text-white/20 text-xs">Sin spam. Podés darte de baja cuando quieras.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

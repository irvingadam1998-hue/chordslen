import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Nosotros — ChordLens',
  description:
    'Conocé al equipo detrás de ChordLens, nuestra misión y los valores que guían el desarrollo de la plataforma.',
}

const values = [
  {
    icon: '♿',
    title: 'Accesibilidad',
    description:
      'Creemos que aprender música no debería ser un privilegio. ChordLens es gratuito, sin registro, y funciona desde cualquier dispositivo con un navegador. Nuestro objetivo es que cualquier persona que quiera aprender una canción pueda hacerlo sin barreras.',
  },
  {
    icon: '🎯',
    title: 'Precisión',
    description:
      'La detección de acordes basada en análisis de audio es técnicamente compleja. Trabajamos constantemente para mejorar la exactitud de nuestros algoritmos, combinando análisis de frecuencias con modelos de detección de notas para acercarnos lo más posible a los acordes reales.',
  },
  {
    icon: '🤝',
    title: 'Comunidad',
    description:
      'ChordLens nació de la comunidad musical y queremos devolverle el favor. Escuchamos el feedback de los usuarios, priorizamos las funcionalidades más pedidas y compartimos nuestro aprendizaje técnico en el blog. Juntos aprendemos mejor.',
  },
]

const team = [
  {
    name: 'Martina Reyes',
    role: 'Fundadora & Desarrolladora Full-Stack',
    description:
      'Guitarrista desde los 10 años y desarrolladora con más de 8 años de experiencia. Creó ChordLens porque no encontraba una herramienta que detectara acordes reales del audio, en lugar de transcripciones manuales. Lidera el desarrollo del backend y los algoritmos de análisis musical.',
    initials: 'MR',
  },
  {
    name: 'Diego Albornoz',
    role: 'Diseñador de Producto & Frontend',
    description:
      'Diseñador UX con foco en interfaces musicales. Toca el bajo en una banda de rock independiente y entiende de primera mano la frustración de aprender canciones de oído. En ChordLens es responsable de la experiencia visual y la accesibilidad de la interfaz.',
    initials: 'DA',
  },
  {
    name: 'Valentina Cruz',
    role: 'Investigadora en Audio & Machine Learning',
    description:
      'Doctora en procesamiento de señales de audio por la UBA. Trabaja en la integración de modelos de detección de notas y en la mejora continua de los algoritmos de reconocimiento armónico. Apasionada del jazz y la teoría musical.',
    initials: 'VC',
  },
]

const techStack = [
  { name: 'Next.js 15', desc: 'Framework React para el frontend y la API.' },
  { name: 'TypeScript', desc: 'Tipado estático para un código más robusto.' },
  { name: 'Tailwind CSS', desc: 'Estilos utilitarios para una UI consistente.' },
  { name: 'yt-dlp', desc: 'Descarga y extracción de audio desde YouTube.' },
  { name: 'librosa', desc: 'Análisis de audio y extracción de características.' },
  { name: 'Basic Pitch (Spotify)', desc: 'Detección de notas con modelos de ML.' },
  { name: 'Python', desc: 'Backend de procesamiento de audio.' },
  { name: 'Docker', desc: 'Contenedorización para despliegue consistente.' },
]

export default function NosotrosPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="border-b border-white/5 py-20 px-6">
        <div className="max-w-4xl mx-auto text-center flex flex-col items-center gap-6">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">SOBRE NOSOTROS</p>
          <h1 className="text-4xl sm:text-6xl font-black tracking-tighter leading-none">
            Somos músicos<br />
            <span className="text-yellow-400">y desarrolladores.</span>
          </h1>
          <p className="text-white/50 text-lg max-w-2xl leading-relaxed">
            ChordLens nació de una frustración simple: las herramientas existentes para aprender
            acordes dependían de transcripciones manuales y estaban desactualizadas. Queríamos
            algo que analizara el audio real y te diera los acordes tal como suenan en la grabación.
          </p>
        </div>
      </section>

      {/* Story */}
      <section className="py-20 px-6 border-b border-white/5">
        <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-12 items-center">
          <div className="flex flex-col gap-5">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">NUESTRA HISTORIA</p>
            <h2 className="text-3xl font-bold">De la frustración al producto</h2>
            <div className="flex flex-col gap-4 text-white/50 text-sm leading-relaxed">
              <p>
                Todo empezó en 2023 cuando Martina intentaba aprender una canción de oído y ninguna
                aplicación le daba los acordes correctos. Las plataformas existentes mostraban
                transcripciones subidas por usuarios, muchas veces incorrectas, y no había forma de
                verificarlas contra el audio original.
              </p>
              <p>
                Junto a Diego y Valentina, decidieron construir algo diferente: una herramienta que
                tomara el audio directamente de YouTube, lo analizara con algoritmos de procesamiento
                de señales, y devolviera los acordes reales, sincronizados con el video.
              </p>
              <p>
                Después de varios meses de desarrollo y pruebas con cientos de canciones de distintos
                géneros, lanzaron la primera versión de ChordLens. La respuesta de la comunidad fue
                inmediata: en las primeras dos semanas, más de 5.000 canciones fueron analizadas.
              </p>
            </div>
          </div>
          <div className="bg-white/3 border border-white/8 rounded-2xl p-8 flex flex-col gap-6">
            {[
              { number: '5.000+', label: 'Canciones analizadas en el primer mes' },
              { number: '120+', label: 'Países con usuarios activos' },
              { number: '98%', label: 'Precisión en acordes básicos' },
              { number: '2023', label: 'Año de fundación' },
            ].map(({ number, label }) => (
              <div key={label} className="flex flex-col gap-1">
                <span className="text-3xl font-black text-yellow-400 font-mono">{number}</span>
                <span className="text-white/40 text-sm">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="py-20 px-6 border-b border-white/5 bg-yellow-400/3">
        <div className="max-w-4xl mx-auto text-center flex flex-col items-center gap-6">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">MISIÓN</p>
          <h2 className="text-3xl font-bold">Nuestra misión</h2>
          <p className="text-white/60 text-xl leading-relaxed max-w-3xl">
            Democratizar el aprendizaje musical haciendo que cualquier persona, sin importar su nivel
            o recursos, pueda descubrir los acordes de las canciones que ama y aprender a tocarlas.
          </p>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 px-6 border-b border-white/5">
        <div className="max-w-5xl mx-auto flex flex-col gap-12">
          <div className="text-center flex flex-col gap-3">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">VALORES</p>
            <h2 className="text-3xl font-bold">Lo que nos guía</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {values.map(({ icon, title, description }) => (
              <div
                key={title}
                className="bg-white/3 border border-white/8 rounded-2xl p-6 flex flex-col gap-4 hover:border-yellow-400/20 transition-colors"
              >
                <span className="text-3xl">{icon}</span>
                <h3 className="text-lg font-bold text-white">{title}</h3>
                <p className="text-white/40 text-sm leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-20 px-6 border-b border-white/5">
        <div className="max-w-5xl mx-auto flex flex-col gap-12">
          <div className="text-center flex flex-col gap-3">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">EQUIPO</p>
            <h2 className="text-3xl font-bold">Las personas detrás de ChordLens</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {team.map(({ name, role, description, initials }) => (
              <div
                key={name}
                className="bg-white/3 border border-white/8 rounded-2xl p-6 flex flex-col gap-5"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-yellow-400 flex items-center justify-center shrink-0">
                    <span className="text-gray-950 font-black text-sm">{initials}</span>
                  </div>
                  <div>
                    <p className="font-bold text-white text-sm">{name}</p>
                    <p className="text-yellow-400/70 text-xs">{role}</p>
                  </div>
                </div>
                <p className="text-white/40 text-sm leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto flex flex-col gap-12">
          <div className="text-center flex flex-col gap-3">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">TECNOLOGÍA</p>
            <h2 className="text-3xl font-bold">Cómo está construido</h2>
            <p className="text-white/40 text-sm max-w-xl mx-auto">
              ChordLens combina tecnologías modernas de desarrollo web con herramientas especializadas
              en procesamiento de audio y machine learning.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {techStack.map(({ name, desc }) => (
              <div
                key={name}
                className="bg-white/3 border border-white/8 rounded-xl p-4 flex flex-col gap-2 hover:border-white/15 transition-colors"
              >
                <span className="text-white font-mono font-bold text-sm">{name}</span>
                <span className="text-white/30 text-xs leading-relaxed">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

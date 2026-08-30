'use client'

import { useState } from 'react'

interface FAQItem {
  q: string
  a: string
}

interface FAQSection {
  category: string
  icon: string
  items: FAQItem[]
}

const faqs: FAQSection[] = [
  {
    category: 'Primeros pasos',
    icon: '🚀',
    items: [
      {
        q: '¿Qué es ChordLens?',
        a: 'ChordLens es una herramienta web que analiza el audio de videos de YouTube para detectar los acordes reales de cualquier canción. A diferencia de las tablaturras manuales, ChordLens extrae los acordes directamente del audio, lo que significa que lo que ves es lo que realmente suena en la grabación. El resultado se muestra en un timeline sincronizado con el video, junto con herramientas de transposición, capo y visualización.',
      },
      {
        q: '¿Cómo se usa ChordLens?',
        a: 'El proceso es muy simple: abrí YouTube, buscá la canción que querés aprender y copiá la URL del video (algo como https://www.youtube.com/watch?v=...). Luego pegala en el campo de búsqueda de ChordLens y hacé clic en "ANALIZAR". El sistema va a descargar el audio, analizarlo y mostrarte los acordes en un timeline interactivo. El análisis suele tardar entre 30 y 90 segundos dependiendo de la duración de la canción.',
      },
      {
        q: '¿Qué URLs acepta ChordLens?',
        a: 'ChordLens acepta cualquier URL válida de YouTube. Esto incluye el formato largo (https://www.youtube.com/watch?v=ID), el formato corto de youtu.be (https://youtu.be/ID), y URLs con timestamp o parámetros adicionales. No funciona con videos privados, con restricción de edad sin verificación, o con contenido bloqueado por derechos de autor en tu región. Tampoco funciona con Spotify, SoundCloud u otras plataformas.',
      },
    ],
  },
  {
    category: 'Análisis',
    icon: '🎵',
    items: [
      {
        q: '¿Cuánto tarda el análisis?',
        a: 'El tiempo de análisis depende principalmente de la duración del video. Para canciones de hasta 4 minutos, el proceso suele completarse en 30 a 60 segundos. Canciones más largas pueden tardar hasta 90 segundos o más. Esto se debe a que el proceso involucra tres etapas: descarga del audio desde YouTube, análisis de frecuencias con algoritmos de detección de notas, y clasificación de los acordes resultantes. No es posible acelerar este proceso sin reducir la calidad del análisis.',
      },
      {
        q: '¿Por qué puede fallar el análisis?',
        a: 'Hay varias razones por las que el análisis puede no completarse correctamente. La más común es que el video no está disponible en tu región, que tiene restricciones de descarga, o que es un video privado. También puede fallar si el audio tiene demasiado ruido de fondo, si es una grabación en vivo con mala calidad, o si contiene principalmente percusión sin melodía. Otro caso común son los videos de muy larga duración (más de 10 minutos). Si el análisis falla, intentá con otra versión de la misma canción en YouTube.',
      },
      {
        q: '¿En qué tipo de canciones funciona mejor?',
        a: 'ChordLens funciona mejor con canciones que tienen instrumentos melódicos bien definidos: guitarra, piano, bajo, o voz clara. El análisis es más preciso en grabaciones de estudio con buena calidad de audio. Funciona bien en pop, rock, baladas, folk y música acústica. El rendimiento puede ser menor en estilos con mucha percusión dominante (algunos tipos de electrónica o hip-hop), en grabaciones con mucho reverb o efectos, o en géneros con microtonalidad como cierta música árabe o india.',
      },
    ],
  },
  {
    category: 'Transposición',
    icon: '🎸',
    items: [
      {
        q: '¿Qué es el capo y para qué sirve?',
        a: 'El capo (o cejilla) es un accesorio que se coloca en el mástil de la guitarra para subir el tono de todas las cuerdas simultáneamente. Se usa principalmente para cambiar la tonalidad de una canción sin tener que cambiar las posiciones de los acordes. Por ejemplo, si una canción está en Si Mayor (con acordes difíciles), podés colocar el capo en el traste 2 y tocar los acordes de La Mayor, que son mucho más sencillos. ChordLens te permite indicar en qué traste tenés el capo y automáticamente adapta los acordes mostrados.',
      },
      {
        q: '¿Cómo funciona la transposición en ChordLens?',
        a: 'La transposición te permite subir o bajar el tono de los acordes detectados. Podés usar el slider de transposición para mover los acordes hacia arriba (semitonos positivos) o hacia abajo (semitonos negativos) sin cambiar el video. Esto es útil cuando querés tocar la canción en una tonalidad diferente, por ejemplo para adaptarla a tu rango vocal. Podés combinar el capo con la transposición para encontrar la combinación de acordes más cómoda para tocar.',
      },
      {
        q: '¿Qué es un semitono?',
        a: 'Un semitono es la distancia más pequeña entre dos notas en la música occidental. Es el intervalo entre dos teclas adyacentes en un piano (incluyendo las teclas negras). Por ejemplo, de Do a Do# hay un semitono, de Mi a Fa también hay un semitono. En la guitarra, cada traste representa exactamente un semitono. Cuando transponés una canción +2 semitonos, todas las notas suben dos semitonos: lo que era Do se convierte en Re, lo que era La se convierte en Si, y así sucesivamente.',
      },
    ],
  },
  {
    category: 'Técnico',
    icon: '⚙️',
    items: [
      {
        q: '¿Por qué ChordLens necesita Python?',
        a: 'El corazón del análisis de audio de ChordLens está escrito en Python porque las mejores bibliotecas de procesamiento de señales y machine learning para audio (como librosa, Basic Pitch de Spotify, y numpy) están disponibles en ese ecosistema. El servidor Node.js de Next.js llama al script Python como un proceso separado para realizar el análisis. Si estás usando la versión web de ChordLens, no necesitás instalar nada. Si querés correr ChordLens en tu propio servidor, necesitarás Python 3.8+ con las dependencias correspondientes.',
      },
      {
        q: '¿ChordLens es gratuito?',
        a: 'Sí, ChordLens ofrece un plan gratuito con 10 análisis por día, suficiente para la mayoría de los usuarios casuales. No necesitás registrarte ni dar información de pago para usar el plan gratuito. Ofrecemos planes pagos (Pro y Equipo) para usuarios que necesiten más análisis, funciones avanzadas como exportación a PDF, o acceso a la API. Todos los planes incluyen las funciones principales de análisis de acordes, capo y transposición.',
      },
    ],
  },
]

function AccordionItem({ q, a }: FAQItem) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border border-white/8 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-4 hover:bg-white/3 transition-colors"
      >
        <span className="text-sm font-medium text-white/80">{q}</span>
        <span
          className={`text-white/30 text-lg font-light shrink-0 transition-transform duration-200 ${
            open ? 'rotate-45' : ''
          }`}
        >
          +
        </span>
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-white/5">
          <p className="text-white/50 text-sm leading-relaxed pt-4">{a}</p>
        </div>
      )}
    </div>
  )
}

export default function AyudaPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="border-b border-white/5 py-16 px-6 text-center">
        <div className="max-w-2xl mx-auto flex flex-col items-center gap-4">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">CENTRO DE AYUDA</p>
          <h1 className="text-4xl font-black tracking-tighter">¿En qué podemos ayudarte?</h1>
          <p className="text-white/40 text-sm">
            Encontrá respuestas a las preguntas más frecuentes sobre ChordLens.
          </p>

          {/* Search bar (UI only) */}
          <div className="w-full mt-4 relative">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <span className="text-white/20 text-sm">🔍</span>
            </div>
            <input
              type="text"
              placeholder="Buscá una pregunta..."
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-yellow-400/40 transition-colors"
            />
          </div>
        </div>
      </section>

      {/* FAQ sections */}
      <section className="py-16 px-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-14">
          {faqs.map((section) => (
            <div key={section.category} className="flex flex-col gap-5">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{section.icon}</span>
                <h2 className="text-lg font-bold text-white">{section.category}</h2>
              </div>
              <div className="flex flex-col gap-3">
                {section.items.map((item) => (
                  <AccordionItem key={item.q} q={item.q} a={item.a} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Contact section */}
      <section className="border-t border-white/5 py-16 px-6">
        <div className="max-w-3xl mx-auto bg-white/3 border border-white/8 rounded-2xl p-8 text-center flex flex-col items-center gap-5">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">CONTACTO</p>
          <h2 className="text-2xl font-bold">¿No encontraste tu respuesta?</h2>
          <p className="text-white/40 text-sm max-w-md leading-relaxed">
            Si tenés una pregunta que no está cubierta en esta sección, escribinos directamente.
            Respondemos todos los mensajes en menos de 48 horas hábiles.
          </p>
          <a
            href="mailto:hola@chordlens.app"
            className="bg-yellow-400 text-gray-950 text-sm font-bold px-6 py-2.5 rounded-lg hover:bg-yellow-300 transition-colors"
          >
            Escribinos a hola@chordlens.app
          </a>
          <p className="text-white/20 text-xs">
            También podés encontrarnos en{' '}
            <a href="https://twitter.com/chordlens" className="text-white/40 hover:text-white/60 underline">
              @chordlens
            </a>{' '}
            en Twitter/X.
          </p>
        </div>
      </section>
    </div>
  )
}

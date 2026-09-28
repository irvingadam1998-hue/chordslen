import Link from 'next/link'
import {
  ArrowRight,
  ChevronDown,
  Headphones,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react'
import PageHeading from '@/components/PageHeading'
export const metadata = { title: 'Ayuda — ChordLens' }
const sections = [
  {
    title: 'Empieza con una canción',
    icon: Headphones,
    items: [
      [
        '¿Cómo encuentro los acordes?',
        'Pega un enlace de YouTube o sube un archivo de audio. Cuando termine el análisis, reproduce la canción y sigue la tarjeta resaltada. Puedes seleccionar cualquier acorde para saltar a ese momento.',
      ],
      [
        '¿Cuánto tarda?',
        'Depende de la duración del audio, la descarga y los recursos del servidor. Puede tardar varios minutos. La pantalla muestra el tiempo transcurrido mientras espera la respuesta.',
      ],
      [
        '¿Qué archivos puedo subir?',
        'MP3, WAV, FLAC, M4A, OGG y otros formatos de audio compatibles. El límite habitual es 50 MB; la aplicación verifica el límite configurado por el servidor antes de subirlo.',
      ],
    ],
  },
  {
    title: 'Practica a tu manera',
    icon: SlidersHorizontal,
    items: [
      [
        '¿Los números de las tarjetas son compases?',
        'No. Identifican los cambios detectados. Cada tarjeta muestra el instante de inicio y, cuando se conoce, la duración del acorde.',
      ],
      [
        '¿Qué cambia al transportar?',
        'Se modifican los nombres y posiciones de los acordes, incluidas séptimas e inversiones. El audio mantiene su tono original. El capo adapta las posiciones a la cejilla que indiques.',
      ],
      [
        '¿Qué significa C/E?',
        'Es un acorde de Do mayor con Mi en el bajo. Si no hay una posición compatible en la biblioteca, la aplicación lo indica en lugar de mostrar una posición distinta.',
      ],
      [
        '¿Puedo guardar la progresión?',
        'Sí. Exportar TXT descarga la secuencia con sus tiempos y los ajustes actuales de capo y transposición.',
      ],
    ],
  },
  {
    title: 'Cuando algo falla',
    icon: TriangleAlert,
    items: [
      [
        '¿Los acordes siempre son correctos?',
        'Son estimaciones automáticas. La mezcla, el ruido, las notas compartidas y los cambios rápidos pueden generar ambigüedad. Escucha los pasajes dudosos y compara con tu instrumento.',
      ],
      [
        'YouTube rechaza la descarga. ¿Qué hago?',
        'Puedes continuar subiendo un archivo de audio. Si aparece un aviso de cookies, la persona que administra el servidor debe renovar la sesión de YouTube configurada allí.',
      ],
    ],
  },
]
export default function AyudaPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <PageHeading label="Centro de ayuda" title="Menos dudas. Más música.">
        Todo lo necesario para pasar de tu primera canción a una sesión de
        práctica.
      </PageHeading>
      <div className="grid items-start gap-10 lg:grid-cols-[1fr_280px]">
        <div className="space-y-8">
          {sections.map(({ title, icon: Icon, items }) => (
            <section key={title}>
              <h2 className="mb-4 flex items-center gap-2 text-lg font-extrabold">
                <Icon size={20} />
                {title}
              </h2>
              <div className="panel divide-y divide-[#dce2d8]">
                {items.map(([q, a]) => (
                  <details key={q} className="group p-5">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-bold">
                      {q}
                      <ChevronDown
                        size={16}
                        className="transition-transform group-open:rotate-180"
                      />
                    </summary>
                    <p className="muted mt-4 max-w-2xl text-sm leading-7">
                      {a}
                    </p>
                  </details>
                ))}
              </div>
            </section>
          ))}
        </div>
        <aside id="cookies" className="notice scroll-mt-28 flex-col">
          <TriangleAlert size={23} />
          <h2 className="font-extrabold">Actualizar cookies</h2>
          <p>
            Este aviso se refiere a la sesión de YouTube del servidor, no a las
            cookies de tu navegador.
          </p>
          <p>
            Si administras ChordLens, sigue la guía{' '}
            <strong>COOKIES_YOUTUBE.md</strong> del proyecto para exportarlas y
            reemplazarlas en el backend. No pegues su contenido en la
            aplicación.
          </p>
          <Link
            href="/#analizar"
            className="mt-2 flex items-center gap-2 font-bold"
          >
            Usar un archivo <ArrowRight size={16} />
          </Link>
        </aside>
      </div>
    </main>
  )
}

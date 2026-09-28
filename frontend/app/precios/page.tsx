import Link from 'next/link'
import { ArrowRight, Check, Guitar } from 'lucide-react'
import PageHeading from '@/components/PageHeading'
export const metadata = { title: 'Disponibilidad — ChordLens' }
export default function PreciosPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <PageHeading
        label="Disponibilidad"
        title="Empieza por tu próxima canción."
      >
        Las herramientas de esta versión están disponibles sin registro ni
        contratación de una suscripción.
      </PageHeading>
      <section className="panel grid max-w-4xl gap-8 p-7 sm:p-10 md:grid-cols-2">
        <div>
          <Guitar size={32} className="mb-6" />
          <h2 className="text-2xl font-extrabold">Tu estudio de práctica</h2>
          <p className="muted my-4 text-sm leading-7">
            El tiempo y la disponibilidad del análisis dependen del servidor.
            Esta versión no ofrece una cola de pago ni planes de análisis
            prioritario.
          </p>
          <Link href="/#analizar" className="btn-primary">
            Analizar una canción <ArrowRight size={16} />
          </Link>
        </div>
        <ul className="flex flex-col justify-center gap-5">
          {[
            'Enlaces de YouTube y archivos de audio',
            'Secuencia de acordes y reproducción',
            'Diagramas, capo y transposición',
            'Exportación de la progresión a TXT',
            'Afinador cromático y glosario',
          ].map((text) => (
            <li key={text} className="flex items-start gap-3 text-sm">
              <Check size={18} className="text-[#64804f]" />
              {text}
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}

import { AudioLines, Ear, Guitar, ScanLine } from 'lucide-react'
import PageHeading from '@/components/PageHeading'
export const metadata = { title: 'El proyecto — ChordLens' }
export default function NosotrosPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <PageHeading
        label="El proyecto"
        title="Entender una canción, acorde a acorde."
      >
        ChordLens es un espacio para explorar la armonía del audio y convertir
        esa exploración en práctica.
      </PageHeading>
      <section className="mb-10 grid gap-8 rounded-3xl bg-[#284e3e] p-8 text-white sm:p-12 md:grid-cols-2">
        <div>
          <AudioLines size={32} className="mb-6 text-[#d9f58a]" />
          <h2 className="text-3xl font-extrabold tracking-tight">
            Una guía que acompaña
            <br />a tu oído.
          </h2>
        </div>
        <p className="self-center text-sm leading-8 text-[#d0ddce]">
          Un enlace o un archivo se convierte en una secuencia de acordes con
          tiempos. Puedes escuchar cada cambio, consultar una posición y ajustar
          la tonalidad mostrada. El objetivo es ayudarte a descubrir la música,
          con resultados que puedas comprobar.
        </p>
      </section>
      <div className="grid gap-5 md:grid-cols-3">
        {[
          {
            icon: Ear,
            title: 'Escuchar primero',
            text: 'Los acordes detectados son una referencia para explorar. Una grabación puede admitir distintas interpretaciones.',
          },
          {
            icon: Guitar,
            title: 'Practicar con claridad',
            text: 'El acorde actual, el siguiente y la secuencia completa comparten un mismo espacio, sin perder el momento de la canción.',
          },
          {
            icon: ScanLine,
            title: 'Medir las mejoras',
            text: 'El reconocimiento está evolucionando. La precisión se comprueba con audio anotado y evaluación temporal, sin prometer resultados perfectos.',
          },
        ].map(({ icon: Icon, title, text }) => (
          <article className="panel p-6" key={title}>
            <Icon size={24} className="mb-6" />
            <h2 className="mb-3 text-lg font-extrabold">{title}</h2>
            <p className="muted text-sm leading-7">{text}</p>
          </article>
        ))}
      </div>
    </main>
  )
}

import { Headphones, Mic, SlidersHorizontal } from 'lucide-react'
import Tuner from '@/components/Tuner'
import PageHeading from '@/components/PageHeading'
export const metadata = {
  title: 'Afinador de guitarra — ChordLens',
  description:
    'Afinador cromático con micrófono. Afinación estándar EADGBE, A4 = 440 Hz.',
}
export default function AfinadorPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <div className="grid items-start gap-12 lg:grid-cols-2">
        <div>
          <PageHeading label="Antes de tocar" title="Todo empieza por afinar.">
            Acerca tu guitarra, activa el micrófono y pulsa una cuerda. El
            afinador escucha directamente desde tu navegador.
          </PageHeading>
          <div className="flex flex-col gap-6">
            {[
              {
                icon: Mic,
                title: 'Activa el micrófono',
                text: 'Permite el acceso cuando lo solicite tu navegador.',
              },
              {
                icon: Headphones,
                title: 'Una cuerda a la vez',
                text: 'Deja que suene y evita ruido alrededor.',
              },
              {
                icon: SlidersHorizontal,
                title: 'Busca el centro',
                text: 'Ajusta suavemente hasta que el indicador marque Afinado.',
              },
            ].map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex items-start gap-4">
                <span className="rounded-xl border border-[#dce2d8] bg-white p-3">
                  <Icon size={20} />
                </span>
                <div>
                  <h2 className="text-sm font-bold">{title}</h2>
                  <p className="muted mt-1 text-xs leading-6">{text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <section className="panel p-6 sm:p-10" aria-label="Afinador cromático">
          <Tuner />
        </section>
      </div>
    </main>
  )
}

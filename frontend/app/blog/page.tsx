import Link from 'next/link'
import { ArrowRight, BookOpen } from 'lucide-react'
import PageHeading from '@/components/PageHeading'
export const metadata = { title: 'Aprender — ChordLens' }
const lessons = [
  {
    title: 'Leer un diagrama',
    subtitle: 'Tu primera posición',
    body: 'Las seis líneas verticales representan las cuerdas, de la más grave a la más aguda. Los puntos muestran dónde pisar; los números indican dedos. Un círculo sobre una cuerda significa que suena al aire y una cruz indica que no se toca. El número al lado del diagrama señala el primer traste mostrado.',
  },
  {
    title: 'Mayor, menor y séptima',
    subtitle: 'El color de un acorde',
    body: 'Do mayor contiene Do, Mi y Sol. Si bajas Mi un semitono, obtienes Do menor. Añadir Si produce Cmaj7; añadir Si bemol produce C7. Por eso las letras y números después de la raíz importan: describen notas diferentes, no solo distintas maneras de escribir el mismo acorde.',
  },
  {
    title: 'El bajo también cuenta',
    subtitle: 'Entender las inversiones',
    body: 'C/E conserva las notas de Do mayor, pero sitúa Mi en el bajo. C/G pone Sol en esa posición. Al escuchar una progresión, presta atención al movimiento de las notas graves: puede unir acordes con transiciones más suaves.',
  },
  {
    title: 'Practicar un cambio',
    subtitle: 'Poco a poco',
    body: 'Selecciona el acorde que te cuesta para escuchar su inicio. Mira qué posición viene después e identifica qué dedos pueden quedarse cerca de las cuerdas. Alterna ambas posiciones lentamente antes de volver a tocar sobre la grabación.',
  },
]
export default function BlogPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <PageHeading label="Aprender" title="Pequeñas ideas para tocar mejor.">
        Una referencia breve para leer los acordes y sacar más partido a cada
        sesión.
      </PageHeading>
      <div className="grid gap-6 md:grid-cols-2">
        {lessons.map((lesson, i) => (
          <article key={lesson.title} className="panel p-7">
            <div className="mb-7 flex items-center justify-between">
              <BookOpen size={21} />
              <span className="muted font-mono text-xs">0{i + 1}</span>
            </div>
            <p className="eyebrow mb-2">{lesson.subtitle}</p>
            <h2 className="section-title mb-4">{lesson.title}</h2>
            <p className="muted text-sm leading-7">{lesson.body}</p>
          </article>
        ))}
      </div>
      <Link href="/glosario" className="btn-soft mt-8">
        Explorar el glosario <ArrowRight size={16} />
      </Link>
    </main>
  )
}

import Link from 'next/link'
import { AudioLines } from 'lucide-react'
export default function Footer() {
  return (
    <footer className="mt-auto border-t border-[#dce2d8] py-9">
      <div className="shell flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-extrabold">
            <AudioLines size={18} /> chordlens.
          </p>
          <p className="muted text-xs">Escucha. Entiende. Toca.</p>
        </div>
        <nav
          aria-label="Enlaces del pie"
          className="flex flex-wrap gap-x-6 gap-y-3 text-xs font-semibold"
        >
          <Link href="/nosotros">El proyecto</Link>
          <Link href="/blog">Aprender</Link>
          <Link href="/ayuda">Ayuda</Link>
          <Link href="/precios">Disponibilidad</Link>
          <Link href="/privacidad">Privacidad</Link>
        </nav>
        <p className="muted max-w-[220px] text-xs leading-relaxed">
          Las estimaciones de acordes son una guía. Tu oído tiene la última
          palabra.
        </p>
      </div>
    </footer>
  )
}

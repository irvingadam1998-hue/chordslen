'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { AudioLines, ArrowUpRight, Menu, X } from 'lucide-react'

const links = [
  { href: '/', label: 'Estudio' },
  { href: '/afinador', label: 'Afinador' },
  { href: '/glosario', label: 'Acordes' },
  { href: '/ayuda', label: 'Ayuda' },
]
export default function Navbar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-50 border-b border-[#dce2d8] bg-[#f5f5f0]/95 backdrop-blur-lg">
      <div className="shell flex h-[76px] items-center justify-between gap-5">
        <Link
          href="/"
          onClick={() => setOpen(false)}
          aria-label="ChordLens, inicio"
          className="flex items-center gap-2.5"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#284e3e] text-[#d9f58a]">
            <AudioLines size={22} />
          </span>
          <span className="text-xl font-extrabold tracking-tight">
            chordlens<span className="text-[#75935b]">.</span>
          </span>
        </Link>
        <nav
          aria-label="Navegación principal"
          className="hidden items-center gap-1 md:flex"
        >
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? 'page' : undefined}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${pathname === link.href ? 'bg-[#e6ebdf] text-[#213e35]' : 'muted hover:bg-[#eceee7]'}`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/#analizar"
          className="hidden items-center gap-2 text-xs font-bold lg:flex"
        >
          Tu próxima canción <ArrowUpRight size={17} />
        </Link>
        <button
          className="icon-btn md:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {open && (
        <nav
          id="mobile-nav"
          aria-label="Navegación móvil"
          className="shell flex flex-col gap-1 pb-5 md:hidden"
        >
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              aria-current={pathname === link.href ? 'page' : undefined}
              className="rounded-lg px-3 py-3 text-sm font-semibold hover:bg-[#e6ebdf]"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  )
}

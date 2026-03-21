'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

const links = [
  { href: '/', label: 'Inicio' },
  { href: '/glosario', label: 'Glosario' },
  { href: '/blog', label: 'Blog' },
  { href: '/precios', label: 'Precios' },
  { href: '/ayuda', label: 'Ayuda' },
  { href: '/nosotros', label: 'Nosotros' },
]

export default function Navbar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#080808]/90 backdrop-blur-md border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-yellow-400 flex items-center justify-center shrink-0">
            <span className="text-gray-950 font-black text-sm">♪</span>
          </div>
          <span className="font-bold tracking-tight text-white group-hover:text-yellow-400 transition-colors">
            ChordLens
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm transition-colors ${
                pathname === href
                  ? 'text-yellow-400 font-medium'
                  : 'text-white/40 hover:text-white/80'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* CTA + hamburger */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-xs font-bold tracking-widest bg-yellow-400 text-gray-950 px-4 py-2 rounded-lg hover:bg-yellow-300 transition-colors hidden sm:block"
          >
            ANALIZAR
          </Link>
          {/* Hamburger */}
          <button
            onClick={() => setOpen(!open)}
            aria-label="Abrir menú"
            className="md:hidden flex flex-col gap-1.5 p-1"
          >
            <span
              className={`block w-5 h-px bg-white/60 transition-transform duration-200 ${
                open ? 'translate-y-[7px] rotate-45' : ''
              }`}
            />
            <span
              className={`block w-5 h-px bg-white/60 transition-opacity duration-200 ${
                open ? 'opacity-0' : ''
              }`}
            />
            <span
              className={`block w-5 h-px bg-white/60 transition-transform duration-200 ${
                open ? '-translate-y-[7px] -rotate-45' : ''
              }`}
            />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-white/5 bg-[#080808] px-6 py-4 flex flex-col gap-1">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={`text-sm py-2.5 transition-colors ${
                pathname === href
                  ? 'text-yellow-400 font-medium'
                  : 'text-white/50 hover:text-white/90'
              }`}
            >
              {label}
            </Link>
          ))}
          <div className="pt-3 border-t border-white/5 mt-2">
            <Link
              href="/"
              onClick={() => setOpen(false)}
              className="inline-block text-xs font-bold tracking-widest bg-yellow-400 text-gray-950 px-4 py-2 rounded-lg hover:bg-yellow-300 transition-colors"
            >
              ANALIZAR
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

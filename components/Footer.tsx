import Link from 'next/link'

const columns = [
  {
    heading: 'Producto',
    links: [
      { href: '/', label: 'Inicio' },
      { href: '/precios', label: 'Precios' },
      { href: '/changelog', label: 'Changelog' },
    ],
  },
  {
    heading: 'Recursos',
    links: [
      { href: '/glosario', label: 'Glosario' },
      { href: '/blog', label: 'Blog' },
      { href: '/ayuda', label: 'Ayuda' },
    ],
  },
  {
    heading: 'Legal',
    links: [
      { href: '/privacidad', label: 'Privacidad' },
      { href: '/terminos', label: 'Términos' },
    ],
  },
  {
    heading: 'Tecnología',
    links: [
      { href: 'https://github.com/yt-dlp/yt-dlp', label: 'yt-dlp', external: true },
      { href: 'https://librosa.org', label: 'librosa', external: true },
      { href: 'https://nextjs.org', label: 'Next.js', external: true },
    ],
  },
]

export default function Footer() {
  return (
    <footer className="border-t border-white/5 bg-[#080808] pt-12 pb-8 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Top section */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 sm:col-span-3 lg:col-span-1 flex flex-col gap-3">
            <Link href="/" className="flex items-center gap-2.5 group w-fit">
              <div className="w-7 h-7 rounded-lg bg-yellow-400 flex items-center justify-center shrink-0">
                <span className="text-gray-950 font-black text-sm">♪</span>
              </div>
              <span className="font-bold tracking-tight text-white group-hover:text-yellow-400 transition-colors">
                ChordLens
              </span>
            </Link>
            <p className="text-white/30 text-sm leading-relaxed max-w-xs">
              Detectá los acordes de cualquier canción.
            </p>
          </div>

          {/* Link columns */}
          {columns.map((col) => (
            <div key={col.heading} className="flex flex-col gap-3">
              <p className="text-white/60 text-xs font-semibold tracking-widest uppercase">
                {col.heading}
              </p>
              <ul className="flex flex-col gap-2">
                {col.links.map((link) => (
                  <li key={link.href}>
                    {'external' in link && link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-white/30 text-sm hover:text-white/70 transition-colors"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-white/30 text-sm hover:text-white/70 transition-colors"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-white/5 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-white/20 text-xs">
          <p>© 2025 ChordLens · Todos los derechos reservados.</p>
          <p className="text-center sm:text-right">
            Los acordes son aproximados según análisis de audio.
          </p>
        </div>
      </div>
    </footer>
  )
}

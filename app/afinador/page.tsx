import Tuner from '@/components/Tuner'

export const metadata = {
  title: 'Afinador de guitarra online — ChordLens',
  description: 'Afinador cromático gratuito que usa el micrófono de tu dispositivo. Afinación estándar EADGBE, A4 = 440 Hz.',
}

export default function AfinadorPage() {
  return (
    <main className="min-h-screen text-white flex flex-col">

      {/* Header */}
      <section className="border-b border-white/5 py-16 px-6 text-center">
        <div className="max-w-xl mx-auto flex flex-col items-center gap-4">
          <div className="inline-flex items-center gap-2 bg-yellow-400/10 border border-yellow-400/20 rounded-full px-4 py-1.5 text-yellow-400 text-xs font-medium tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
            Herramienta gratuita
          </div>
          <h1 className="text-4xl sm:text-5xl font-black tracking-tighter">
            Afinador de guitarra
          </h1>
          <p className="text-white/40 text-sm leading-relaxed max-w-sm">
            Afinador cromático que usa el micrófono de tu dispositivo.
            Estándar <span className="text-white/60 font-mono">A4 = 440 Hz</span>.
          </p>
        </div>
      </section>

      {/* Tuner */}
      <section className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm bg-white/3 border border-white/8 rounded-2xl p-8">
          <Tuner />
        </div>
      </section>

      {/* How to use */}
      <section className="border-t border-white/5 py-16 px-6">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-sm font-semibold tracking-widest text-white/30 uppercase mb-8 text-center">Cómo usar</h2>
          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { n: '01', title: 'Activá el micrófono', desc: 'Presioná el botón y permitile acceso al micrófono al navegador.' },
              { n: '02', title: 'Tocá una cuerda', desc: 'Pulsá la cuerda de tu guitarra cerca del micrófono. La nota detectada aparece en grande.' },
              { n: '03', title: 'Ajustá hasta centrar', desc: 'La aguja muestra cuántos cents estás desviado. Cuando se pone amarilla, estás afinado.' },
            ].map(({ n, title, desc }) => (
              <div key={n} className="flex flex-col gap-3 p-5 rounded-xl bg-white/3 border border-white/8">
                <span className="text-white/15 font-mono text-xs">{n}</span>
                <h3 className="font-semibold text-sm text-white">{title}</h3>
                <p className="text-white/40 text-xs leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

    </main>
  )
}

'use client'

import { useState } from 'react'
import Link from 'next/link'

const freeFeatures = [
  '10 análisis por día',
  'Acordes básicos y extendidos',
  'Player sincronizado con video',
  'Mapa visual de acordes',
  'Transposición y capo básico',
  'Glosario de acordes',
]

const proFeatures = [
  'Análisis ilimitados',
  'Todo lo del plan Gratuito',
  'Transposición y capo avanzado',
  'Letra sincronizada incluida',
  'Exportar acordes a PDF',
  'Análisis prioritario (más rápido)',
  'Soporte por email',
]

const teamFeatures = [
  'Todo lo del plan Pro',
  'Hasta 5 usuarios',
  'Biblioteca compartida de canciones',
  'Acceso a la API de ChordLens',
  'Soporte dedicado',
  'Facturación centralizada',
  'SLA de disponibilidad 99.9%',
]

const billingFAQ = [
  {
    q: '¿Puedo cancelar en cualquier momento?',
    a: 'Sí. Podés cancelar tu suscripción cuando quieras desde el panel de usuario. Al cancelar, tu plan Pro o Equipo sigue activo hasta el final del período de facturación actual. No hacemos reembolsos por períodos no utilizados.',
  },
  {
    q: '¿Qué métodos de pago aceptan?',
    a: 'Aceptamos tarjetas de crédito y débito internacionales (Visa, Mastercard, American Express). El pago es procesado de forma segura por Stripe. No almacenamos datos de tarjetas en nuestros servidores.',
  },
  {
    q: '¿El plan Gratuito tiene fecha de vencimiento?',
    a: 'No. El plan Gratuito es permanente y no requiere tarjeta de crédito ni registro. Podés usarlo sin límite de tiempo, con el límite de 10 análisis por día.',
  },
  {
    q: '¿Hay descuento para estudiantes o educadores?',
    a: 'Sí. Ofrecemos un 50% de descuento en el plan Pro para estudiantes universitarios y docentes de música. Escribinos a hola@chordlens.app con tu certificado de estudiante o credencial docente y te enviamos el código de descuento.',
  },
]

export default function PreciosPage() {
  const [annual, setAnnual] = useState(false)
  const [openFAQ, setOpenFAQ] = useState<number | null>(null)

  const proPrice = annual ? 7 : 9
  const teamPrice = annual ? 23 : 29

  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="border-b border-white/5 py-16 px-6 text-center">
        <div className="max-w-2xl mx-auto flex flex-col items-center gap-4">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">PRECIOS</p>
          <h1 className="text-4xl font-black tracking-tighter">Simple y transparente</h1>
          <p className="text-white/40 text-sm leading-relaxed">
            Empezá gratis. Sin tarjeta de crédito. Sin sorpresas.
          </p>

          {/* Billing toggle */}
          <div className="flex items-center gap-3 mt-4 bg-white/5 border border-white/8 rounded-full p-1">
            <button
              onClick={() => setAnnual(false)}
              className={`text-xs font-medium px-4 py-1.5 rounded-full transition-colors ${
                !annual ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
              }`}
            >
              Mensual
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`text-xs font-medium px-4 py-1.5 rounded-full transition-colors flex items-center gap-2 ${
                annual ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
              }`}
            >
              Anual
              <span className="text-[10px] bg-yellow-400 text-gray-950 font-bold px-2 py-0.5 rounded-full">
                AHORRÁ 20%
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Pricing cards */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-5">

          {/* Free */}
          <div className="bg-white/3 border border-white/8 rounded-2xl p-7 flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <p className="text-white/60 text-sm font-medium">Gratuito</p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-black text-white">$0</span>
                <span className="text-white/30 text-sm mb-1">/mes</span>
              </div>
              <p className="text-white/30 text-xs">Para uso casual y aprendizaje.</p>
            </div>
            <Link
              href="/"
              className="w-full text-center text-xs font-bold tracking-wider border border-white/15 text-white/70 py-2.5 rounded-xl hover:border-white/30 hover:text-white transition-colors"
            >
              EMPEZAR GRATIS
            </Link>
            <ul className="flex flex-col gap-3">
              {freeFeatures.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-sm text-white/50">
                  <span className="text-white/30 mt-0.5 shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Pro */}
          <div className="bg-yellow-400/5 border border-yellow-400/30 rounded-2xl p-7 flex flex-col gap-6 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="bg-yellow-400 text-gray-950 text-[10px] font-black tracking-widest px-3 py-1 rounded-full">
                MÁS POPULAR
              </span>
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-yellow-400 text-sm font-medium">Pro</p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-black text-white">${proPrice}</span>
                <span className="text-white/30 text-sm mb-1">/mes</span>
              </div>
              {annual && (
                <p className="text-yellow-400/60 text-xs">Facturado anualmente (${proPrice * 12}/año)</p>
              )}
              <p className="text-white/30 text-xs">Para músicos y estudiantes activos.</p>
            </div>
            <Link
              href="/"
              className="w-full text-center text-xs font-bold tracking-wider bg-yellow-400 text-gray-950 py-2.5 rounded-xl hover:bg-yellow-300 transition-colors"
            >
              EMPEZAR PRUEBA GRATIS
            </Link>
            <ul className="flex flex-col gap-3">
              {proFeatures.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-sm text-white/60">
                  <span className="text-yellow-400 mt-0.5 shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Team */}
          <div className="bg-white/3 border border-white/8 rounded-2xl p-7 flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <p className="text-white/60 text-sm font-medium">Equipo</p>
              <div className="flex items-end gap-1">
                <span className="text-4xl font-black text-white">${teamPrice}</span>
                <span className="text-white/30 text-sm mb-1">/mes</span>
              </div>
              {annual && (
                <p className="text-white/30 text-xs">Facturado anualmente (${teamPrice * 12}/año)</p>
              )}
              <p className="text-white/30 text-xs">Para escuelas de música y bandas.</p>
            </div>
            <a
              href="mailto:hola@chordlens.app?subject=Plan%20Equipo"
              className="w-full text-center text-xs font-bold tracking-wider border border-white/15 text-white/70 py-2.5 rounded-xl hover:border-white/30 hover:text-white transition-colors"
            >
              CONTACTAR VENTAS
            </a>
            <ul className="flex flex-col gap-3">
              {teamFeatures.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-sm text-white/50">
                  <span className="text-white/30 mt-0.5 shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Comparison note */}
      <section className="py-6 px-6 text-center">
        <p className="text-white/25 text-xs">
          Todos los planes incluyen acceso al glosario, blog y centro de ayuda.
          Los precios están en USD. Impuestos locales pueden aplicar.
        </p>
      </section>

      {/* FAQ section */}
      <section className="border-t border-white/5 py-16 px-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-10">
          <div className="text-center flex flex-col gap-3">
            <p className="text-yellow-400 text-xs font-mono tracking-widest">PREGUNTAS FRECUENTES</p>
            <h2 className="text-2xl font-bold">Sobre facturación</h2>
          </div>
          <div className="flex flex-col gap-3">
            {billingFAQ.map((item, i) => (
              <div key={i} className="border border-white/8 rounded-xl overflow-hidden">
                <button
                  onClick={() => setOpenFAQ(openFAQ === i ? null : i)}
                  className="w-full text-left px-5 py-4 flex items-center justify-between gap-4 hover:bg-white/3 transition-colors"
                >
                  <span className="text-sm font-medium text-white/80">{item.q}</span>
                  <span
                    className={`text-white/30 text-lg font-light shrink-0 transition-transform duration-200 ${
                      openFAQ === i ? 'rotate-45' : ''
                    }`}
                  >
                    +
                  </span>
                </button>
                {openFAQ === i && (
                  <div className="px-5 pb-5 border-t border-white/5">
                    <p className="text-white/45 text-sm leading-relaxed pt-4">{item.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA bottom */}
      <section className="border-t border-white/5 py-16 px-6 text-center">
        <div className="max-w-xl mx-auto flex flex-col items-center gap-5">
          <h2 className="text-2xl font-bold">¿Todavía tenés dudas?</h2>
          <p className="text-white/40 text-sm leading-relaxed">
            Empezá con el plan gratuito sin compromisos. Si necesitás más análisis o funciones
            avanzadas, podés actualizar cuando quieras.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <Link
              href="/"
              className="bg-yellow-400 text-gray-950 text-xs font-bold tracking-widest px-6 py-3 rounded-xl hover:bg-yellow-300 transition-colors"
            >
              EMPEZAR GRATIS
            </Link>
            <a
              href="mailto:hola@chordlens.app"
              className="border border-white/15 text-white/60 text-xs font-bold tracking-widest px-6 py-3 rounded-xl hover:border-white/30 hover:text-white transition-colors"
            >
              HABLAR CON EL EQUIPO
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}

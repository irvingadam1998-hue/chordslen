'use client'
import { useEffect, useState } from 'react'
import { LoaderCircle } from 'lucide-react'
export default function ProgressSteps({
  currentStep,
}: {
  currentStep: 1 | 2 | 3 | null
  hasError?: boolean
}) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const id = setInterval(
      () => setSeconds(Math.floor((Date.now() - started) / 1000)),
      1000,
    )
    return () => clearInterval(id)
  }, [])
  return (
    <div
      role="status"
      className="flex items-start gap-3 rounded-xl bg-[#edf2e6] p-4 text-sm"
    >
      <LoaderCircle size={19} className="mt-0.5 animate-spin" />
      <div>
        <p className="font-semibold">
          {currentStep === 1
            ? 'Enviando tu audio'
            : 'Tu canción se está procesando'}
        </p>
        <p className="muted mt-1 text-xs leading-relaxed">
          Puedes dejar esta página abierta. El tiempo depende de la canción y
          del servidor.
        </p>
        <p aria-live="off" className="muted mt-2 font-mono text-[10px]">
          {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}{' '}
          transcurridos
        </p>
      </div>
    </div>
  )
}

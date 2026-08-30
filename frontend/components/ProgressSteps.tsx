'use client'

interface ProgressStepsProps {
  currentStep: 1 | 2 | 3 | null
  hasError?: boolean
}

const steps = [
  { id: 1, label: 'Descargando audio desde YouTube' },
  { id: 2, label: 'Analizando frecuencias con IA' },
  { id: 3, label: 'Construyendo el mapa de acordes' },
]

export default function ProgressSteps({ currentStep, hasError }: ProgressStepsProps) {
  const getStatus = (stepId: number) => {
    if (currentStep === null) return 'completed'
    if (hasError && stepId === currentStep) return 'error'
    if (stepId < currentStep) return 'completed'
    if (stepId === currentStep) return 'active'
    return 'pending'
  }

  return (
    <div className="flex flex-col gap-2 w-full">
      {steps.map((step) => {
        const status = getStatus(step.id)
        return (
          <div key={step.id} className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border text-sm transition-all ${
            status === 'active'  ? 'bg-yellow-400/5 border-yellow-400/30 text-white' :
            status === 'completed' ? 'bg-white/3 border-white/8 text-white/40' :
            status === 'error'   ? 'bg-red-950/30 border-red-800/40 text-red-400' :
                                   'bg-transparent border-white/5 text-white/20'
          }`}>
            <div className="shrink-0 w-5 h-5 flex items-center justify-center">
              {status === 'completed' && (
                <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {status === 'active' && <div className="w-3.5 h-3.5 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin" />}
              {status === 'error' && (
                <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
              {status === 'pending' && <div className="w-1.5 h-1.5 rounded-full bg-white/20" />}
            </div>
            <span>{step.label}</span>
            {status === 'active' && (
              <span className="ml-auto text-[10px] text-yellow-400/60 font-mono">en progreso</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

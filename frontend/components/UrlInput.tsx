'use client'

interface UrlInputProps {
  url: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled: boolean
}

export default function UrlInput({ url, onChange, onSubmit, disabled }: UrlInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !disabled) {
      onSubmit()
    }
  }

  return (
    <div className="flex gap-2 w-full">
      <input
        type="text"
        value={url}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="https://www.youtube.com/watch?v=..."
        disabled={disabled}
        className="flex-1 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 focus:outline-none focus:border-yellow-400/60 focus:bg-white/8 transition-all disabled:opacity-40 disabled:cursor-not-allowed text-sm"
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !url.trim()}
        className="px-5 py-3 rounded-xl bg-yellow-400 text-gray-950 font-bold text-sm tracking-widest hover:bg-yellow-300 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap"
      >
        {disabled ? '...' : 'ANALIZAR'}
      </button>
    </div>
  )
}

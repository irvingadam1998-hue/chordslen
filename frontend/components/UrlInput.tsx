'use client'
import { ArrowRight, Link2 } from 'lucide-react'
export default function UrlInput({
  url,
  onChange,
  onSubmit,
  disabled,
}: {
  url: string
  onChange: (url: string) => void
  onSubmit: () => void
  disabled?: boolean
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
      className="flex flex-col gap-3"
    >
      <label htmlFor="youtube-url" className="text-xs font-semibold">
        Enlace de YouTube
      </label>
      <div className="relative">
        <Link2 size={18} className="muted absolute left-4 top-4" />
        <input
          id="youtube-url"
          type="url"
          required
          placeholder="https://www.youtube.com/watch?v=…"
          value={url}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="field pl-11"
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !url.trim()}
        className="btn-primary w-full"
      >
        {disabled ? 'Procesando audio' : 'Encontrar acordes'}
        <ArrowRight size={17} />
      </button>
    </form>
  )
}

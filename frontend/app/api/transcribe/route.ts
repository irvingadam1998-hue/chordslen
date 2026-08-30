import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

function isYouTubeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return [
      'www.youtube.com',
      'youtube.com',
      'youtu.be',
      'm.youtube.com',
    ].includes(parsed.hostname)
  } catch {
    return false
  }
}

export async function POST(req: NextRequest) {
  let body: { url?: string; start?: number; end?: number }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'JSON inválido' }, { status: 400 })
  }

  const { url, start, end } = body

  if (!url || typeof url !== 'string')
    return NextResponse.json({ error: 'URL requerida' }, { status: 400 })
  if (!isYouTubeUrl(url))
    return NextResponse.json(
      { error: 'La URL debe ser de YouTube' },
      { status: 400 }
    )
  if (typeof start !== 'number' || typeof end !== 'number')
    return NextResponse.json(
      { error: 'start y end requeridos' },
      { status: 400 }
    )
  if (end - start > 60)
    return NextResponse.json(
      { error: 'Máximo 60 segundos por transcripción' },
      { status: 400 }
    )
  if (end <= start)
    return NextResponse.json(
      { error: 'end debe ser mayor que start' },
      { status: 400 }
    )

  // ── Ruta fija temporal al backend de producción ───────────────────────
  const FALLBACK_BACKEND_URL = 'https://chordslen-production.up.railway.app'
  const FALLBACK_BACKEND_KEY = '7f9a8d2c1b4e5f6a8c9d0e1f2a3b4c5d'

  const backendUrl = (
    process.env.FLASK_API_URL ||
    process.env.REMOTE_EXTRACTOR_URL ||
    FALLBACK_BACKEND_URL
  ).replace(/\/$/, '')

  if (backendUrl) {
    try {
      const backendKey =
        process.env.FLASK_API_KEY ||
        process.env.REMOTE_EXTRACTOR_TOKEN ||
        process.env.API_KEY ||
        FALLBACK_BACKEND_KEY

      const res = await fetch(`${backendUrl}/transcribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(backendKey ? { 'x-api-key': backendKey } : {}),
        },
        body: JSON.stringify({ url, start, end }),
        signal: AbortSignal.timeout(180000),
      })
      const parsed = await res.json()
      if (!parsed.success)
        return NextResponse.json({ error: parsed.error }, { status: 500 })
      return NextResponse.json(parsed)
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : 'Error al contactar el servidor'
      return NextResponse.json({ error: msg }, { status: 500 })
    }
  }

  // ── Python local ──────────────────────────────────────────────────────────
  const scriptPath = path.join(process.cwd(), 'scripts', 'transcribe.py')
  const pythonCmd =
    process.platform === 'win32'
      ? 'python'
      : path.join(process.cwd(), '.venv', 'bin', 'python')

  const result = await new Promise<string>((resolve, reject) => {
    const timeout = setTimeout(() => {
      child.kill()
      reject(new Error('Timeout: la transcripción tardó más de 3 minutos.'))
    }, 180000)
    const child = spawn(
      pythonCmd,
      [scriptPath, url, String(start), String(end)],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    )
    let stdout = '',
      stderr = ''
    child.stdout.on('data', (d: Buffer) => {
      stdout += d.toString()
    })
    child.stderr.on('data', (d: Buffer) => {
      stderr += d.toString()
    })
    child.on('error', (err: NodeJS.ErrnoException) => {
      clearTimeout(timeout)
      reject(
        new Error(
          err.code === 'ENOENT' ? 'Python no está instalado.' : err.message
        )
      )
    })
    child.on('close', (code: number) => {
      clearTimeout(timeout)
      if (code !== 0 && !stdout)
        reject(new Error(stderr || `Script terminó con código ${code}`))
      else resolve(stdout)
    })
  }).catch((err: Error) =>
    JSON.stringify({ success: false, error: err.message })
  )

  try {
    const parsed = JSON.parse(result)
    if (!parsed.success)
      return NextResponse.json({ error: parsed.error }, { status: 500 })
    return NextResponse.json(parsed)
  } catch {
    return NextResponse.json(
      { error: 'Respuesta inválida del script Python' },
      { status: 500 }
    )
  }
}

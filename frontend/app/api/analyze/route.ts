import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

// ── Rate limiting ────────────────────────────────────────────────────────────
const RATE_LIMIT_MS = 5000 // 1 request per IP every 5 seconds
const ipLastRequest = new Map<string, number>()

function getClientIp(req: NextRequest): string {
  return (
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    req.headers.get('x-real-ip') ??
    'unknown'
  )
}

function isRateLimited(ip: string): boolean {
  const now = Date.now()
  const last = ipLastRequest.get(ip) ?? 0
  if (now - last < RATE_LIMIT_MS) return true
  ipLastRequest.set(ip, now)
  return false
}

function isYouTubeUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return (
      parsed.hostname === 'www.youtube.com' ||
      parsed.hostname === 'youtube.com' ||
      parsed.hostname === 'youtu.be' ||
      parsed.hostname === 'm.youtube.com'
    )
  } catch {
    return false
  }
}

const ANALYZE_TIMEOUT_MS = (() => {
  const value = Number(process.env.ANALYZE_TIMEOUT_MS || 600000)
  return Number.isFinite(value) && value > 0 ? value : 600000
})()

export async function POST(req: NextRequest) {
  const requiredKey = process.env.API_KEY
  if (requiredKey) {
    const providedKey = req.headers.get('x-api-key')
    if (providedKey !== requiredKey) {
      return NextResponse.json(
        { error: 'API key inválida o ausente' },
        { status: 401 }
      )
    }
  }

  const ip = getClientIp(req)
  if (isRateLimited(ip)) {
    return NextResponse.json(
      {
        error:
          'Demasiadas solicitudes. Espera 5 segundos antes de intentar de nuevo.',
      },
      { status: 429 }
    )
  }

  let body: { url?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json(
      { error: 'JSON inválido en el cuerpo de la solicitud' },
      { status: 400 }
    )
  }

  const { url } = body
  if (!url || typeof url !== 'string') {
    return NextResponse.json({ error: 'URL requerida' }, { status: 400 })
  }

  if (!isYouTubeUrl(url)) {
    return NextResponse.json(
      { error: 'La URL debe ser de YouTube' },
      { status: 400 }
    )
  }

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

      const res = await fetch(`${backendUrl}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(backendKey ? { 'x-api-key': backendKey } : {}),
        },
        body: JSON.stringify({ url }),
        signal: AbortSignal.timeout(30000),
      })

      const parsed = await res.json()

      if (res.status === 202 && parsed.job_id) {
        return NextResponse.json(
          { jobId: parsed.job_id, status: 'processing' },
          { status: 202 }
        )
      }

      if (parsed?.success === false || parsed?.error) {
        return NextResponse.json(
          { error: parsed.error || 'El análisis falló' },
          { status: res.status || 500 }
        )
      }

      return NextResponse.json(parsed)
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Error al contactar el servidor de análisis'
      return NextResponse.json({ error: msg }, { status: 500 })
    }
  }

  const scriptPath = path.join(process.cwd(), 'scripts', 'analyze.py')
  const pythonCmd =
    process.platform === 'win32'
      ? 'python'
      : path.join(process.cwd(), '.venv', 'bin', 'python')

  const result = await new Promise<string>((resolve, reject) => {
    const timeout = setTimeout(() => {
      child.kill()
      reject(
        new Error(
          `Timeout: el análisis tardó más de ${Math.round(ANALYZE_TIMEOUT_MS / 60000)} minutos. Intenta con una canción más corta.`
        )
      )
    }, ANALYZE_TIMEOUT_MS)

    const child = spawn(pythonCmd, [scriptPath, url], {
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (data: Buffer) => {
      stdout += data.toString()
    })

    child.stderr.on('data', (data: Buffer) => {
      stderr += data.toString()
    })

    child.on('error', (err: NodeJS.ErrnoException) => {
      clearTimeout(timeout)
      if (err.code === 'ENOENT') {
        reject(
          new Error(
            'Python no está instalado o no está en el PATH. Instala Python 3.8+ para continuar.'
          )
        )
      } else {
        reject(err)
      }
    })

    child.on('close', (code: number) => {
      clearTimeout(timeout)
      if (code !== 0 && !stdout) {
        reject(
          new Error(stderr || `El script Python terminó con código ${code}`)
        )
      } else {
        resolve(stdout)
      }
    })
  }).catch((err: Error) => {
    return JSON.stringify({ success: false, error: err.message })
  })

  try {
    const parsed = JSON.parse(result)
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error }, { status: 500 })
    }
    return NextResponse.json(parsed)
  } catch {
    return NextResponse.json(
      { error: 'El script Python devolvió una respuesta inválida' },
      { status: 500 }
    )
  }
}

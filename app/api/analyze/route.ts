import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

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

export async function POST(req: NextRequest) {
  let body: { url?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'JSON inválido en el cuerpo de la solicitud' }, { status: 400 })
  }

  const { url } = body

  if (!url || typeof url !== 'string') {
    return NextResponse.json({ error: 'URL requerida' }, { status: 400 })
  }

  if (!isYouTubeUrl(url)) {
    return NextResponse.json({ error: 'La URL debe ser de YouTube' }, { status: 400 })
  }

  const scriptPath = path.join(process.cwd(), 'scripts', 'analyze.py')

  const result = await new Promise<string>((resolve, reject) => {
    const timeout = setTimeout(() => {
      child.kill()
      reject(new Error('Timeout: el análisis tardó más de 5 minutos. Intentá con una canción más corta.'))
    }, 300000)

    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
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
        reject(new Error('Python no está instalado o no está en el PATH. Instala Python 3.8+ para continuar.'))
      } else {
        reject(err)
      }
    })

    child.on('close', (code: number) => {
      clearTimeout(timeout)
      if (code !== 0 && !stdout) {
        reject(new Error(stderr || `El script Python terminó con código ${code}`))
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

import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs/promises'
import os from 'os'

export async function POST(req: NextRequest) {
  let formData: FormData
  try {
    formData = await req.formData()
  } catch {
    return NextResponse.json({ error: 'Formulario inválido' }, { status: 400 })
  }

  const file = formData.get('audio') as File | null
  if (!file) {
    return NextResponse.json({ error: 'No se recibió ningún archivo de audio' }, { status: 400 })
  }

  const ext = file.name.split('.').pop()?.toLowerCase() || 'mp3'
  const allowed = ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'weba', 'webm']
  if (!allowed.includes(ext)) {
    return NextResponse.json({ error: `Formato no soportado. Usá: ${allowed.join(', ')}` }, { status: 400 })
  }

  const tmpPath = path.join(os.tmpdir(), `chordlens-${Date.now()}.${ext}`)

  try {
    const buffer = Buffer.from(await file.arrayBuffer())
    await fs.writeFile(tmpPath, buffer)

    const scriptPath = path.join(process.cwd(), 'scripts', 'analyze.py')

    const result = await new Promise<string>((resolve, reject) => {
      const timeout = setTimeout(() => {
        child.kill()
        reject(new Error('Timeout: el análisis tardó más de 5 minutos. Intentá con una canción más corta.'))
      }, 300000)

      const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
      const child = spawn(pythonCmd, [scriptPath, '--file', tmpPath], {
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      let stdout = ''
      let stderr = ''

      child.stdout.on('data', (data: Buffer) => { stdout += data.toString() })
      child.stderr.on('data', (data: Buffer) => { stderr += data.toString() })

      child.on('error', (err: NodeJS.ErrnoException) => {
        clearTimeout(timeout)
        if (err.code === 'ENOENT') {
          reject(new Error('Python no está instalado o no está en el PATH.'))
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

    const parsed = JSON.parse(result)
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error }, { status: 500 })
    }
    return NextResponse.json(parsed)
  } finally {
    await fs.unlink(tmpPath).catch(() => {})
  }
}

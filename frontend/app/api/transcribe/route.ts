import { NextRequest, NextResponse } from 'next/server'
import { proxyBackend } from '@/lib/backend'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    if (!body || typeof body.url !== 'string' || typeof body.start !== 'number' || typeof body.end !== 'number') {
      return NextResponse.json({ error: 'URL, inicio y fin requeridos' }, { status: 400 })
    }
    return proxyBackend('/transcribe', {
      method: 'POST', body: JSON.stringify({ url: body.url, start: body.start, end: body.end }),
    })
  } catch {
    return NextResponse.json({ error: 'Solicitud inválida' }, { status: 400 })
  }
}

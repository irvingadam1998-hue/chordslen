import { NextRequest, NextResponse } from 'next/server'
import { proxyBackend } from '@/lib/backend'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    if (!body || typeof body.url !== 'string') {
      return NextResponse.json({ error: 'URL requerida' }, { status: 400 })
    }
    return proxyBackend('/analyze', { method: 'POST', body: JSON.stringify({ url: body.url }) })
  } catch {
    return NextResponse.json({ error: 'Solicitud inválida' }, { status: 400 })
  }
}

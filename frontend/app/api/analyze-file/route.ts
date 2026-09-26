import { NextRequest, NextResponse } from 'next/server'
import { backendConfig, backendFetch } from '@/lib/backend'

// Only a small upload ticket travels through Next.js; audio goes straight to the worker.
export async function POST(req: NextRequest) {
  try {
    const response = await backendFetch('/upload-ticket', {
      method: 'POST', body: JSON.stringify({ origin: req.nextUrl.origin }),
    })
    const data = await response.json()
    if (!response.ok) return NextResponse.json(data, { status: response.status })
    const publicUrl = (process.env.PUBLIC_WORKER_URL || backendConfig().url).replace(/\/$/, '')
    return NextResponse.json({
      uploadUrl: `${publicUrl}/analyze-file`, token: data.token, maxBytes: data.max_bytes,
    })
  } catch (error) {
    console.error('[upload-ticket]', error instanceof Error ? error.message : 'Request failed')
    return NextResponse.json({ error: 'No se pudo iniciar la subida. Intenta de nuevo en unos segundos.' }, { status: 502 })
  }
}

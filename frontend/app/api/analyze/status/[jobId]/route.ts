import { NextRequest, NextResponse } from 'next/server'

const FALLBACK_BACKEND_URL = 'https://chordslen-production.up.railway.app'
const FALLBACK_BACKEND_KEY = '7f9a8d2c1b4e5f6a8c9d0e1f2a3b4c5d'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params

  const backendUrl = (
    process.env.FLASK_API_URL ||
    process.env.REMOTE_EXTRACTOR_URL ||
    FALLBACK_BACKEND_URL
  ).replace(/\/$/, '')

  const backendKey =
    process.env.FLASK_API_KEY ||
    process.env.REMOTE_EXTRACTOR_TOKEN ||
    process.env.API_KEY ||
    FALLBACK_BACKEND_KEY

  try {
    const res = await fetch(`${backendUrl}/status/${jobId}`, {
      method: 'GET',
      headers: {
        ...(backendKey ? { 'x-api-key': backendKey } : {}),
      },
      cache: 'no-store',
    })

    const data = await res.json()
    if (!res.ok) {
      return NextResponse.json(
        { error: data.error || 'Error al consultar el estado del trabajo' },
        { status: res.status || 500 }
      )
    }

    return NextResponse.json(data)
  } catch (err) {
    const message =
      err instanceof Error ? err.message : 'No se pudo consultar el estado'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

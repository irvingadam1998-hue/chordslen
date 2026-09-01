import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params

  const backendUrl = (
    process.env.FLASK_API_URL ||
    process.env.REMOTE_EXTRACTOR_URL ||
    ''
  ).replace(/\/$/, '')

  const backendKey =
    process.env.FLASK_API_KEY ||
    process.env.REMOTE_EXTRACTOR_TOKEN ||
    process.env.API_KEY ||
    ''

  if (!backendUrl) {
    return NextResponse.json(
      { error: 'Backend de transcripción no configurado (FLASK_API_URL / REMOTE_EXTRACTOR_URL)' },
      { status: 500 }
    )
  }

  try {
    const res = await fetch(`${backendUrl}/transcribe/status/${jobId}`, {
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

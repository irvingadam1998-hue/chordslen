import { NextResponse } from 'next/server'

export function backendConfig() {
  const url = (process.env.FLASK_API_URL || process.env.REMOTE_EXTRACTOR_URL ||
    (process.env.NODE_ENV === 'development' ? 'http://localhost:5002' : '')).replace(/\/$/, '')
  if (!url) throw new Error('Configura FLASK_API_URL para conectar el servidor de análisis.')
  const key = process.env.FLASK_API_KEY || process.env.REMOTE_EXTRACTOR_TOKEN || ''
  return { url, key }
}

export async function backendFetch(path: string, init: RequestInit = {}) {
  const { url, key } = backendConfig()
  return fetch(`${url}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { 'x-api-key': key } : {}),
      ...init.headers,
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(30000),
  })
}

export async function proxyBackend(path: string, init: RequestInit = {}) {
  try {
    const response = await backendFetch(path, init)
    const data = await response.json()
    const headers: Record<string, string> = {}
    const retryAfter = response.headers.get('Retry-After')
    if (retryAfter) headers['Retry-After'] = retryAfter
    return NextResponse.json(
      { ...data, ...(data.job_id ? { jobId: data.job_id } : {}) },
      { status: response.status, headers },
    )
  } catch (error) {
    console.error('[backend]', error instanceof Error ? error.message : 'Request failed')
    return NextResponse.json(
      { error: 'No se pudo contactar el servidor de análisis. Intenta de nuevo en unos segundos.' },
      { status: 502 },
    )
  }
}

import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  let body: { artist?: string; title?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'JSON inválido' }, { status: 400 })
  }

  const { artist, title } = body
  if (!artist || !title) {
    return NextResponse.json({ error: 'artist y title requeridos' }, { status: 400 })
  }

  try {
    const encodedArtist = encodeURIComponent(artist)
    const encodedTitle = encodeURIComponent(title)
    const res = await fetch(`https://api.lyrics.ovh/v1/${encodedArtist}/${encodedTitle}`, {
      signal: AbortSignal.timeout(8000),
    })

    if (!res.ok) {
      return NextResponse.json({ error: 'Letra no encontrada' }, { status: 404 })
    }

    const data = await res.json()
    return NextResponse.json({ lyrics: data.lyrics || '' })
  } catch {
    return NextResponse.json({ error: 'No se pudo obtener la letra' }, { status: 500 })
  }
}

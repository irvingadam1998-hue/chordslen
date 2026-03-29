# Remote Extractor Contract

ChordLens ahora puede delegar la extracción de audio de YouTube a un servicio remoto desplegado.

Configura estas variables en Railway o en tu VPS:

- `REMOTE_EXTRACTOR_URL`
- `REMOTE_EXTRACTOR_TOKEN` opcional
- `REMOTE_EXTRACTOR_AUDIO_PATH` opcional, por defecto `/audio`
- `REMOTE_EXTRACTOR_FRAGMENT_PATH` opcional, por defecto `/fragment`

## Endpoint `POST /audio`

Body JSON:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "format": "wav"
}
```

Respuesta aceptada:

```json
{
  "success": true,
  "audio_url": "https://extractor.example/audio/file.wav",
  "title": "Song title",
  "artist": "Artist name",
  "ext": "wav"
}
```

También se acepta `download_url` o `url` en lugar de `audio_url`.

Si el servicio no quiere exponer un archivo descargable, también puede responder:

```json
{
  "success": true,
  "audio_base64": "<base64>",
  "title": "Song title",
  "artist": "Artist name",
  "ext": "wav"
}
```

## Endpoint `POST /fragment`

Body JSON:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "start": 30,
  "end": 45,
  "format": "wav"
}
```

Respuesta aceptada:

```json
{
  "success": true,
  "audio_url": "https://extractor.example/audio/fragment.wav",
  "ext": "wav"
}
```

O base64:

```json
{
  "success": true,
  "audio_base64": "<base64>",
  "ext": "wav"
}
```

## Notas

- Si `REMOTE_EXTRACTOR_URL` está configurado, ChordLens lo intenta antes que Invidious, Cobalt, Piped y `yt-dlp`.
- Si el extractor remoto falla, el flujo actual sigue con los fallbacks existentes.
- Esto no garantiza 100% de disponibilidad, pero te permite mover la parte más frágil a una infraestructura separada del frontend en Railway.

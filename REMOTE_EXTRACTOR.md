# Contrato HTTP del worker ChordLens

Todos los endpoints salvo `/health` requieren `x-api-key: API_KEY` cuando el
worker tiene configurada esa clave. La subida desde navegador usa su propio
ticket temporal de un solo uso.

## Análisis y transcripción

- `POST /analyze`: `{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }`
- `POST /transcribe`: `{ "url": "...", "start": 30, "end": 45 }`
- `GET /status/<job_id>` y `GET /transcribe/status/<job_id>`: consultar resultado.

Un trabajo pendiente responde HTTP 202 con `job_id` y `status: "processing"`.
Al finalizar responde HTTP 200, `status: "done"`, `success: true` y los datos.
Un trabajo fallido responde HTTP 200, `status: "failed"`, `success: false` y
`error`; los errores de YouTube también incluyen `code`, `fallback: "upload"` y
`retry_after`. Es necesario comprobar `success`/`status`, no solo HTTP.

Los resultados no se borran al consultarlos. Solicitudes del mismo video o del
mismo fragmento reutilizan el trabajo pendiente o exitoso durante su TTL. Si no
queda capacidad para un trabajo diferente, devuelve HTTP 429 y `Retry-After`.

## Archivos

1. El servidor Next.js pide `POST /upload-ticket` con API key y
   `{ "origin": "https://tu-frontend.example" }`.
2. Recibe `token`, `max_bytes`, `expires_in` y entrega el ticket al navegador.
3. El navegador envía multipart `audio` a `POST /analyze-file` con
   `X-Upload-Token: token`. CORS se limita al origen autorizado.
4. Consulta `/status/<job_id>` a través de Next.js.

El ticket dura 600 segundos y solo se puede usar una vez. También se permite
`POST /analyze-file` con API key para clientes de servidor. El archivo temporal
se elimina al finalizar el procesamiento, incluso si falla.

## Extracción sin análisis

- `POST /audio`: `{ "url": "..." }`.
- `POST /fragment`: `{ "url": "...", "start": 30, "end": 45 }`, máximo 60 s.
- `GET /files/<id>`: descarga con la misma API key; expira según el TTL.

`/audio` y `/fragment` devuelven `success`, `audio_url`, `ext` y, si están
disponibles, `title`/`artist`. La pausa de YouTube se comparte con los análisis.
No se realizan peticiones adicionales solo para los metadatos ni se contactan
proveedores de descarga externos.

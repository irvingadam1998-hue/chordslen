# ChordLens

Analiza acordes de una canción de YouTube o de un archivo de audio, los muestra
sincronizados con la reproducción y permite adaptar las posiciones al capo.

- `frontend/`: Next.js 16, React y TypeScript.
- `backend/extractor_server/`: servidor Flask con trabajos asíncronos, resultados
  reutilizables, límites de concurrencia y subida directa de archivos.
- `backend/scripts/`: análisis con librosa, transcripción y descarga directa de
  YouTube mediante una configuración compartida de yt-dlp.

## Desarrollo

Requisitos: Python 3.11+, Node.js 22+ y FFmpeg en PATH.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/extractor_server/app.py
```

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

En desarrollo Next.js usa `http://localhost:5002` por defecto. Si configuras
`API_KEY` en el backend, añade `FLASK_API_KEY` con el mismo valor en
`frontend/.env.local`. Abre `http://localhost:3000`.

También puedes ejecutar `docker compose up --build` desde la raíz. El worker y
el frontend se construyen con todos sus archivos. Para acceso desde otro equipo,
configura `PUBLIC_WORKER_URL` con la dirección pública del worker.

## Verificación y despliegue

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

Consulta [DEPLOYMENT.md](DEPLOYMENT.md) para publicar en Render sin proveedores
de descarga de pago. Ninguna configuración puede garantizar que YouTube acepte
siempre la IP del servidor; el análisis de archivos no depende de YouTube.

- [Frontend en Vercel: paso a paso](DESPLIEGUE_VERCEL.md).
- [Exportar cookies y saber cuándo renovarlas](COOKIES_YOUTUBE.md).

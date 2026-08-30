# Deploy recomendado (gratis / barato)

## 1) Frontend: Vercel

- Importa este repo en Vercel
- Usa la rama principal
- deja la app como Next.js
- configura las variables:

```env
FLASK_API_URL=https://your-worker.onrender.com
FLASK_API_KEY=change-me
REMOTE_EXTRACTOR_URL=https://your-worker.onrender.com
REMOTE_EXTRACTOR_TOKEN=change-me
NEXT_PUBLIC_API_URL=https://your-frontend.vercel.app
```

## 2) Worker pesado: Render

- Crea un nuevo Web Service en Render
- selecciona `Render Blueprint` y usa el archivo `render.yaml` del repo
- o crea un Python service con esta carpeta:
  - `backend/extractor_server`
- comando de arranque:

```bash
python app.py
```

Variables requeridas:

```env
PORT=5002
API_KEY=change-me
MAX_CONCURRENT_JOBS=1
JOB_TTL_SECONDS=300
EXTRACTOR_FILE_TTL_SECONDS=900
YTDLP_PLAYER_CLIENTS=android,ios,tv_embedded
YTDLP_PO_TOKEN=
YTDLP_PO_TOKEN_CLIENT=android.gvs
YOUTUBE_COOKIES_B64=
YOUTUBE_COOKIES_FILE=
```

## 3) Job queue

La arquitectura actual usa SQLite en el worker para evitar que el job quede solo en RAM. Eso ya sirve para un demo y para una etapa de prueba.

Para producción más robusta, conviene moverlo a Redis/Firestore.

## 4) Qué evita el bloqueo de YouTube

La app web no descarga audio directamente. El worker remoto hace la descarga y el análisis. Esto evita que Railway/Vercel vean la IP del extractor y que YouTube detecte tráfico de bot.

## 5) Si YouTube sigue bloqueando

Añade cookies válidas:

```env
YOUTUBE_COOKIES_B64=<base64 del cookies.txt>
```

o usa un extractor remoto adicional.

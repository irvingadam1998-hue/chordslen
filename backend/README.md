# Backend extractor

Este servicio queda separado y hace la extracción de audio de YouTube.

## Variables de entorno

```env
PORT=5002
API_KEY=secret123
YTDLP_PLAYER_CLIENTS=android,ios,tv_embedded
# opcional si quieres usar cookies reales en este backend
# YOUTUBE_COOKIES_FILE=/app/cookies.txt
```

## Recomendación de despliegue

- Deploy en un VPS o servicio separado.
- Este backend es el que procesa la URL de YouTube.
- El frontend solo le pide audio a este servicio.

## Endpoints esperados

- GET /health
- POST /audio
- POST /fragment

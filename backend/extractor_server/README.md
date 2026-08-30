# Extractor Server

Servicio remoto para que `ChordLens` pida audio de YouTube desde otra infraestructura.

## Variables

- `API_KEY` opcional
- `PORT` opcional, por defecto `5002`
- `YOUTUBE_COOKIES_B64` opcional
- `YOUTUBE_COOKIES_FILE` opcional
- `YTDLP_PO_TOKEN` opcional
- `YTDLP_PO_TOKEN_CLIENT` opcional, por defecto `android.gvs`
- `YTDLP_PLAYER_CLIENTS` opcional, por ejemplo `android,ios,tv_embedded`
- `EXTRACTOR_FILE_TTL_SECONDS` opcional, por defecto `900`

## Endpoints

- `GET /health`
- `POST /audio`
- `POST /fragment`
- `GET /files/<id>`

## Run local

```bash
pip install -r extractor_server/requirements.txt
API_KEY=secret python extractor_server/app.py
```

## Deploy

Despliega este servicio separado del frontend, idealmente en un VPS o proveedor distinto de Railway. Luego configura en tu app principal:

- `REMOTE_EXTRACTOR_URL=https://tu-extractor.example.com`
- `REMOTE_EXTRACTOR_TOKEN=secret`

Si el extractor necesita cookies o PO token, configúralos aquí, no en el frontend.

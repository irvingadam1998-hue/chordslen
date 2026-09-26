# Worker ChordLens

Servidor Flask para descarga directa, análisis y transcripción. Usa una sola
implementación de yt-dlp, un proceso Gunicorn, SQLite y trabajos en hilos.

Desde la raíz del repositorio:

```bash
pip install -r backend/requirements.txt
python backend/extractor_server/app.py
```

Para Docker:

```bash
docker build -f backend/extractor_server/Dockerfile -t chordlens-worker .
```

Configuración y límites: [DEPLOYMENT.md](../../DEPLOYMENT.md).
Endpoints: [REMOTE_EXTRACTOR.md](../../REMOTE_EXTRACTOR.md).

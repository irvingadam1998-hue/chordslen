# Backend ChordLens

El servicio actual es `extractor_server/app.py`. Hace la descarga directa de
YouTube, el análisis de acordes, la transcripción y el análisis de archivos.
`flask_server/` es una implementación anterior; no se usa para el despliegue.

Desde la raíz del repositorio:

```bash
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/extractor_server/app.py
```

Requiere Node.js 22+ y FFmpeg. Para el contenedor, usa contexto de construcción
en la raíz del repositorio y `backend/extractor_server/Dockerfile`.

Consulta [DEPLOYMENT.md](../DEPLOYMENT.md) y el [contrato HTTP](../REMOTE_EXTRACTOR.md).

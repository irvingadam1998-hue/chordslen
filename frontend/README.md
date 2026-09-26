# Frontend

Next.js sirve la UI y envía los trabajos al worker Python. No ejecuta Python ni
descarga audio de YouTube. La subida de audio se autoriza con un ticket temporal
y va directamente del navegador al worker.

```env
FLASK_API_URL=http://localhost:5002
FLASK_API_KEY=tu-clave-del-worker
PUBLIC_WORKER_URL=http://localhost:5002
```

`PUBLIC_WORKER_URL` debe ser accesible desde el navegador (HTTPS en producción).
La API key nunca se entrega al navegador. En desarrollo, la dirección del worker
por defecto es `http://localhost:5002`.

```bash
npm ci
npm run dev
```

Ver [despliegue](../DEPLOYMENT.md).

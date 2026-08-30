# Frontend

Este servicio queda separado y solo se encarga de la UI.

## Variables de entorno

```env
NEXT_PUBLIC_API_URL=http://localhost:5002
REMOTE_EXTRACTOR_URL=http://localhost:5002
REMOTE_EXTRACTOR_TOKEN=secret123
```

## Recomendación de despliegue

- Deploy en Railway, Vercel o un host web.
- No debe descargar audio de YouTube directamente.
- Solo debe llamar al backend extractor.

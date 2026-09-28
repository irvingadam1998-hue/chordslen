# Arranque local con la red neuronal

Modelo: `experiments/joint-solo-exclude/candidate.pt`, ya promovido y con
`switch_cost` 48. Todos los comandos se ejecutan desde la raíz del proyecto.

Necesitas **dos terminales**: una para el backend y otra para el frontend.

## Terminal 1 — Backend (puerto 5002)

```bash
cd ~/Documentos/PERSONAL/chordslen

API_KEY=clave-local \
ACR_ENGINE=neural \
ACR_MODE=accurate \
ACR_VOCABULARY=triads \
ACR_MODEL_PATH="$PWD/experiments/joint-solo-exclude/candidate.pt" \
.venv/bin/python backend/extractor_server/app.py
```

- `ACR_MODE=accurate` es obligatorio: el modelo se promovió en ese modo y
  rechaza `fast`.
- `ACR_VOCABULARY=triads` junta las séptimas con su tríada (Am7→Am, Fmaj7→F,
  G7→G), como en la mayoría de los cancioneros. Si quieres ver las séptimas,
  usa `full`.
- `API_KEY` puede ser cualquier texto, pero tiene que coincidir con
  `FLASK_API_KEY` del frontend.
- Deja esta terminal abierta. El backend queda escuchando en `http://localhost:5002`.

## Terminal 2 — Frontend (puerto 3000)

**Primera vez:** crea `frontend/.env.local`. Tiene prioridad sobre `frontend/.env`,
que puede apuntar a un servidor remoto.

```bash
cd ~/Documentos/PERSONAL/chordslen/frontend
cat > .env.local <<'EOF'
FLASK_API_URL=http://localhost:5002
FLASK_API_KEY=clave-local
PUBLIC_WORKER_URL=http://localhost:5002
EOF
```

**Instalar dependencias** (solo la primera vez o si cambia `package-lock.json`):

```bash
npm ci
```

> Esto ejecuta los scripts `preinstall`/`postinstall` de las dependencias. Si es
> una instalación nueva, revisa antes con `npm audit` y hazla en una máquina sin
> tokens de CI/CD ni credenciales de producción.

**Arrancar:**

```bash
npm run dev
```

Abre <http://localhost:3000>.

## Comprobar que usa la red neuronal

Analiza una canción. El resultado JSON trae `"engine": "neural"`.

Si ves `"engine": "current"` y el aviso `ACR_NEURAL_FALLBACK`, el modelo no se
pudo cargar. Mira el error `[acr] neural fallback: ...` en la terminal 1. Las
causas habituales son:

- una ruta mal escrita en `ACR_MODEL_PATH`;
- un `ACR_MODE` distinto de `accurate`;
- que falte torch en `.venv` (`.venv/bin/pip list | grep torch`).

## Volver al detector clásico

Detén el backend con Ctrl+C y arráncalo sin las variables `ACR_*`:

```bash
API_KEY=clave-local .venv/bin/python backend/extractor_server/app.py
```

## Limitaciones

- El modelo se validó con guitarra sola (GuitarSet). En canciones con voz,
  batería y bajo no se ha medido, así que compara con el detector clásico en
  algunas canciones reales.
- `docker compose` **no** usa este modelo: la imagen no instala torch ni copia
  el checkpoint.

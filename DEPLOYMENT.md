# Desplegar ChordLens sin proveedores de descarga de pago

El backend descarga directamente de YouTube con `yt-dlp`. No utiliza RapidAPI,
Cobalt, Invidious, proxies de pago ni un servicio de descarga externo. La web
solo envía trabajos al backend de ChordLens.

## Backend en Render

1. Sube los cambios del repositorio a GitHub.
2. En Render crea un **Blueprint** desde este repositorio usando `render.yaml`.
3. El servicio usa **Docker**, contexto `.` y Dockerfile
   `backend/extractor_server/Dockerfile`. No establezcas `backend/extractor_server`
   como Root Directory: el contenedor necesita también `backend/scripts`.
4. El Blueprint solicita el plan `free`, un único proceso y genera `API_KEY`.
5. Comprueba que `https://TU-WORKER.onrender.com/health` responde `ok: true`.

El contenedor instala Python, FFmpeg, Node.js 22, `yt-dlp[default]` (incluido EJS)
y las dependencias del análisis. Se mantiene **un proceso Gunicorn** con varios
hilos: los trabajos y la pausa de YouTube se coordinan dentro de ese proceso.
No aumentes `--workers` sin cambiar esa coordinación.

Si reutilizas un servicio anterior, elimina el valor forzado
`YTDLP_PLAYER_CLIENTS=android,ios,tv_embedded` y los tokens antiguos. Deja que la
versión actualizada de yt-dlp seleccione sus clientes predeterminados.

## Frontend

Despliega `frontend` como proyecto Next.js. En sus variables configura:

```env
FLASK_API_URL=https://TU-WORKER.onrender.com
FLASK_API_KEY=EL_API_KEY_DEL_WORKER
PUBLIC_WORKER_URL=https://TU-WORKER.onrender.com
```

`FLASK_API_KEY` permanece en el servidor de Next.js. No uses un prefijo
`NEXT_PUBLIC_` para esa clave. `PUBLIC_WORKER_URL` es la dirección accesible desde
el navegador; puede diferir de `FLASK_API_URL` si hay una red interna.

La subida solicita una autorización de un solo uso y envía el archivo directamente
al worker. Esto evita el límite de 4.5 MB de las funciones de Vercel. El límite
del worker es 50 MB, configurable con `MAX_UPLOAD_MB`. Las autorizaciones duran
10 minutos, están asociadas al origen de la web y nunca incluyen la API key.

## Configuración del worker

| Variable | Predeterminado | Uso |
| --- | --- | --- |
| `API_KEY` | vacío en local | Secreto compartido con el frontend; obligatorio en despliegues públicos |
| `MAX_CONCURRENT_JOBS` | `1` | Límite de análisis simultáneos |
| `JOB_TTL_SECONDS` | `3600` | Conservación y reutilización de resultados |
| `YOUTUBE_MIN_INTERVAL_SECONDS` | `5` | Separación mínima entre descargas |
| `YOUTUBE_COOLDOWN_SECONDS` | `900` | Pausa tras un rechazo por bots/403/429 |
| `MAX_UPLOAD_MB` | `50` | Tamaño máximo del archivo subido |
| `EXTRACTOR_FILE_TTL_SECONDS` | `900` | Conservación de archivos de `/audio` y `/fragment` |
| `YTDLP_NODE_PATH` | Node en PATH | Ruta opcional al ejecutable Node.js 22+ |
| `YOUTUBE_COOKIES_FILE` | vacío | Archivo Netscape de cookies, opcional y solo en el worker |
| `YOUTUBE_COOKIES_B64` | vacío | El mismo archivo codificado en base64, como secreto del worker |

Se conserva compatibilidad con `REMOTE_EXTRACTOR_URL` y `REMOTE_EXTRACTOR_TOKEN`
en el frontend, aunque se recomienda usar los nombres `FLASK_API_*`.

## Cookies y bloqueos

No hace falta iniciar sesión en Gmail para analizar videos públicos. Si un video
necesita autenticación y tienes acceso a él, el worker admite cookies de YouTube.
Se copian a un archivo temporal privado por descarga y se eliminan al terminar.
No subas cookies al repositorio ni al frontend. Una sesión iniciada no garantiza
eliminar un bloqueo de la IP; las cookies también caducan y su uso puede afectar
la cuenta. La guía oficial de yt-dlp explica la exportación y sus limitaciones:
https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies

No se instala un generador de PO tokens ni se fuerza un token estático. Los tokens
pueden estar ligados a un video y caducar; una variable fija no es una solución
permanente. Los ajustes avanzados `YTDLP_PLAYER_CLIENTS`, `YTDLP_PO_TOKEN` y
`YTDLP_PO_TOKEN_CLIENT` siguen disponibles para configuración explícita.

Cuando aparece un rechazo, se pausa YouTube y la interfaz permite continuar con
un archivo local. Los resultados existentes siguen disponibles durante la pausa.
Los errores de red, configuración y videos privados no se anuncian como una
solicitud de cookies.

## Verificación

```bash
python -m unittest discover -s backend/tests -v
python backend/scripts/check_youtube.py 'URL_DE_UN_VIDEO_PUBLICO_CORTO'
cd frontend
npm run build
```

El diagnóstico descarga una vez, devuelve tamaño/versión o un error clasificado
y elimina el audio temporal. Debe ejecutarse también desde el servidor desplegado:
que funcione desde una computadora no demuestra que YouTube acepte la IP de Render.

Para actualizar los componentes de YouTube, reconstruye sin caché de capas de pip
o instala `pip install --upgrade 'yt-dlp[default]'` en tu entorno local.

## Límites del plan gratuito

No se promete disponibilidad permanente en Render Free: el servicio puede dormirse,
el disco es efímero y la memoria es limitada. SQLite evita perder resultados al
reiniciar solo el proceso si el archivo sigue presente; no persiste a través de
reemplazos del disco. Mantén un solo análisis simultáneo y revisa memoria/logs con
canciones reales. El cálculo de características armónicas trabaja en bloques de
10 segundos con solapamiento para limitar sus matrices temporales, conservando
la línea de tiempo. No se han contratado recursos de pago.

Cambiar de hosting, añadir cookies o actualizar yt-dlp no garantiza que YouTube
nunca bloquee solicitudes. La aceptación de la IP debe verificarse en el despliegue.

Fuentes: [EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS),
[YouTube](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube),
[PO tokens](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide),
[Render Free](https://render.com/docs/free),
[Vercel: tamaño de solicitudes](https://vercel.com/docs/errors/function_payload_too_large).

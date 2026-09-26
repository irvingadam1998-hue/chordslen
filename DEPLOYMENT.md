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

Paso a paso en [DESPLIEGUE_VERCEL.md](DESPLIEGUE_VERCEL.md).

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

Exportación, renovación y significado de los nuevos avisos:
[COOKIES_YOUTUBE.md](COOKIES_YOUTUBE.md).

Los videos públicos pueden funcionar sin iniciar sesión, pero YouTube puede
exigir autenticación a determinadas sesiones o servidores. El worker admite
cookies de YouTube para probar una sesión autenticada.
Se copian a un archivo temporal privado por descarga y se eliminan al terminar.
No subas cookies al repositorio ni al frontend. Una sesión iniciada no garantiza
eliminar un bloqueo de la IP; las cookies también caducan y su uso puede afectar
la cuenta. La guía oficial de yt-dlp explica la exportación y sus limitaciones:
https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies

### Si Render muestra "Sign in to confirm you’re not a bot"

La descarga del mismo video desde otra computadora solo confirma que ese entorno
puede obtenerlo. No demuestra que la sesión o la IP de Render sea aceptada.
El soporte de cookies ya existe: esta prueba no necesita cambios de código.

1. En una ventana de incógnito, inicia sesión en YouTube con una cuenta destinada
   a esta aplicación. Según yt-dlp, usar una cuenta para descargar puede ocasionar
   restricciones; evita exponer tu cuenta principal.
2. En esa misma pestaña abre `https://www.youtube.com/robots.txt`. Exporta solo
   las cookies de `youtube.com` en formato Netscape a `cookies.txt`, siguiendo la
   guía oficial enlazada arriba, y cierra la ventana de incógnito. La guía explica
   qué extensiones permiten exportar esa sesión privada. No uses la exportación
   de todas las cookies del navegador: puede incluir sesiones de otros sitios.
3. En el **servicio backend de Render**, abre **Environment → Secret Files →
   Add Secret File**. Usa el nombre `cookies.txt` y pega allí su contenido.
4. En **Environment Variables**, configura:

   ```env
   YOUTUBE_COOKIES_FILE=/etc/secrets/cookies.txt
   ```

   Elimina `YOUTUBE_COOKIES_B64` si estaba configurada: tiene prioridad sobre el
   archivo y podría seguir usando cookies antiguas. Deja sin configurar
   `YTDLP_PLAYER_CLIENTS` y `YTDLP_PO_TOKEN` para esta prueba; no fuerces clientes
   antiguos que no admiten cookies de cuenta.
5. Guarda los cambios y aplica tú el nuevo despliegue. Render monta los archivos
   secretos en `/etc/secrets`. El proceso nuevo empieza sin la pausa anterior;
   si mantienes el proceso en ejecución, respeta la pausa de 15 minutos tras el
   rechazo antes de volver a probar.
6. Prueba una vez el mismo video. Si aparecen avisos de cookies caducadas o
   rotadas, vuelve a exportar la sesión. Si el rechazo continúa con cookies
   válidas, autenticar la cuenta no ha sido suficiente; no se puede prometer una
   solución permanente mediante cookies en esa IP de Render.

No pegues el contenido de las cookies en chats, incidencias ni logs: da acceso a
la sesión. Tampoco lo incluyas en el frontend ni en Git. Los archivos secretos
de Render se describen en su [documentación oficial](https://render.com/docs/configure-environment-variables#secret-files).

No se instala un generador de PO tokens ni se fuerza un token estático. Los tokens
pueden estar ligados a un video y caducar; una variable fija no es una solución
permanente. Los ajustes avanzados `YTDLP_PLAYER_CLIENTS`, `YTDLP_PO_TOKEN` y
`YTDLP_PO_TOKEN_CLIENT` siguen disponibles para configuración explícita.

Cuando aparece un rechazo, se pausa YouTube y la interfaz permite continuar con
un archivo local. Los resultados existentes siguen disponibles durante la pausa.
Los avisos de cookies distinguen vencimiento por fecha, invalidación de sesión,
rechazo con cookies configuradas y archivo mal configurado. Los errores de red,
otros errores de configuración y videos privados no se anuncian como vencimiento.

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

## Rendimiento y diagnóstico de esperas

El cálculo de acordes se ejecuta en el backend de Render. Vercel envía el trabajo
y consulta su resultado. En la respuesta final y en los logs `[analyze] timings=...`
se incluyen estos tiempos, en segundos:

| Campo | Qué mide |
| --- | --- |
| `download_seconds` | Preparación y descarga de YouTube, incluida la conversión de audio y cualquier espera del descargador. |
| `load_seconds` | Lectura y conversión del audio para el análisis. |
| `features_seconds` | Separación armónica y cálculo de características musicales. |
| `chords_seconds` | Identificación de acordes y construcción de la línea de tiempo. |
| `analysis_seconds` | Análisis completo, incluida la carga inicial de sus librerías. |
| `total_seconds` | Descarga más análisis en una solicitud de YouTube. |

Estos tiempos comienzan dentro del trabajo: no incluyen el arranque de Render
antes de atenderlo, la subida desde el navegador ni la espera de la siguiente
consulta de estado. Un resultado reutilizado conserva los tiempos de su análisis
original. `/health` por sí solo no mide el procesamiento de una canción.

La optimización del análisis reutiliza las plantillas normalizadas de acordes y
filtra cada eje del espectrograma con el filtro unidimensional de SciPy, conservando
el tratamiento de bordes y la separación armónica. Se mantiene la frecuencia de
muestreo, los bloques de 10 segundos y la resolución temporal del análisis.

En una prueba local con audio sintético de 180 segundos, la primera ejecución
pasó de **39.99 s a 18.22 s**. La repetición medida con cProfile pasó de **34.53 s
a 15.47 s**. Coincidieron los 30 eventos de acordes, sus tiempos y la tonalidad.
Estas cifras describen esa prueba local; no incluyen YouTube ni garantizan el
mismo tiempo en Render. Para aplicar la optimización, publica el backend con
`backend/requirements.txt` actualizado (SciPy 1.17+).

Si solo la primera canción tarda más, considera el arranque del servicio:
[Render Free](https://render.com/docs/free#spinning-down-on-idle) se suspende
tras 15 minutos sin tráfico y su reactivación tarda aproximadamente un minuto.
Si las siguientes también tardan, los campos anteriores permiten distinguir
descarga de cálculo sin cambiar de plan a ciegas.

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

# Desplegar el frontend de ChordLens en Vercel

Vercel aloja la web Next.js y sus rutas API. El backend de Python, FFmpeg,
yt-dlp y las cookies permanecen en Render. Los siguientes pasos los ejecutas tú
cuando quieras publicar los cambios locales.

## 1. Preparar Render

Si eliminaste el backend anterior, créalo primero siguiendo
[DEPLOYMENT.md](DEPLOYMENT.md#backend-en-render). Necesitas un backend activo
para analizar canciones, aunque la web de Vercel ya abra correctamente.

1. En Render copia la URL pública HTTPS del servicio, por ejemplo
   `https://TU-WORKER.onrender.com`.
2. Abre esa URL seguida de `/health` y comprueba que responde `"ok": true`.
3. En **Environment**, localiza `API_KEY`. El Blueprint la genera; si creaste
   el servicio manualmente, configura una clave secreta. Usarás exactamente
   el mismo valor en Vercel como `FLASK_API_KEY`.
4. Configura las cookies en Render siguiendo [COOKIES_YOUTUBE.md](COOKIES_YOUTUBE.md).

## 2. Importar el frontend

1. Revisa y sube tú los cambios a tu repositorio de GitHub.
2. En [Vercel](https://vercel.com/new), elige **Add New → Project** e importa
   el repositorio `chordslen` desde la cuenta de GitHub que lo contiene.
3. Configura estos valores:

   | Ajuste | Valor |
   | --- | --- |
   | Framework Preset | `Next.js` |
   | Root Directory | `frontend` |
   | Build Command | `npm run build` |
   | Install Command | Predeterminado de Vercel para npm |
   | Output Directory | Predeterminado de Next.js, sin sobrescribir |
   | Node.js Version | `22.x` |

   Si Node.js no aparece al importar, revisa **Settings → Build and Deployment**.
   La carpeta correcta es `frontend`, porque allí están `package.json`, el lockfile
   y la aplicación. Vercel explica estos ajustes en su
   [guía de configuración del build](https://vercel.com/docs/builds/configure-a-build).

## 3. Añadir variables en Vercel

Antes del primer despliegue, abre **Environment Variables** y configura:

| Nombre | Valor de ejemplo | De dónde sale |
| --- | --- | --- |
| `FLASK_API_URL` | `https://TU-WORKER.onrender.com` | URL pública del backend, sin `/api` ni `/analyze` al final. |
| `FLASK_API_KEY` | El valor secreto de `API_KEY` | Copia exacta de la variable del backend de Render. |
| `PUBLIC_WORKER_URL` | `https://TU-WORKER.onrender.com` | URL HTTPS accesible desde el navegador para subir archivos. |

Reemplaza los ejemplos por tus valores reales, sin comillas. Selecciona
**Production**; selecciona también **Preview** si quieres que las vistas previas
usen ese backend. Ambas compartirán su capacidad de análisis.

`FLASK_API_KEY` se usa en el servidor de Next.js. Mantén ese nombre, sin añadir
`NEXT_PUBLIC_`. Las cookies (`YOUTUBE_COOKIES_FILE` o `YOUTUBE_COOKIES_B64`)
se configuran en Render, no aquí. `PUBLIC_WORKER_URL` es una URL, no un secreto.

## 4. Publicar y probar

1. Pulsa **Deploy** y espera el estado **Ready**.
2. Abre la dirección `https://TU-PROYECTO.vercel.app`.
3. Analiza un archivo de audio corto para comprobar la conexión con Render.
4. Prueba un enlace de YouTube. Si aparece **«Actualizar cookies de YouTube»**,
   sigue [la guía de renovación](COOKIES_YOUTUBE.md#4-renovación-posterior).

Si cambias variables después, entra en **Deployments**, abre el menú del
despliegue correspondiente y usa **Redeploy**. Las variables nuevas se aplican
solo a nuevos despliegues, según la
[documentación de Vercel](https://vercel.com/docs/environment-variables/managing-environment-variables).

## Problemas habituales

| Síntoma | Qué revisar |
| --- | --- |
| No detecta Next.js o no encuentra `package.json` | `Root Directory` debe ser `frontend`. |
| «Configura FLASK_API_URL» | Falta esa variable en el entorno del despliegue o falta redesplegar. |
| Error de autorización / 401 | `FLASK_API_KEY` de Vercel y `API_KEY` de Render deben coincidir. |
| «No se pudo contactar el servidor de análisis» / 502 | Comprueba URL y `/health`. Si Render estaba dormido, espera a que arranque y vuelve a intentar. |
| Abre la web pero falla al subir audio | Revisa que `PUBLIC_WORKER_URL` sea la URL pública HTTPS del backend y que esté disponible. |
| Archivo demasiado grande | El worker admite 50 MB por defecto, configurable con `MAX_UPLOAD_MB` en Render. |
| Error de cookies o verificación de bots | Revísalo en Render con [COOKIES_YOUTUBE.md](COOKIES_YOUTUBE.md); un redeploy del frontend no renueva la sesión. |

La subida de audio va directamente al backend mediante un permiso temporal;
el navegador nunca necesita la API key. No necesitas instalar Python en Vercel.

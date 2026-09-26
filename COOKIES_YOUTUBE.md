# Exportar y renovar las cookies de YouTube en Render

Las cookies permiten al backend usar una sesión de YouTube. No tienen una duración
garantizada: YouTube puede invalidarlas antes de su fecha de vencimiento. Mantener
una cuenta abierta en otra computadora no actualiza el archivo que usa Render.
La [guía de yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
explica la rotación de sesiones y advierte sobre posibles restricciones de la cuenta.

## 1. Exportar desde Chrome

1. Instala [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc),
   enlazada en la [FAQ de yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
2. Abre `chrome://extensions`, entra en **Detalles** de esa extensión y activa
   **Permitir en incógnito**.
3. Abre una ventana de incógnito (`Ctrl + Shift + N`) e inicia sesión en YouTube
   con la cuenta dedicada al proyecto.
4. En esa misma pestaña abre `https://www.youtube.com/robots.txt`. Mantén solo
   esa pestaña de incógnito abierta durante la exportación.
5. Abre la extensión y exporta **las cookies de youtube.com**, en formato
   **Netscape**, a `cookies.txt`. Evita la opción de exportar todos los sitios.
6. Cierra la ventana de incógnito sin pulsar «Cerrar sesión» en YouTube. No vuelvas
   a abrir esa sesión exportada para navegar.
7. Abre `cookies.txt` con un editor de texto. Debe comenzar por
   `# Netscape HTTP Cookie File` o `# HTTP Cookie File`, seguido de las filas de
   cookies. Un archivo con solo el encabezado no sirve.

Este procedimiento de incógnito sigue la
[exportación recomendada por yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).

## 2. Configurar el backend de Render

1. Abre **Render → tu servicio backend → Environment → Secret Files → Add Secret File**.
2. En **Filename** escribe `cookies.txt`. En **Contents** pega todo el contenido
   del archivo, conservando tabulaciones y saltos de línea.
3. En **Environment Variables** añade:

   ```env
   YOUTUBE_COOKIES_FILE=/etc/secrets/cookies.txt
   ```

4. Elimina `YOUTUBE_COOKIES_B64` si existe: esa variable tiene prioridad y podría
   hacer que se sigan usando cookies antiguas. Para empezar, deja sin configurar
   `YTDLP_PLAYER_CLIENTS` y `YTDLP_PO_TOKEN`.
5. Guarda los cambios y espera a que el despliegue del backend esté **Live**.
   Render monta el archivo en `/etc/secrets/cookies.txt` y aplica la modificación
   mediante un nuevo despliegue, según su
   [documentación de archivos secretos](https://render.com/docs/configure-environment-variables#secret-files).
6. Desde ChordLens solicita un análisis de YouTube que no esté ya en caché.

Las cookies van únicamente en el backend. No las pongas en Vercel, GitHub, chats
ni capturas. Contienen credenciales de la sesión.

## 3. Cómo saber cuándo actualizarlas

Al intentar una descarga nueva, ChordLens comprueba las fechas de las cookies de
autenticación y los avisos de yt-dlp. No basta con que alguna cookie de publicidad
haya caducado; se revisan las necesarias para iniciar sesión. Una fecha `0` o
vacía corresponde a una cookie de sesión, sin vencimiento fijo comprobable.

Cuando sea necesario, la pantalla mostrará **«Actualizar cookies de YouTube»**:

| Mensaje o código | Significado | Acción |
| --- | --- | --- |
| «Las cookies de inicio de sesión de YouTube han vencido» (`YOUTUBE_COOKIES_EXPIRED`) | Las fechas de una parte necesaria de la autenticación ya vencieron. | Exporta un archivo nuevo y reemplaza el de Render. |
| «YouTube indica que las cookies de la cuenta ya no son válidas» (`YOUTUBE_COOKIES_INVALID`) | yt-dlp recibió un aviso de sesión invalidada o rotada. | Renueva las cookies aunque sus fechas sean futuras. |
| «YouTube pide verificar la sesión aunque hay cookies configuradas» (`YOUTUBE_COOKIES_REJECTED`) | Hay cookies, pero continúa el desafío contra bots. No confirma vencimiento. | Renueva una vez; si persiste, revisa el bloqueo de la IP del servidor. |
| «No se pudo leer un archivo válido de cookies» (`YOUTUBE_COOKIES_CONFIG`) | Archivo ausente, ilegible, vacío, formato incorrecto o base64 inválido. | Revisa el archivo secreto y la variable activa. |
| «YouTube está rechazando las solicitudes desde este servidor» (`YOUTUBE_BLOCKED`) | Bloqueo general, límite de solicitudes o rechazo sin cookies configuradas. | Respeta la pausa; no presupongas que las cookies vencieron. |

Si la descarga funciona pese al aviso de cookies inválidas, el resultado se
conserva y aparece un aviso amarillo para renovar la sesión. En caso de error,
puedes continuar subiendo un archivo de audio.

El aviso aparece al usar la aplicación, **no es una alarma programada ni un
correo anticipado**. Un resultado guardado en caché no prueba las cookies otra vez.
`/health` confirma que el backend está disponible, no que YouTube acepte la sesión.

## 4. Renovación posterior

1. Repite la exportación del apartado 1 en una nueva sesión de incógnito.
2. En Render, edita el archivo secreto `cookies.txt` y sustituye todo su contenido.
3. Guarda, espera el nuevo despliegue y prueba un análisis nuevo. No necesitas
   modificar Vercel ni el código solo para renovar las cookies.

Tras un rechazo remoto se conserva el motivo durante la pausa de descarga
(15 minutos por defecto). El nuevo proceso del despliegue comienza sin esa pausa.
Cookies nuevas no garantizan que YouTube acepte la IP de Render.

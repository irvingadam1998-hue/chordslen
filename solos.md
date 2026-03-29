Tengo un proyecto web que actualmente descarga videos de YouTube en el servidor para analizar acordes. El problema es que YouTube bloquea las descargas desde servidores (detección de bots).

Necesito que analices mi código actual y agregues la siguiente funcionalidad:

## REQUERIMIENTOS

1. **Cambiar la arquitectura a procesamiento local en el navegador:**
   - El servidor NO debe descargar el audio completo
   - El servidor solo debe extraer la URL directa del stream de audio usando yt-dlp
   - El navegador descarga el audio directamente desde esa URL
   - El análisis de acordes se hace 100% en el navegador con JavaScript

2. **Mantener la funcionalidad existente:**
   - Conservar toda la lógica actual de análisis de acordes
   - Mantener la interfaz de usuario igual
   - El resultado final debe ser el mismo (los acordes detectados)

3. **Nuevo endpoint necesario:**
   - Crear `/api/get-audio-url` que reciba URL de YouTube y devuelva:
     * `audioUrl`: URL directa del stream de audio
     * `title`: título de la canción
     * `duration`: duración en segundos

4. **Frontend modificado:**
   - Agregar funciones JavaScript para:
     * Obtener la URL del audio desde el nuevo endpoint
     * Descargar el audio en el navegador usando fetch
     * Procesar el audio localmente usando Web Audio API
     * Enviar el audio procesado a la función de análisis de acordes existente

5. **Consideraciones técnicas:**
   - Usar yt-dlp con user-agent real para evitar bloqueos
   - No guardar archivos temporales en el servidor
   - Implementar manejo de errores para URLs inválidas o bloqueadas
   - Agregar indicadores de progreso en el frontend

## CÓDIGO ACTUAL

[PEGA AQUÍ EL CÓDIGO COMPLETO DE TU PROYECTO]

Por favor, muéstrame:
1. Los archivos modificados completos
2. Explicación de los cambios principales
3. Instrucciones para probar la nueva funcionalidad
# Pruebas con canciones completas

Herramienta independiente de desarrollo. No modifica `backend/model/`, el worker,
el frontend ni los checkpoints originales. Cada ejecución crea una carpeta nueva,
copia los pesos, conserva el audio exacto y registra hashes/configuración/código.
No activa ni promueve modelos. Los audios y resultados quedan bajo `experiments/`,
ignorado por Git.

## Comparar el audio real

Desde la raíz del proyecto, con el entorno existente:

```bash
.venv/bin/python benchmarks/real_world.py analyze \
  --url 'https://youtu.be/0jnGcNESWcE' \
  --checkpoint experiments/joint-solo-exclude/candidate.pt \
  --compare-hpss
```

Para un archivo ya descargado, sustituye `--url` por `--audio /ruta/cancion.wav`.
Se utiliza el mismo descargador de la aplicación, incluidas sus variables de
cookies, sin guardar credenciales en el experimento. Para YouTube se necesita
Node 22+/Deno y FFmpeg en PATH; no interviene ningún servicio de pago.

La comparación conserva:

- `current`: detector matemático, canción completa.
- `neural`: checkpoint neuronal, canción completa, sin fallback oculto.
- `neural_hpss`: opcional, mismo checkpoint tras reducir percusión con HPSS.

HPSS no separa voz/guitarra/bajo individualmente. Es una hipótesis que hay que
evaluar: podría mejorar o empeorar la canción. Conserva también `harmonic.wav`.
No cambia el modo `full`/`triads` guardado en el checkpoint; se registra el modo
efectivamente usado. Una salida de tríadas no prueba que las séptimas eran falsas.

La herramienta produce `report.json`, JSON y probabilidades por detector,
`model.pt` (copia), `audio.wav`, `reference.lab` y `review.html`. Un cambio de código
durante la ejecución la marca incompleta: espera a que termine el otro agente y
repite en otra carpeta. No se mezclan resultados de versiones distintas.

## Escuchar y crear una referencia independiente

Abre `review.html` de esa carpeta en el navegador, junto a `audio.wav`. Incluye
reproducción por tramo, tiempos con milisegundos y exportación de anotaciones.
Las predicciones están ocultas al principio para reducir sesgo de confirmación.
Verlas sigue siendo posible, pero es preferible revisar primero sin ellas.

Las letras con acordes sirven de orientación; no proporcionan por sí solas los
límites temporales ni garantizan las extensiones de la grabación concreta.
No se asignan tiempos automáticamente a partir de las predicciones.

Una línea LAB tiene `inicio fin acorde` en segundos. Marca `X` en zonas sin revisar
y `N` solo cuando hayas confirmado ausencia de acorde. No rellenes regiones dudosas
con el acorde sugerido por el modelo. Las etiquetas usan raíz inglesa, `m`, `7`,
`maj7`, `m7`, etc.; se admite formato Harte como `A:min7` e inversiones `C/E`.
Guarda una referencia revisada con un nombre nuevo, sin sobrescribir otras.

## Medir después de revisar

```bash
.venv/bin/python benchmarks/real_world.py score \
  --run experiments/real-world/MI-EJECUCION \
  --reference /ruta/referencia.lab \
  --reference-kind exact
```

`exact` requiere que también se hayan revisado las séptimas. Si tu referencia es
una versión simplificada para acompañamiento, usa `--reference-kind simplified`:
se comparan ambos lados a nivel de tríadas y no se anuncian errores de séptimas.
Se rechazan referencias vacías/desconocidas, solapamientos y tiempos fuera del audio.

Se calculan WCSR por duración, raíz, calidad, confusiones, F1 de cambios, cobertura
y, con referencia exacta, segundos con séptimas añadidas/omitidas conservando la
misma tríada. `F → Dm7` es un error de raíz, no solo una séptima añadida.
Los informes solo describen los intervalos revisados de esa canción. Menos eventos,
menos séptimas o mayor confianza no significan automáticamente más precisión.

## Cómo decidir si una mejora funciona

1. Estas canciones ya se usan para diagnosticar: son desarrollo/validación, no test.
2. Añadir mezclas variadas, versiones exactas y anotaciones temporales revisadas;
   incluir ejemplos con séptimas reales (p. ej. la referencia de «Amor en silencio»).
3. Registrar artistas y composiciones canónicos; separar por ambos antes de entrenar.
   Distintos enlaces del mismo tema no deben cruzar particiones.
4. Con suficientes referencias, crear el manifiesto LAB descrito en `ACR_GUIDE.md`.
   Entrenar cualquier candidato nuevo en otra carpeta y comparar con `evaluate.py`.
5. Seleccionar cambios únicamente en validation. Después evaluar una sola vez sobre
   artistas/composiciones de test nunca usados para ajustes.
6. Aceptar una mejora solo si aumenta acierto de acordes y mantiene raíz/cambios,
   sin ocultar regresiones en séptimas reales. Reportar también cobertura y coste.

No hay un nuevo porcentaje de precisión para YouTube hasta completar esa referencia.
GuitarSet contiene extractos de guitarra, no una muestra representativa de mezclas
comerciales: [descripción oficial](https://zenodo.org/records/3371780).

Pruebas del evaluador independiente:

```bash
.venv/bin/python -m unittest benchmarks.test_real_world
```

# Primera comparación con canciones de YouTube

Se analizaron ambas grabaciones completas con una copia del candidato
`experiments/joint-solo-exclude/candidate.pt`, SHA-256
`86165bdef85bb0f7add1a19e79742da22b9566f3b9e52879b2d18b46d1e6fd32`.
Modo accurate, vocabulario full, Viterbi switch_cost 48. El checkpoint original
y los archivos del detector no se modificaron. Ambas ejecuciones finalizaron
sin fallos y sin cambios de código durante el análisis.

## Observaciones, no porcentajes de precisión

| Grabación | Duración | Salida | Cambios/eventos | Tiempo con séptimas |
| --- | ---: | --- | ---: | ---: |
| Dónde están corazón | 259,61 s | Detector anterior | 125 | 2,05% |
| Dónde están corazón | 259,61 s | Red actual | 94 | 64,43% |
| Dónde están corazón | 259,61 s | Red + HPSS | 97 | 28,49% |
| Amor en silencio | 276,96 s | Detector anterior | 163 | 3,33% |
| Amor en silencio | 276,96 s | Red actual | 125 | 29,29% |
| Amor en silencio | 276,96 s | Red + HPSS | 123 | 17,82% |

El porcentaje anterior cuenta duración etiquetada 7/maj7/m7, no acordes correctos.
La primera salida neuronal reproduce los 94 eventos del ejemplo del usuario.
HPSS reduce la presencia de séptimas, pero eso no demuestra una mejora.

En «Amor en silencio», la referencia proporcionada contiene C#7, B7 y F#m7.
La variante HPSS reduce C#7 de 6,34 a 3,00 s y F#m7 de 15,02 a 3,16 s.
Ninguna de las dos salidas neuronales emite B7. No se puede decidir qué duraciones
son correctas sin revisar sus posiciones en la grabación. Eliminar séptimas en
general podría empeorar esta canción. HPSS se mantiene como experimento, no se
activó en la aplicación.

## Artefactos locales

- [Dónde están corazón: escuchar y anotar](../experiments/real-world/donde-20260926/review.html)
- [Amor en silencio: escuchar y anotar](../experiments/real-world/amor-20260926-online/review.html)

Cada carpeta conserva el audio original y el armónico, copia de los pesos,
probabilidades por frame, alternativas, timelines y `report.json`.
El audio de la primera ejecución procede de
`experiments/real-world/inputs/0jnGcNESWcE/audio.wav`; `source.json` en esa carpeta
registra el enlace y los metadatos de la descarga.

Enlaces analizados:

- https://youtu.be/0jnGcNESWcE
- https://youtu.be/DluWoeeLFe4

Las referencias del usuario no tienen timestamps. `reference.lab` queda en X
(desconocido) y los informes indican `accuracy_available=false`. No se inventaron
anotaciones ni se usaron las predicciones para crear la respuesta correcta.

Para continuar: revisar tramos con el HTML, exportar un LAB y ejecutar `score`
según [README.md](README.md). Estas dos canciones quedan como desarrollo;
una medición general requiere un conjunto independiente de canciones anotadas.

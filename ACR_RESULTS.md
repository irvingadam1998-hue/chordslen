# Resultados reales del prototipo

Fecha de ejecución: 26 de septiembre de 2026. Estos resultados son una **prueba
del pipeline**, no un benchmark de reconocimiento de canciones comerciales.

## Qué se ejecutó

- Python 3.14.7, PyTorch 2.14.0+cpu, sin CUDA disponible.
- GuitarSet 1.1.0, audio mono de micrófono y acordes ejecutados de sus JAMS.
- Subconjunto determinista: 4 grabaciones train, 4 validation, 4 test; otras
  348 excluidas. Artistas y familias de progresión separados. Seed 42.
- CQT de 36 bins/octava, hop 512, 22.050 Hz; segmentos de 4 s.
- CNN de 67.447 parámetros, sin módulo temporal aprendido ni cabeza de bajo.
- Ocho épocas iniciales y una novena al comprobar reanudación. Mejor checkpoint
  según pérdida de validación: época 6. Se comprobó también la bajada de LR.
- Pérdida de train: 4,7152 → 2,3736. La pérdida de validación no acompaña esa
  mejora: evidencia de que este pequeño entrenamiento no generaliza.

Artefactos locales (ignorados por Git, no publicados):

```text
data/guitarset-prototype.jsonl
data/guitarset/{annotation.zip,annotations/,audio/}
data/features/
experiments/prototype/{best.pt,last.pt,training.jsonl,config.json,support.json}
experiments/prototype/validation.json
```

SHA-256 del checkpoint evaluado:
`179a6b091971dfd9716d09756aad8aebc71453c48d015e5fdd4d31dfc282003f`.

## Comparación sobre los mismos cuatro audios de validación

145,17 s de audio; 102,50 s evaluables con el vocabulario conjunto de nueve
calidades y N. Cobertura: 70,60%. Los intervalos con calidades no representables
no se convierten a mayor/menor para inflar el resultado.

| Métrica | Detector actual | CNN experimental |
| --- | ---: | ---: |
| Weighted chord accuracy (duración exacta) | 61,73% | 0,00% |
| Frame accuracy (rejilla de 20 ms) | 61,72% | 0,00% |
| Root accuracy | 51,56% | 4,69% |
| Quality accuracy | 75,34% | 57,63% |
| F1 de cambios (tolerancia 250 ms) | 0,4950 | 0,2564 |

Root utiliza todos los intervalos cuya raíz es interpretable, incluso si la calidad
queda fuera del vocabulario. Por eso su denominador difiere de WCSR/quality.
Un error de raíz sigue siendo un acorde incorrecto aunque la calidad sea correcta.

| Grabación | WCSR actual | WCSR CNN |
| --- | ---: | ---: |
| `00_BN3-119-G_solo` | 4,32% | 0,00% |
| `00_Jazz3-137-Eb_solo` | 0,00% | 0,00% |
| `00_SS3-84-Bb_comp` | 76,94% | 0,00% |
| `00_SS3-98-C_comp` | 75,80% | 0,00% |

Confusiones más largas de la CNN: D#→E (13,18 s), F→E (11,80 s), A#→E (8,57 s).
El detector actual confundió, entre otros, C→G y D#→A#.

Los tiempos agregados de esa ejecución fueron 12,11 s para baseline y 4,25 s para
NN, con las condiciones de caché de esa sesión. No son una medición controlada de
rendimiento ni predicen el tiempo en Render.

## Decisión y datos que faltan

**No activar este checkpoint.** La CNN no supera al detector actual. No se promovió
ni se modificó ninguna variable de producción. Los cuatro audios de test se
reservaron y no se usaron para ajustar el modelo ni para esta tabla.

El subconjunto tiene solamente 1.939 frames con quality dentro del vocabulario en
train, frente a 4.383 con raíz anotada. Entre las clases representables hay 313
frames maj, 62 de 7, 542 maj7 y 1.022 m7. No hay ejemplos de min, dim, aug, sus2,
sus4 ni N; tampoco hay raíz G. No puede aprender esas clases a partir de esos
datos. El split conservador también separa familias con armonías distintas.

El siguiente experimento debe incorporar datos suficientes y diversos con audio
y anotaciones alineadas de esas clases, manteniendo artistas/composiciones
independientes. Ampliar GuitarSet puede ayudar a comprobar entrenamiento, pero
no cubre por sí solo mezclas con voz/batería ni garantiza todas las clases.
Faltan audios comerciales autorizados y metadatos para Isophonics/Billboard;
para RWC falta además seleccionar una fuente concreta de anotación de acordes.

El experimento inicial anterior no comparó una red temporal entrenada ni una rama
de bajo. Los informes adicionales de la siguiente sección sí incluyen modelos
temporales. Sigue pendiente una comparación controlada de resoluciones/contextos
y separación de instrumentos. CNN/BiLSTM/Transformer tienen pruebas de forma,
máscaras y gradientes. CUDA no se probó porque este equipo no dispone de ella.

## Informes adicionales verificados en el proyecto

Se revisaron los informes locales completos y se verificó que sus SHA-256
corresponden a los respectivos `best.pt`. Esta revisión no volvió a ejecutar los
entrenamientos. Los tres informes utilizan exactamente las mismas 20 grabaciones
de validation y el manifiesto con SHA-256
`c0f1e0aaac32bc203cc55ede38b1a158444646531e3af3df361f436773634063`.
No deben compararse directamente con la tabla inicial de cuatro grabaciones.

| Sistema | WCSR | Root accuracy | Quality accuracy |
| --- | ---: | ---: | ---: |
| Detector actual | 35,78% | 42,06% | 58,04% |
| CNN + Transformer (`accurate`) | 8,41% | 35,59% | 30,08% |
| CNN + BiLSTM (`regularized`) | 15,47% | 42,79% | 37,56% |
| CNN + BiLSTM, salida conjunta (`joint`) | 35,61% | 46,82% | 53,55% |

Fuentes locales: `experiments/validation.json`,
`experiments/validation-regularized.json` y `experiments/validation-joint.json`.
El checkpoint `joint` evaluado tiene SHA-256
`551dc67f6290b8e250297edce2803d4e5afc5d446c348645b5905f4d4e8601da`.

La mejor variante neuronal de estos informes mejora la raíz, pero no el acierto
completo ni la calidad. Los cuatro checkpoints revisados, incluido el prototipo,
siguen con `production_ready=false`. Estos resultados de validación no demuestran
una mejora generalizable ni sustituyen una evaluación final en test.

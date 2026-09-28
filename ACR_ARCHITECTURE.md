# Evolución del reconocimiento de acordes

## Fase 1: auditoría y decisiones antes de implementar

El sistema actual es un detector de plantillas, no una red neuronal. Su ventana
es de 0,5 s con pasos de 0,25 s; limita el audio a 360 s. `measure` es un índice
de evento, no una estimación de compás. `validate_result` mide cobertura de nombres,
no precisión temporal. La similitud de las plantillas tampoco es una probabilidad.

| Elemento existente | Decisión | Motivo |
| --- | --- | --- |
| `CHORD_INTERVALS`, `CHORD_TYPE_PENALTY` | Conservar en baseline | Comparación reproducible; no son objetivos aprendidos. |
| `detect_chord_from_chroma`, `ChordScorer` | Conservar | Detector de respaldo independiente de PyTorch. |
| `detect_key` | Reutilizar como información auxiliar | No descarta predicciones cromáticas. |
| `get_diatonic_chords`, `get_dominant_chord` | Conservar | Priors explícitos opcionales; peso cero por defecto en NN. |
| `apply_harmonic_corrections` | Conservar solo en baseline | Sus sustituciones no se aplican a predicciones neuronales. |
| `simplify_chord` | Conservar solo en baseline | No eliminar maj7/m7 de la salida neuronal. |
| `_harmonic_audio`, `_harmonic_chroma` | Conservar | Optimizaciones existentes útiles para baseline. |
| `_analyze_audio` | Conservar algoritmo; parametrizar duración | Evaluación de canciones completas sin cambiar las reglas. |
| `validate_result` | Conservar contrato | Añadir evaluación científica independiente. |
| `analyze_file_path`, `analyze_url` | Añadir selección de motor | Mantener argumentos existentes, JSON, descarga y avisos de cookies. |

## Arquitectura modular propuesta

Audio completo → features configurables → CNN con posición frecuencial preservada
→ contexto opcional (`none`, BiLSTM o Transformer) → cabezas de raíz (12), calidad
(9), presencia de acorde (2) y bajo (12, supervisión opcional) → probabilidades
conjuntas → prior musical explícito opcional → Viterbi → intervalos/timeline.

`N` significa ausencia de acorde; `X`, etiquetas no representables y zonas sin
anotar no se usan como falsos ejemplos negativos. Las inversiones solo se
emiten si la cabeza de bajo recibió supervisión y aporta suficiente confianza.
No se deduce que todo acorde sin barra tenga un bajo anotado.

```text
backend/model/
  config.py       # configuración serializada también en checkpoints
  labels.py       # vocabulario, Harte y símbolos de la aplicación
  features.py     # CQT/chroma/mel/STFT/bajo y caché
  prepare.py      # descarga GuitarSet, manifiestos, particiones
  dataset.py      # validación, alineación y segmentos PyTorch
  model.py        # CNN + módulo temporal intercambiable
  train.py        # pérdidas, AMP, checkpoints, reanudación
  temporal.py     # Viterbi y priors transparentes
  inference.py    # audio completo, contexto solapado y salida compatible
  metrics.py      # comparación temporal, cambios y confusiones
  configs/       # prototipo, FAST y ACCURATE
evaluate.py       # ambos motores sobre los mismos audios y anotaciones
analyze.py        # entrada cómoda desde la raíz; entrada backend conservada
ACR_GUIDE.md      # instalación, entrenamiento, GPU y evaluación
```

## Datos y separación

GuitarSet tiene JAMS con dos anotaciones de acordes (instruidos y ejecutados),
no LAB. Se seleccionará explícitamente la anotación ejecutada. Es guitarra
acústica: por sí solo no representa canciones comerciales con batería y voz.
Sus seis intérpretes comparten repertorio. Separar solamente archivos o
segmentos produciría leakage. Se reservan intérpretes y familias de progresión
distintos; las combinaciones cruzadas se excluyen y quedan documentadas.

Isophonics y Billboard pueden incorporarse mediante sus LAB y un manifiesto con
audio local, artista y origen/composición. No se asume que SALAMI sea LAB.
RWC exige verificar la procedencia/formato de la anotación de acordes concreta;
las anotaciones AIST no equivalen automáticamente a etiquetas de acordes LAB.
No se descargará audio comercial de fuentes no proporcionadas por esos datasets.
Los identificadores de artista/origen deben ser canónicos entre datasets.

Fuentes: [GuitarSet y tipos de anotación](https://guitarset.weebly.com/),
[descarga versionada](https://zenodo.org/records/3371780),
[Isophonics](https://isophonics.net/content/reference-annotations),
[Billboard](https://ddmal.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)/),
[AIST/RWC](https://staff.aist.go.jp/m.goto/RWC-MDB/AIST-Annotation/).

## Dependencias y activación gradual

Las dependencias neuronales son opcionales. El backend actual debe seguir
arrancando sin PyTorch ni pesos. Los checkpoints experimentales no se activan
automáticamente en producción. Primero se comparan en validación; después se
evalúan una sola vez en test. Un archivo ausente, incompatible o corrupto debe
activar el respaldo con un aviso identificable.

FAST y ACCURATE son configuraciones entrenables diferentes. No se cambia la
resolución de las features de un modelo ya entrenado durante inferencia. Dentro
de un checkpoint se puede variar el solapamiento de contexto y la decodificación.
Los parámetros son hipótesis de partida, no mejoras demostradas.

## Plan experimental

1. Entrenar CNN mínima sobre audio real y comprobar gradientes, pérdida e inferencia.
2. Comparar CNN con BiLSTM/Transformer, manteniendo split y features.
3. Ablaciones: CQT; CQT+chroma+bajo; mel; STFT; resolución y contexto 2/4/8 s.
4. Medir con/sin Viterbi y con/sin prior musical en validación. No ajustar con test.
5. Comparar baseline y candidato sobre exactamente los mismos intervalos.
6. Documentar por canción, calidad, dataset, duración, tiempo y memoria.

La separación de fuentes queda como experimento externo mediante audio preparado
en el manifiesto, conservando la misma duración y alineación. HPSS no separa
guitarra, piano y voz. Integrar Demucs u otro separador requiere evaluar sus pesos,
coste y posibles artefactos; no se instala ni se ejecuta por defecto.

No hay una mejora de precisión demostrada por el mero hecho de implementar esta
arquitectura. El informe de ejecución registrará resultados reales y limitaciones.

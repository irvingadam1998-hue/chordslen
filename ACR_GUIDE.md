# Entrenar y medir el detector neuronal

El algoritmo anterior sigue disponible. Una arquitectura nueva **no garantiza**
mayor precisión: los resultados medidos se registran en `ACR_RESULTS.md`.
La auditoría y las decisiones están en [ACR_ARCHITECTURE.md](ACR_ARCHITECTURE.md).

## 1. Entorno

Desde la raíz, con un entorno Python compatible con los wheels de PyTorch:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
# CPU; no descargar CUDA para un servidor sin GPU:
pip install 'torch>=2.9,<3' --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements-neural.txt
```

Para GPU NVIDIA, instala el wheel indicado para tu sistema/controlador en el
[selector oficial de PyTorch](https://pytorch.org/get-started/locally/), en lugar
del wheel CPU anterior. Comprueba:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

`--device auto` elige CUDA si está disponible; `--device cuda` falla claramente
si no lo está. AMP usa `torch.autocast` y `torch.amp.GradScaler` solo en CUDA.
El camino CUDA está implementado, pero debe verificarse en una GPU real; una
prueba en CPU no lo certifica. [Referencia AMP](https://docs.pytorch.org/docs/stable/amp.html).

El Docker existente sigue instalando solo las dependencias del detector actual.
No añadas PyTorch al Render gratuito sin medir memoria. Para servir la NN necesitas
instalar también sus dependencias y proporcionar el checkpoint en ese backend;
el frontend de Vercel sigue llamando a la misma API remota. No se entrena en Vercel.

## 2. Datos reales y particiones

GuitarSet 1.1.0 tiene audios y JAMS descargables desde su
[registro oficial](https://zenodo.org/records/3371780). Descarga completa:

```bash
python -m backend.model.prepare --guitarset data/guitarset --download --manifest data/manifest.jsonl
```

Para comprobar mecánicamente el pipeline con menos descarga:

```bash
python -m backend.model.prepare --guitarset data/guitarset --download --audio-limit-per-split 4 --manifest data/guitarset-prototype.jsonl
```

El subconjunto **no es un benchmark suficiente**. Se elige determinísticamente
antes de entrenar. La descarga parcial de audio usa HTTP Range y verifica el CRC
de cada miembro ZIP; las descargas completas verifican el MD5 publicado. Si el
servidor no acepta Range, descarga/extrae el ZIP completo. Puedes copiar
`annotation.zip` y `audio_mono-mic.zip` descargados manualmente a `data/guitarset/`.

Partición conservadora: cuatro intérpretes para train, uno para validation y uno
para test, con una familia de progresión distinta en cada partición. Se excluyen
las combinaciones cruzadas, incluyendo versiones solo/acompañamiento y cambios
de estilo/tempo de la misma familia. Es una partición propia, no la de los papers.
Los dos archivos señalados por el repositorio oficial con problemas de tiempo
también quedan excluidos, sin corregir etiquetas a escondidas:
[incidencia de GuitarSet](https://github.com/marl/GuitarSet/issues/5).

Se usa la anotación de acordes **ejecutados**, identificada por sus metadatos.
Las etiquetas extendidas no representables se excluyen de la pérdida de quality;
su raíz todavía puede supervisarse. `support.json` permite ver qué clases tuvieron
ejemplos. Las clases sin ejemplos no deben anunciarse como aprendidas.

Para Isophonics/Billboard u otro corpus con LAB, crea JSONL (una grabación por línea):

```json
{"id":"corpus:tema-001","dataset":"Isophonics","audio":"audio/tema.wav","annotation":"labels/tema.lab","format":"lab","artist_id":"artista-canonico","origin_id":"composicion-canonica","split":"train","implicit_bass":false}
```

Las rutas se resuelven respecto al manifiesto. LAB requiere `inicio fin acorde`
en segundos, en orden, sin solapamientos; por ejemplo `0.0 3.2 C:maj7` y
`3.2 4.0 A:min/5`. `N` es ausencia de acorde; `X` y huecos son desconocidos.
Por defecto solo se supervisa el bajo indicado explícitamente. Activa
`implicit_bass` únicamente si la convención del dataset garantiza ese significado.

Asigna `train`, `validation`, `test` o `excluded` a **grabaciones completas**, antes
de crear segmentos. Ningún `artist_id`, `origin_id` ni hash de audio puede cruzar
particiones. Usa identificadores canónicos compartidos entre datasets: un hash no
detecta un cover, una mezcla diferente ni un mismo audio recodificado. Es necesario
auditar esos duplicados por metadatos. El programa rechaza cruces conocidos:

```bash
python -m backend.model.prepare --manifest data/manifest.jsonl
```

Faltan los audios comerciales y un inventario de artista/origen para incorporar
Isophonics/Billboard. No vienen incluidos aquí. Billboard ofrece LAB por separado;
`salami_chords.txt` **no** es LAB. Para RWC falta además seleccionar y verificar
una fuente concreta de anotaciones de acordes; no se inventa un adaptador basado
solamente en el nombre del dataset.

### Añadir un corpus LAB con audio propio

Si tienes el audio (por ejemplo, los discos de Isophonics) y sus `.lab`, colócalos
con la misma ruta relativa `<artista>/[álbum/]<canción>` en dos carpetas. Se admite
audio `.wav`, `.flac`, `.mp3`, `.ogg` y `.m4a`; las anotaciones sin audio se omiten
y se informa cuántas. Este comando fusiona el corpus con el manifiesto de GuitarSet:

```bash
python -m backend.model.prepare --lab-annotations data/isophonics/chordlab \
  --lab-audio data/isophonics/audio --lab-dataset Isophonics --lab-implicit-bass \
  --base-manifest data/manifest.jsonl --manifest data/manifest-combined.jsonl
```

- `--lab-split train` (predeterminado) añade todo al entrenamiento: validation y test
  siguen siendo GuitarSet, comparables con resultados anteriores.
- `--lab-split auto` reparte **artistas completos** 80/10/10 con un hash estable. Con
  pocos artistas (Isophonics es casi todo The Beatles) puede dejar particiones vacías.
- `--lab-implicit-bass`: un acorde sin `/bajo` tiene la raíz en el bajo (Harte).
- El origen de cada canción ignora el número de pista, así que las reediciones
  comparten `origin_id`. Los covers de otros artistas **no** se detectan.
- Los LAB con `N` enseñan al modelo el silencio, ausente en GuitarSet.

## 3. Entrenamiento gradual

Primero CNN sin recurrente/Transformer:

```bash
python -m backend.model.train --manifest data/guitarset-prototype.jsonl --config backend/model/configs/prototype.json --output experiments/prototype --device auto
```

Después, con un corpus suficiente, entrena y compara configuraciones:

```bash
python -m backend.model.train --manifest data/manifest.jsonl --config backend/model/configs/fast.json --output experiments/fast
python -m backend.model.train --manifest data/manifest.jsonl --config backend/model/configs/accurate.json --output experiments/accurate
```

Los JSON controlan `train.batch_size`, `learning_rate`, `num_epochs`,
`segment_seconds`, `patience`, `num_workers`, `amp`, `class_weighting`,
`features.sample_rate` y `hop_length`. Son los equivalentes configurables de
BATCH_SIZE, LEARNING_RATE, NUM_EPOCHS, SEGMENT_SECONDS, SAMPLE_RATE y HOP_LENGTH.
Reduce batch/contexto si falta memoria; aumenta épocas solo si validación lo
justifica. `model.temporal` admite `none`, `bilstm`, `transformer`.

`train.pitch_shift` (0–6) transpone cada segmento de train un número aleatorio de
semitonos en `[-n, +n]`: desplaza los bins CQT, rota chroma y bajo, y ajusta
raíz y bajo de las etiquetas. Validation nunca se transpone. Solo admite
`representation` `cqt` o `chroma`; los bins que quedan vacíos se rellenan con silencio.

Con GuitarSet solo, `accurate.json` (Transformer, 836k parámetros) memoriza train:
91 % en train y 12 % en validation. `regularized.json` es la alternativa para corpus
pequeños: BiLSTM de una capa (136k parámetros), dropout 0.3, `weight_decay` 0.01 y
`pitch_shift` 6:

```bash
python -m backend.model.train --manifest data/manifest.jsonl --config backend/model/configs/regularized.json --output experiments/regularized
```

Features: `representation` admite `cqt`, `chroma`, `mel`, `stft`; `chroma` y `bass`
añaden ramas de información al vector espectral; `harmonic` habilita HPSS.
La CQT predeterminada usa 36 bins/octava, siete octavas desde C1, afinación fija
y bloques con contexto para limitar la memoria de los espectros. Conserva posición
frecuencial antes de las cabezas; no promedia todos los tonos juntos. La afinación
y resolución también son hipótesis evaluables, no garantías.

Normalización y pesos de clase se calculan exclusivamente con train. La pérdida
combina root + quality + presencia; añade bajo con peso configurable cuando hay
etiquetas. Los pesos son inversa de raíz de frecuencia, acotados. Se enmascaran
padding/etiquetas desconocidas por cabeza. Los archivos incluyen:

- `best.pt`: menor pérdida de validación; `last.pt`: último estado reanudable.
- `training.jsonl`: pérdidas, accuracy conjunta sin suavizar, learning rate y tiempo.
- `config.json`, `support.json`: configuración y soporte de clases de train.
- Dentro del checkpoint: normalización, vocabulario, versiones, hashes de datos,
  optimizador, scheduler, scaler y estados RNG.

Reanudar en el mismo directorio, manteniendo datos/configuración:

```bash
python -m backend.model.train --manifest data/guitarset-prototype.jsonl --config backend/model/configs/prototype.json --output experiments/prototype --resume experiments/prototype/last.pt --epochs 16
```

No se garantiza identidad bit a bit entre hardware/versiones. El scheduler reduce
LR por pérdida de validación y early stopping evita seguir sin mejora. El mejor
checkpoint por loss no necesariamente maximiza WCSR: la comparación final es obligatoria.

## 4. Inferencia y fallback

Los pesos guardan su configuración de features: inferencia no cambia el hop ni
la resolución de un checkpoint entrenado. FAST utiliza menor solapamiento; ACCURATE
usa ventanas solapadas con contexto futuro/pasado. No es una inferencia causal.
Las configuraciones `fast.json` y `accurate.json` requieren entrenamientos separados.

```bash
# Detector actual, sin PyTorch ni pesos:
python analyze.py --file cancion.wav --engine current
# Probar explícitamente un checkpoint experimental solo en esta ejecución:
ACR_ALLOW_EXPERIMENTAL=1 python analyze.py --file cancion.wav --engine neural --checkpoint experiments/prototype/best.pt --mode accurate
# La entrada original sigue funcionando:
python backend/scripts/analyze.py --file cancion.wav
```

Variables del backend: `ACR_ENGINE=auto|current|neural`, `ACR_MODE=fast|accurate`,
`ACR_MODEL_PATH`; opcionalmente `ACR_MODEL_PATH_FAST` y `ACR_MODEL_PATH_ACCURATE`.
Sin modelo utilizable se ejecuta el actual. Un fallo de carga o un modelo explícito
ausente añade `ACR_NEURAL_FALLBACK`; `engine` identifica el motor real. Los avisos
de cookies se conservan. La caché de trabajos distingue modelo/modo.

No se activan pesos aleatorios ni experimentales por defecto. `production_ready`
es un control local, no una certificación científica. Tras una comparación completa
de validación, puedes generar un candidato habilitable:

```bash
python -m backend.model.promote --checkpoint experiments/accurate/best.pt --report experiments/validation.json --output experiments/accurate/candidate.pt
```

La promoción exige mejorar WCSR sin empeorar root, quality ni F1 de cambios respecto
al baseline. No cambia variables del servidor ni despliega nada. La representatividad
del corpus y el tamaño de muestra siguen siendo responsabilidad del experimento.
Evalúa después el candidato una sola vez en test, antes de decidir su uso real.

El JSON conserva `success`, `chords_timeline`, `key`, `timings`, etc. Añade `engine`,
`duration`, metadatos del modelo y `end`/`confidence` por evento. La confianza es
probabilidad conjunta del modelo **sin calibrar**, no una garantía. `N` debe
mostrarse como silencio/sin acorde. `measure` sigue siendo índice, no compás.

## 5. Medir si mejoró

```bash
python evaluate.py --manifest data/manifest.jsonl --checkpoint experiments/accurate/best.pt --split validation --output experiments/validation.json
python evaluate.py --manifest data/manifest.jsonl --checkpoint experiments/accurate/candidate.pt --split test --output experiments/test.json
```

`python evaluate.py` también funciona: si falta el manifiesto o checkpoint indica
que faltan métricas, sin generar porcentajes ficticios. Cuando falta solo el
checkpoint puede evaluar baseline. La evaluación neuronal nunca usa fallback.
Se rechazan artistas/orígenes/audio de test vistos por el checkpoint en train o
validation. Ambos motores procesan los mismos archivos completos y se agregan
solo pares exitosos; cualquier error queda listado e invalida el informe completo.

Métricas del JSON:

- `frame_accuracy`: acierto root+quality o N en una rejilla de 20 ms, configurable.
- `weighted_chord_accuracy`/`chord_accuracy`: fracción de **duración** correctamente
  etiquetada; intersección exacta de intervalos, no cobertura de nombres.
- Root y quality ponderadas por duración; N no recibe raíz/calidad ficticia.
- Precision/recall/F1 por clase y macro; matrices de confusión en segundos.
- F1 de cambios, precision, recall y error de tiempo; emparejamiento uno a uno,
  tolerancia predeterminada 250 ms; se excluyen inicio/final y huecos desconocidos.
- `mir_eval`: root, majmin, sevenths, MIREX y segmentación seg/underseg/overseg
  **sobre el vocabulario representable**. No comparar esos valores directamente
  con papers que usan otro vocabulario o partición.
- Bajo sobre etiquetas explícitas, cobertura del vocabulario y del tiempo,
  tiempos por canción y diferencias pareadas. Sin referencias de bajo no hay métrica.

Conserva los tres splits y sus hashes. Ajusta resolución/contexto/costes solo en
validation. Compara primero CNN, luego BiLSTM y Transformer sin cambiar los demás
factores. Prueba 2/4/8 s; usa `--no-viterbi` para la ablación temporal. Examina las
regresiones por canción/clase, no solo el promedio. Repite entrenamiento con varias
semillas y reporta dispersión; un prototipo pequeño no mide generalización a pop.

El prior tonal vale **cero por defecto**. Si se activa, se suma explícitamente a
log-probabilidades, junto a un bonus para acordes diatónicos/dominantes; ninguna
clase se prohíbe. Los acordes prestados siguen disponibles. No hay reglas ocultas
para ii-V-I/cadencias: el modelo temporal debe aprenderlas antes de añadir priors
de transición específicos medidos. Viterbi penaliza cambios sin borrar por regla
todos los acordes cortos. El filtro de 120 ms solo afecta a inversiones inciertas.

Desde Python, `analyze_neural(..., diagnostics_path='experiments/song.npz')` guarda
probabilidades por cabeza, conjuntas, estados originales/decodificados y el prior.
Eso permite inspeccionar discrepancias sin volcar miles de frames en la API.

## 6. Separación de fuentes y memoria

HPSS es opcional; no equivale a separar voz/guitarra/piano/bajo. Para comparar
stems de un separador externo, prepara audios alineados y un manifiesto nuevo con
los mismos artistas/orígenes/splits, y repite entrenamiento y evaluación completos.
No descargamos pesos externos ni añadimos ese coste al análisis por defecto.

Los espectros se calculan por bloques; inferencia procesa una ventana contextual
a la vez. El audio mono y las features finales siguen en RAM. La preparación del
entrenamiento retiene features de train/validation en RAM: para corpus grandes
hará falta un Dataset con memmap/LRU o sharding; mide memoria antes de cargarlo.
La caché evita repetir DSP entre experimentos. No se afirma una mejora de velocidad
sin medirla con la misma máquina, audio y modo.

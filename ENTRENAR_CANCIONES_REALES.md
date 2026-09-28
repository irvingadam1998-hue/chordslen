# Entrenar con canciones reales (mezclas completas)

Hasta ahora la red solo ha aprendido con guitarra sola (GuitarSet). En canciones con
voz, batería y bajo confunde, por ejemplo, Am con Am7. Esta guía la entrena con
canciones reales, usando anotaciones públicas de acordes y **audio de discos que
tú tengas**.

Todos los comandos se ejecutan desde la raíz del proyecto.

## Qué hay ya preparado

- **Anotaciones descargadas** en `data/annotations/`. Son solo texto; no incluyen audio.
  - Isophonics: 224 canciones (The Beatles, Queen, Carole King, Zweieck).
  - Billboard: 729 canciones de pop de EE. UU. (1958–1991), sin duplicados.
- **Catálogo normalizado:** `data/real/catalog/catalog.csv`, con artista, título,
  álbum y duración de las **953 canciones** (54.8 horas en total).

Para regenerar el catálogo desde las anotaciones:

```bash
.venv/bin/python -m backend.model.real_corpus catalog
```

## 1. Reúne tu audio

Abre `data/real/catalog/catalog.csv` y busca qué canciones tienes en disco. No
hace falta tenerlas todas:

| Canciones | Qué esperar |
|---|---|
| ~50 | Una primera prueba útil |
| 200 o más | Una mejora clara |
| Todas | Lo ideal |

Colócalas en cualquier carpeta, por ejemplo `~/Música/chordlens/`, con la
estructura de subcarpetas que quieras. Formatos: `.wav`, `.flac`, `.mp3`, `.ogg`
y `.m4a`.

El script identifica cada canción de una de estas formas:

1. Por las **etiquetas del archivo** (artista y título), lo más fiable.
2. Por el nombre del archivo: `Artista - Título.mp3`.
3. Por la carpeta y el archivo: `Artista/Título.mp3`.

Ignora los acentos, las mayúsculas, un "The" al inicio y los sufijos como
"(Remastered 2009)".

> Usa **versiones de estudio del disco**, no directos ni remixes. Las
> anotaciones corresponden al disco original.

## 2. Empareja el audio y corrige desfases

```bash
.venv/bin/python -m backend.model.real_corpus match --audio ~/Música/chordlens
```

Para cada archivo, el script hace lo siguiente:

- Busca su anotación en el catálogo.
- **Detecta el desfase** entre tu versión y la anotada, por ejemplo si tu disco
  tiene más silencio al inicio. Busca hasta ±15 s, con una precisión de ~0.1 s.
- Guarda las anotaciones corregidas en `data/real/matched/labs/`.
- Crea enlaces a tu audio en `data/real/matched/audio/`. **No copia los
  archivos.**

Revisa el informe `data/real/matched/match_report.csv`. Esto significa cada estado:

| Estado | Significado |
|---|---|
| `ok` | Emparejada y alineada; se usará |
| `sin_anotacion` | No está en el catálogo, o el título o el artista no coinciden |
| `no_coincide` | El audio no sigue esos acordes: probablemente otra canción o un directo |
| `otra_version` | La duración no encaja: otra edición, versión extendida o radio edit |
| `duplicado` | Esa canción ya estaba emparejada con otro archivo |

Si una canción que sí tienes sale como `sin_anotacion`, corrige las etiquetas o
el nombre del archivo y vuelve a ejecutar el comando.

## 3. Crea el manifiesto

Este comando combina tus canciones reales con GuitarSet:

```bash
.venv/bin/python -m backend.model.prepare \
  --lab-annotations data/real/matched/labs --lab-audio data/real/matched/audio \
  --lab-dataset Real --lab-split auto --lab-implicit-bass \
  --base-manifest data/manifest-solo-exclude.jsonl \
  --manifest data/manifest-real.jsonl
```

- `--lab-split auto` reparte **artistas completos**: ~80 % para train, ~12 % para
  validation y ~8 % para test. Un artista nunca aparece en dos particiones.
  The Beatles, Queen y Carole King caen en train.
- **Si solo tienes pocos artistas,** alguna partición puede quedar vacía. En ese
  caso usa `--lab-split train`, para usar tu audio solo en entrenamiento, y mide
  con el paso 5.

Este otro manifiesto contiene solo las canciones reales, para medir sin mezclar
con GuitarSet:

```bash
.venv/bin/python -m backend.model.prepare \
  --lab-annotations data/real/matched/labs --lab-audio data/real/matched/audio \
  --lab-dataset Real --lab-split auto --lab-implicit-bass \
  --manifest data/manifest-real-only.jsonl
```

## 4. Entrena

```bash
.venv/bin/python -m backend.model.train --manifest data/manifest-real.jsonl \
  --config backend/model/configs/real.json --output experiments/real
```

La configuración `real.json` define un modelo algo más grande: 341 000
parámetros, BiLSTM de 2 capas y salida conjunta de 109 acordes. Cada época usa
**3000 segmentos al azar** (unas 6.7 horas de audio), en vez de todos, para que
sea viable en CPU.

**Cuánto tarda:**

- **Features:** la primera vez se calculan para cada canción, unos 2–5 s por
  canción. Con 700 canciones, alrededor de 1 hora. Se guardan en `data/features/`
  y se reutilizan.
- **Entrenamiento:** unos **15 minutos por época** en tu CPU (medido: 0.3 s por
  segmento), y hasta 60 épocas con `patience` 8. Lo normal es que pare entre la
  época 30 y la 40, así que calcula **entre 8 y 15 horas**: déjalo durante la noche.
- **Disco:** unos 10 MB de features por canción (~7 GB para 700). Se leen del
  disco bajo demanda, así que **la RAM no crece** con el número de canciones.

Para seguir el progreso:

```bash
tail -f experiments/real/training.jsonl
```

## 5. Mide con canciones reales

En estos comandos, `validation` y `test` solo contienen canciones reales, de
artistas que el modelo no vio al entrenar.

Primero, ajusta el decodificador **en validation**:

```bash
for c in 16 32 48 64; do
  .venv/bin/python evaluate.py --manifest data/manifest-real-only.jsonl \
    --checkpoint experiments/real/best.pt --split validation --switch-cost $c \
    --output experiments/sweep/real-sc$c.json
done
```

Elige el `switch_cost` con mayor `weighted_chord_accuracy`, promueve el modelo con
ese informe y evalúalo **una sola vez en test**:

```bash
.venv/bin/python -m backend.model.promote --checkpoint experiments/real/best.pt \
  --report experiments/sweep/real-sc48.json --output experiments/real/candidate.pt

.venv/bin/python evaluate.py --manifest data/manifest-real-only.jsonl \
  --checkpoint experiments/real/candidate.pt --split test --output experiments/test-real.json
```

Sustituye `sc48` por el valor que hayas elegido. No uses `--vocabulary triads` al
medir: la métrica exige la séptima exacta cuando la anotación la tiene. Las
tríadas se activan después, en la app, con `ACR_VOCABULARY`. `promote` solo acepta el modelo
si supera al detector clásico en esas canciones reales.

## 6. Úsalo en la app

Es el mismo arranque que en `ARRANQUE_LOCAL.md`, cambiando la ruta del modelo:

```bash
API_KEY=clave-local ACR_ENGINE=neural ACR_MODE=accurate ACR_VOCABULARY=triads \
ACR_MODEL_PATH="$PWD/experiments/real/candidate.pt" \
.venv/bin/python backend/extractor_server/app.py
```

## Expectativas realistas

- **El 100 % no es alcanzable:** dos músicos que transcriben la misma canción
  coinciden en torno a un 90 %. Los mejores sistemas publicados rondan el
  80–85 % en pop, contando solo tríadas mayores y menores.
- **El estilo importa:** el catálogo es pop y rock en inglés de 1958 a 1991. Para
  música latina, como "Dónde están corazón", ayudará, porque armónicamente es
  parecida, pero lo ideal sería añadir anotaciones de tu repertorio con el mismo
  formato LAB.
- **Los derechos importan:** usa audio de discos que tengas. Las anotaciones
  son públicas; el audio no.

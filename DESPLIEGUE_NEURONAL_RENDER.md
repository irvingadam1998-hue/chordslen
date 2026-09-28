# Actualizar el Blueprint existente para usar la red neuronal

El archivo de este proyecto es **`render.yaml`**, en la raíz. La copia local
actual selecciona `runtime: docker`, pero eso no demuestra qué runtime usa hoy
el servicio publicado. Render admite Python nativo y Docker; también permite
cambiar el runtime de un servicio existente mediante su Blueprint. Primero mira
el runtime del servicio en Render y elige la ruta correspondiente abajo. No
crees un Blueprint nuevo.

Esta guía describe cambios que debes preparar y publicar tú. No se ha modificado
el Blueprint, el Dockerfile ni el modelo al escribir estas instrucciones.

## 1. Incluir los pesos en el repositorio que recibe Render

Desde la raíz del proyecto:

```bash
mkdir -p backend/checkpoints
cp experiments/joint-solo-exclude/candidate.pt backend/checkpoints/candidate.pt
```

Añade al final de `.gitignore` esta excepción específica:

```gitignore
!/backend/checkpoints/candidate.pt
```

Comprueba que `backend/checkpoints/candidate.pt` esté incluido cuando publiques tus
cambios en GitHub. Los archivos originales de `experiments/` siguen ignorados.
El candidato revisado pesa 1.766.877 bytes y su SHA-256 es:

```text
86165bdef85bb0f7add1a19e79742da22b9566f3b9e52879b2d18b46d1e6fd32
```

No se utiliza Secret Files para el checkpoint: Render admite archivos de texto y
limita el total de archivos secretos a 1 MB. Las cookies siguen siendo secretos;
no las copies al repositorio ni a la imagen.

## 2. Elegir el runtime y preparar el backend

Si tu servicio actual usa **Python nativo**, cambia el bloque del servicio en
`render.yaml` para quitar `dockerfilePath` y `dockerContext` y usar comandos de
Python. Conserva el mismo nombre, región, plan, health check y variables:

```yaml
    runtime: python
    buildCommand: >-
      pip install -r backend/requirements.txt &&
      pip install --index-url https://download.pytorch.org/whl/cpu 'torch>=2.9,<3' &&
      pip install -r backend/requirements-neural.txt
    startCommand: >-
      cd backend/extractor_server &&
      gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180 app:app
```

Render ejecutará el servicio desde la raíz del repositorio. El servicio nativo
necesita que el repositorio incluya también `backend/checkpoints/candidate.pt`;
configura `ACR_MODEL_PATH` con esa ruta absoluta en el entorno de Render (por
ejemplo, `/opt/render/project/src/backend/checkpoints/candidate.pt`). Si Render
muestra otra ruta de checkout en sus logs, usa esa ruta. Para la versión de
Docker sigue los pasos siguientes.

## 3. Instalar PyTorch e incluir el checkpoint en la imagen

En `backend/extractor_server/Dockerfile`, inmediatamente después de:

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

añade:

```dockerfile
COPY backend/requirements-neural.txt /app/requirements-neural.txt
RUN pip install --no-cache-dir "torch>=2.9,<3" --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /app/requirements-neural.txt
COPY backend/checkpoints/candidate.pt /app/checkpoints/candidate.pt
```

Conserva las instrucciones existentes que copian `backend/model` y
`backend/scripts`, y el arranque con Gunicorn. No se usa `.venv/bin/python` dentro
de esta imagen: su entorno Python se instala durante la construcción.

## 4. Añadir las variables al mismo `render.yaml`

Dentro de `envVars` del servicio `chordlens-worker`, junto a las variables
existentes, añade este bloque con la misma indentación:

```yaml
      - key: ACR_ENGINE
        value: neural
      - key: ACR_MODE
        value: accurate
      - key: ACR_VOCABULARY
        value: triads
      - key: ACR_MODEL_PATH
        value: /app/checkpoints/candidate.pt
```

Mantén nombre, región, runtime, plan, `API_KEY` y las demás variables actuales.
No necesitas `ACR_ALLOW_EXPERIMENTAL=1` para este candidato promovido.
Si configuraste previamente `ACR_MODEL_PATH_ACCURATE` en el panel, elimínala o
hazla apuntar a la misma ruta: tiene prioridad sobre `ACR_MODEL_PATH`.

`triads` convierte las séptimas a su tríada, incluidas las séptimas reales.
No demuestra que fueran predicciones incorrectas. Para mantener las extensiones
usa `full`; se conserva en cualquier caso el mismo archivo de pesos.

## 5. Publicar y sincronizar el Blueprint existente

1. Revisa y sube tú los cambios a la rama de GitHub vinculada a tu Blueprint.
   El código neuronal de `backend/model/`, sus dependencias, el archivo de pesos
   y los cambios de integración de `analyze.py` deben estar incluidos.
2. Render → **Blueprints** → abre el Blueprint que ya administra el backend.
3. **Blueprint Path** debe seguir siendo `render.yaml`.
4. Si Auto Sync está activo, Render sincroniza los cambios del Blueprint al
   recibirlos. Si está desactivado, pulsa **Manual Sync**.
5. Abre el servicio `chordlens-worker` y comprueba el resultado del build/deploy.

El checkpoint y PyTorch se incluyen durante el build: un reinicio de la imagen
vieja no los añade. No copies el comando de tu terminal al campo Blueprint Path.

## 6. Verificar el motor y el frontend

Tras analizar una canción, la respuesta final debe contener:

```json
{"engine":"neural","model":{"mode":"accurate","vocabulary":"triads"}}
```

`engine: current` con `ACR_NEURAL_FALLBACK` significa que no se pudo utilizar la
red. Revisa el error `[acr] neural fallback` en los logs. `/health` comprueba las
dependencias generales; no confirma que se haya cargado el modelo.

Si se mantiene el mismo servicio y la misma API key, Vercel conserva sus valores:

```env
FLASK_API_URL=https://TU-BACKEND.onrender.com
PUBLIC_WORKER_URL=https://TU-BACKEND.onrender.com
FLASK_API_KEY=LA_API_KEY_DEL_BACKEND
```

## Memoria

El Blueprint sigue solicitando el plan gratuito, con 512 MB de RAM. No se ha
medido este modelo en ese límite. PyTorch y las features pueden superar esa
memoria durante un análisis; un error de memoria requiere medir/optimizar el
consumo o decidir otro recurso, no cambiar variables de ruta. Esta guía no cambia
el plan ni contrata recursos.

Fuentes oficiales: [cambiar el runtime de un servicio existente](https://render.com/changelog/change-an-existing-services-runtime-via-api-or-blueprint),
[runtimes Python nativos](https://render.com/docs/native-runtimes),
[Blueprints y sincronización](https://render.com/docs/infrastructure-as-code),
[archivos secretos](https://render.com/docs/configure-environment-variables#secret-files),
[recursos por plan](https://render.com/docs/compute-plans),
[instalación de PyTorch para CPU](https://pytorch.org/get-started/locally/).

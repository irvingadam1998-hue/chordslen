FROM node:22-bookworm-slim AS javascript
FROM python:3.11-slim-bookworm

COPY --from=javascript /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/requirements-neural.txt /app/requirements-neural.txt
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.9,<3" \
    && pip install --no-cache-dir -r /app/requirements-neural.txt
COPY backend/checkpoints/candidate.pt /app/checkpoints/candidate.pt
ENV NUMBA_CPU_NAME=generic \
    NUMBA_CACHE_DIR=/opt/chordlens/numba-cache
COPY backend/scripts ./backend/scripts
COPY backend/model ./backend/model
# Cache is baked into the image, so a free instance restart does not discard it.
# Generic CPU code can be reused on build/runtime hosts with different CPU models.
RUN python backend/scripts/warm_audio.py
COPY backend/extractor_server ./backend/extractor_server
WORKDIR /app/backend/extractor_server
ENV PORT=5002
EXPOSE 5002
# Jobs and the YouTube cooldown share one process; threads serve polling/uploads.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5002} --workers 1 --threads 4 --timeout 180 app:app"]

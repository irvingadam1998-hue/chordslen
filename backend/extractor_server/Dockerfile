FROM node:22-bookworm-slim AS javascript
FROM python:3.11-slim-bookworm

COPY --from=javascript /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/scripts ./scripts
COPY backend/extractor_server ./extractor_server
WORKDIR /app/extractor_server
ENV PORT=5002
EXPOSE 5002
# Jobs and the YouTube cooldown share one process; threads serve polling/uploads.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5002} --workers 1 --threads 4 --timeout 180 app:app"]

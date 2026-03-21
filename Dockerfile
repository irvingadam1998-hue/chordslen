FROM node:20-slim

# System deps: Python, pip, ffmpeg
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    yt-dlp \
    librosa \
    soundfile \
    numpy

WORKDIR /app

# Node deps
COPY package*.json ./
RUN npm ci

# Source
COPY . .

# Build Next.js
RUN npm run build

# Copy static assets into standalone output
RUN cp -r .next/static .next/standalone/.next/static && \
    cp -r public .next/standalone/public

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
EXPOSE 3000

CMD ["node", ".next/standalone/server.js"]

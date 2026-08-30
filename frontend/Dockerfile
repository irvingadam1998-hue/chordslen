FROM node:20-slim

WORKDIR /app

# Node deps
COPY package*.json ./
RUN npm ci

# Source
COPY . .

# Copy YouTube cookies if present (optional — silently skipped if missing)
COPY cookies.tx[t] /app/

# Build Next.js
RUN npm run build

# Copy static assets into standalone output
RUN cp -r .next/static .next/standalone/.next/static && \
    cp -r public .next/standalone/public

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
EXPOSE 3000

CMD ["node", ".next/standalone/server.js"]

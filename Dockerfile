# ---- Stage 1: build the Svelte + TypeScript frontend ----
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Flask API + the built app ----
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask gunicorn yt-dlp && python -c "import yt_dlp"
COPY app.py ./
COPY static ./static
COPY --from=web /web/dist ./web
ENV DATA_DIR=/data WEB_DIR=/app/web
VOLUME /data
EXPOSE 8088
# Downloading/transcoding a long Instagram clip can take well over a minute.
# Gunicorn's default 30 s timeout killed the worker mid-request (surfacing as a
# 502), so allow long requests and serve them on threaded workers.
CMD ["gunicorn","-b","0.0.0.0:8088","-w","2","--threads","4","--timeout","300","--graceful-timeout","30","--access-logfile","-","app:app"]

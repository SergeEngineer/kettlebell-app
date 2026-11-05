FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask gunicorn yt-dlp && python -c "import yt_dlp"
COPY . .
RUN python -c "import urllib.request as u; u.urlretrieve('https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js','static/htmx.min.js')"
ENV DATA_DIR=/data
VOLUME /data
EXPOSE 8088
CMD ["gunicorn","-b","0.0.0.0:8088","-w","2","--access-logfile","-","app:app"]

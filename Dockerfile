FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask gunicorn
COPY . .
RUN python -c "import urllib.request as u; u.urlretrieve('https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js','static/htmx.min.js')"
ENV DATA_DIR=/data
VOLUME /data
EXPOSE 8088
CMD ["gunicorn","-b","0.0.0.0:8088","-w","2","--access-logfile","-","app:app"]

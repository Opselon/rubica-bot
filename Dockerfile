FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    RUBIKA_LOG_LEVEL=INFO \
    RUBIKA_DB_URL=sqlite:///data/bot.db \
    RUBIKA_REGISTER_WEBHOOK=false

WORKDIR /app

RUN addgroup --system rubika && \
    adduser --system --ingroup rubika --home /app --shell /bin/false rubika && \
    mkdir -p /data /var/log/rubika-bot && \
    chown -R rubika:rubika /app /data /var/log/rubika-bot

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY app app
COPY install.py install.py
COPY README.md README.md

USER rubika

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; \
url='http://127.0.0.1:8080/health'; \
sys.exit(0 if urllib.request.urlopen(url, timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

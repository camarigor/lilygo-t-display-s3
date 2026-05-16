FROM python:3.12-slim

# Deps de sistema: libdbus pra dbus-next, ca-certs pra MQTT TLS futuro
RUN apt-get update && apt-get install -y --no-install-recommends \
      libdbus-1-3 dbus ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

# Non-root: precisa bater com UID/GID do user no host (passado via `user:` no compose)
USER 1000:1000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python", "/app/entrypoint.py"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python /app/healthcheck.py || exit 1

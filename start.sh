#!/bin/bash
# Production start script for Render / Gunicorn + Flask-SocketIO
set -e

echo "=========================================="
echo "Starting EmmaStudio"
echo "=========================================="

# Render provides PORT. Do not hard-code the production HTTP port.
PORT="${PORT:-10000}"

# Flask-SocketIO cannot safely use multiple Gunicorn worker processes without
# sticky sessions + a message queue (Redis/RabbitMQ). EmmaStudio currently
# uses in-process Socket.IO state, so use ONE process and multiple threads.
WORKERS="${WORKERS:-1}"
THREADS="${THREADS:-50}"
TIMEOUT="${TIMEOUT:-120}"
MAX_REQUESTS="${MAX_REQUESTS:-1000}"
MAX_REQUESTS_JITTER="${MAX_REQUESTS_JITTER:-100}"

if [ -n "${RENDER:-}" ]; then
    echo "Detected Render environment"
    # Keep exactly one Gunicorn process for Socket.IO session consistency.
    WORKERS=1
fi

echo "Binding to 0.0.0.0:${PORT}"
echo "Gunicorn workers: ${WORKERS}; threads: ${THREADS}; timeout: ${TIMEOUT}s"

exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --worker-class gthread \
  --threads "${THREADS}" \
  --timeout "${TIMEOUT}" \
  --graceful-timeout 30 \
  --max-requests "${MAX_REQUESTS}" \
  --max-requests-jitter "${MAX_REQUESTS_JITTER}" \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --worker-tmp-dir /dev/shm \
  wsgi:app

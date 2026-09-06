#!/bin/bash
# Start script for Render.com or production deployment

echo "=========================================="
echo "Starting Personal App"
echo "=========================================="

# Get port from environment or use default
PORT=${PORT:-8000}
WORKERS=${WORKERS:-2}  # Use 2 workers for free tier to avoid memory issues
TIMEOUT=${TIMEOUT:-120}
MAX_REQUESTS=${MAX_REQUESTS:-1000}
MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}

# Check if running on Render and adjust worker count if needed
if [ -n "$RENDER" ]; then
    echo "Detected Render environment"
    # Render free tier has limited memory, ensure we don't exceed
    WORKERS=${WORKERS:-2}
fi

# Start Gunicorn with specified configuration
exec gunicorn \
  --bind 0.0.0.0:${PORT} \
  --workers ${WORKERS} \
  --worker-class sync \
  --timeout ${TIMEOUT} \
  --max-requests ${MAX_REQUESTS} \
  --max-requests-jitter ${MAX_REQUESTS_JITTER} \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --worker-tmp-dir /dev/shm \
  --preload \
  wsgi:app

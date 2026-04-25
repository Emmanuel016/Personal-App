#!/bin/bash
# Start script for Render.com deployment

echo "=========================================="
echo "Starting Personal App on Render"
echo "=========================================="

# Bind to 0.0.0.0 (required by Render)
# Default port 8000 (Render exposes it via your assigned URL)
# 4 workers for free tier
# Timeout 120 seconds

exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app

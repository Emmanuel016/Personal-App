#!/bin/bash
# Build script for Render.com deployment
set -e

echo "=========================================="
echo "Building Personal App for Render"
echo "=========================================="

# Update pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify required packages
echo "Verifying Gunicorn installation..."
python -c "import gunicorn; print(f'Gunicorn {gunicorn.__version__} installed')"

echo "=========================================="
echo "Build complete!"
echo "=========================================="

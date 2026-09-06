#!/bin/bash
# Build script for Render.com deployment
set -e

echo "=========================================="
echo "Building Personal App for Render"
echo "=========================================="

# Update pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify required packages
echo "Verifying critical packages..."
python -c "import gunicorn; print(f'✓ Gunicorn {gunicorn.__version__} installed')"
python -c "import flask; print(f'✓ Flask {flask.__version__} installed')"
python -c "import sqlalchemy; print(f'✓ SQLAlchemy {sqlalchemy.__version__} installed')"

# Create necessary directories
echo "Creating directories..."
mkdir -p uploads
mkdir -p instance

# Set permissions
echo "Setting permissions..."
chmod +x start.sh

# If running on Render, ensure uploads directory is ready for disk mount
if [ -n "$RENDER" ]; then
    echo "Detected Render environment - preparing for disk mount"
    # The disk will be mounted at /opt/render/project/uploads
    # Ensure local uploads directory exists as fallback
    mkdir -p /opt/render/project/uploads 2>/dev/null || true
fi

echo "=========================================="
echo "Build complete!"
echo "=========================================="

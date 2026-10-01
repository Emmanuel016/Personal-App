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
# Run migration before app starts
if python -c "from models import db; from flask import Flask; import os; app = Flask(__name__); app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///personalapp.db'); db.init_app(app); with app.app_context(): from sqlalchemy import inspect; print('file_content' in [c['name'] for c in inspect(db.engine).get_columns('file_attachments')])" 2>/dev/null | grep -q "True"; then
    echo "Running migration to remove file_content column..."
    python migrate_remove_file_content.py
else
    echo "Migration already applied, skipping..."
fi

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

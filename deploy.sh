#!/bin/bash
echo "=== AZURE DEPLOYMENT SCRIPT ==="

# Install dependencies
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Verifying installations..."
python3 -c "import fastapi, uvicorn, gunicorn; print('All dependencies installed successfully')"

echo "=== DEPLOYMENT COMPLETE ===" 
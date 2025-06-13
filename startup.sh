#!/bin/bash
echo "=== ELLA FastAPI Startup Script ==="
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "PORT environment variable: $PORT"
echo "Files in current directory:"
ls -la

echo "=== Checking Python modules ==="
python -c "import fastapi; print('✅ FastAPI available')" || echo "❌ FastAPI not available"
python -c "import uvicorn; print('✅ Uvicorn available')" || echo "❌ Uvicorn not available"
python -c "import gunicorn; print('✅ Gunicorn available')" || echo "❌ Gunicorn not available"

echo "=== Testing main module import ==="
python -c "import main; print('✅ Main module imports successfully')" || echo "❌ Main module import failed"

echo "=== Starting FastAPI application ==="
echo "Command: gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 600 --access-logfile '-' --error-logfile '-' main:app"

exec gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 600 --access-logfile '-' --error-logfile '-' main:app 
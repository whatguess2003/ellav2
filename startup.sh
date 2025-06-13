#!/bin/bash
set -e

echo "=== ELLA STARTUP SCRIPT ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

echo "=== INSTALLING MINIMAL DEPENDENCIES FIRST ==="
pip install --upgrade pip
pip install fastapi==0.95.2 uvicorn==0.24.0 gunicorn==21.2.0 --no-cache-dir --force-reinstall

echo "=== VERIFYING CORE INSTALLATIONS ==="
python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)"
python -c "import uvicorn; print('✅ Uvicorn:', uvicorn.__version__)"
python -c "import gunicorn; print('✅ Gunicorn:', gunicorn.__version__)"

echo "=== INSTALLING REMAINING DEPENDENCIES ==="
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --no-cache-dir
else
    echo "⚠️ requirements.txt not found, using minimal setup"
fi

echo "=== TESTING APP IMPORT ==="
python -c "from app import app; print('✅ App imports successfully')" || {
    echo "❌ App import failed, trying to install missing dependencies..."
    pip install requests python-dotenv pydantic --no-cache-dir
    python -c "from app import app; print('✅ App imports successfully after retry')"
}

echo "=== STARTING APPLICATION ==="
echo "Command: gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 600 app:app"

exec gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 600 app:app 
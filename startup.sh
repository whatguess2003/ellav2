#!/bin/bash

echo "=== ELLA STARTUP SCRIPT ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo "Pip version: $(pip3 --version)"

# Check if virtual environment exists
if [ ! -d "antenv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv antenv
    source antenv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Dependencies installed successfully"
else
    echo "Virtual environment found. Activating..."
    source antenv/bin/activate
fi

# Verify critical packages are installed
echo "Checking critical packages..."
python3 -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2>/dev/null || {
    echo "FastAPI not found. Installing dependencies..."
    pip install -r requirements.txt
}

python3 -c "import uvicorn; print('Uvicorn:', uvicorn.__version__)" 2>/dev/null || {
    echo "Uvicorn not found. Installing dependencies..."
    pip install -r requirements.txt
}

python3 -c "import gunicorn; print('Gunicorn:', gunicorn.__version__)" 2>/dev/null || {
    echo "Gunicorn not found. Installing dependencies..."
    pip install -r requirements.txt
}

echo "All dependencies verified. Starting application..."

# Start the application
exec gunicorn --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 app:app 
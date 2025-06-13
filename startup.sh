#!/bin/bash
echo "Starting ELLA application..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Files in directory: $(ls -la)"

# Install dependencies if needed
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the application
echo "Starting uvicorn server..."
python -m uvicorn main:app --host 0.0.0.0 --port $PORT 
#!/bin/bash
echo "=== POST-BUILD SCRIPT STARTING ==="
echo "Checking if virtual environment was created:"
if [ -d "antenv" ]; then
    echo "Virtual environment 'antenv' found"
    echo "Checking installed packages:"
    source antenv/bin/activate
    pip list | grep -E "(fastapi|uvicorn|gunicorn)"
else
    echo "ERROR: Virtual environment 'antenv' not found!"
fi

echo "Checking if __oryx_packages__ directory exists:"
if [ -d "__oryx_packages__" ]; then
    echo "__oryx_packages__ directory found"
    ls -la __oryx_packages__/
else
    echo "ERROR: __oryx_packages__ directory not found!"
fi

echo "=== POST-BUILD SCRIPT COMPLETED ===" 
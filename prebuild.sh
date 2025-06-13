#!/bin/bash
echo "=== PRE-BUILD SCRIPT STARTING ==="
echo "Python version: $(python3 --version)"
echo "Pip version: $(pip3 --version)"
echo "Current directory: $(pwd)"
echo "Contents of current directory:"
ls -la
echo "Checking requirements.txt:"
if [ -f "requirements.txt" ]; then
    echo "requirements.txt found:"
    cat requirements.txt
else
    echo "ERROR: requirements.txt not found!"
fi
echo "=== PRE-BUILD SCRIPT COMPLETED ===" 
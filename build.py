#!/usr/bin/env python3
"""
Build script to ensure dependencies are installed for Azure deployment
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print the result"""
    print(f"\n=== {description} ===")
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    print("=== PYTHON BUILD SCRIPT STARTING ===")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Directory contents: {os.listdir('.')}")
    
    # Check if requirements.txt exists
    if not os.path.exists('requirements.txt'):
        print("ERROR: requirements.txt not found!")
        sys.exit(1)
    
    # Show requirements.txt content
    with open('requirements.txt', 'r') as f:
        print(f"requirements.txt content:\n{f.read()}")
    
    # Install dependencies
    success = run_command(
        "pip install -r requirements.txt", 
        "Installing dependencies from requirements.txt"
    )
    
    if success:
        print("=== BUILD SUCCESSFUL ===")
    else:
        print("=== BUILD FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Railway Deployment Script
Sets up PostgreSQL database and starts the application
"""

import os
import sys
import subprocess
import time

def setup_database():
    """Set up PostgreSQL database on Railway"""
    print("🚀 Setting up PostgreSQL database...")
    
    try:
        # Check if we're in Railway environment
        if not (os.getenv('DATABASE_URL') or os.getenv('PGHOST')):
            print("⚠️ Not in Railway environment, skipping database setup")
            return True
        
        # Run database setup
        result = subprocess.run([
            sys.executable, 
            'database/postgresql_setup.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database setup completed successfully")
            print(result.stdout)
            return True
        else:
            print("❌ Database setup failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting ELLA Hotel Assistant...")
    
    port = os.getenv('PORT', '8000')
    
    # Start with uvicorn
    subprocess.run([
        'uvicorn', 
        'main:app', 
        '--host', '0.0.0.0', 
        '--port', port,
        '--workers', '1'
    ])

if __name__ == "__main__":
    print("🏨 ELLA Hotel Assistant - Railway Deployment")
    
    # Setup database first
    if setup_database():
        print("✅ Database ready, starting application...")
        time.sleep(2)  # Give database a moment
        start_application()
    else:
        print("❌ Database setup failed, starting application anyway...")
        start_application() 
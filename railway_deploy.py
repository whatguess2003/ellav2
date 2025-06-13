#!/usr/bin/env python3
"""
Railway Deployment Script
Starts the ELLA Hotel Assistant application
Database setup is handled separately via ella-database-setup repository
"""

import os
import subprocess

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
    print("📋 Database setup: Use ella-database-setup repository")
    print("🔗 https://github.com/whatguess2003/ella-database-setup")
    
    start_application() 
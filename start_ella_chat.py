#!/usr/bin/env python3
"""
Quick start script for ELLA Chat Server
This starts the chat server that serves the ELLA chat interface
"""

import uvicorn
import sys
import os

def start_ella_chat():
    """Start ELLA chat server"""
    print("🤖 Starting ELLA Chat Server...")
    print("Chat Interface: http://localhost:8000")
    print("Dashboard: http://localhost:8000/static/index.html")
    print("API Health: http://localhost:8000/health")
    print("-" * 50)
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 ELLA Chat Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    start_ella_chat() 
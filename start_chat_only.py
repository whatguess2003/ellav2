#!/usr/bin/env python3
"""
Start only the ELLA Chat Server (guest chat interface only)
"""
import uvicorn

def start_chat_server():
    print("💬 Starting ELLA Chat Server (Chat Only)...")
    print("   • Chat Interface: http://localhost:8000")
    print("   • API Health: http://localhost:8000/health")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_chat_server() 
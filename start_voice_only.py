#!/usr/bin/env python3
"""
Start only the ELLA Voice Server (for voice chat and voice hotel assistant)
"""
import uvicorn

def start_voice_server():
    print("🎤 Starting ELLA Voice Server...")
    print("   • WebSocket: /voice/realtime_hotel")
    print("   • Health: /voice/health")
    uvicorn.run(
        "voice_hotel.server:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_voice_server() 
#!/usr/bin/env python3
"""
🏨 PMS-ONLY SERVER STARTUP
LEON Property Management System
Hotel staff interface only - NO CHAT functionality
"""

import uvicorn
import sys
import os
from pathlib import Path

def start_pms_server():
    """Start ONLY the PMS server for hotel staff"""
    print("🏨 STARTING LEON PMS - Property Management System")
    print("=" * 60)
    print("🎯 TARGET USERS: Hotel Staff & Property Managers")
    print("🚫 CHAT SYSTEM: DISABLED (Completely Separate)")
    print("📍 PMS INTERFACE: http://localhost:8001")
    print("=" * 60)
    
    # Change to PMS directory structure (future)
    # For now, use existing main.py but restrict to PMS only
    
    try:
        # Start PMS server on port 8001
        uvicorn.run(
            "main:app",  # Will be changed to pms_system.backend.pms_main:app later
            host="0.0.0.0",
            port=8001,
            reload=True,
            reload_dirs=[".", "static", "pms_system"],  # Only PMS-related dirs
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 PMS Server stopped by user")
    except Exception as e:
        print(f"❌ PMS Server error: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏨 LEON PMS - PROPERTY MANAGEMENT SYSTEM ONLY")
    print("="*60)
    print("📋 FEATURES:")
    print("   • Room Management & Assignments")
    print("   • Check-in/Check-out Operations")
    print("   • Booking Management")
    print("   • Inventory Control")
    print("   • Staff Dashboard")
    print("   • Calendar Operations")
    print("\n🚫 DISABLED:")
    print("   • Guest Chat Interface")
    print("   • WhatsApp-style Chat") 
    print("   • Voice Assistant")
    print("   • AI Chat Tools")
    print("="*60)
    
    start_pms_server() 
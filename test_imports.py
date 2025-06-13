#!/usr/bin/env python3
"""
Test script to identify import issues that might cause Azure deployment failure
"""

print("🔍 Testing imports...")

try:
    print("1. Testing FastAPI...")
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    print("✅ FastAPI imports successful")
except Exception as e:
    print(f"❌ FastAPI imports failed: {e}")

try:
    print("2. Testing standard libraries...")
    import json, os, uuid, mimetypes
    from pathlib import Path
    from typing import Optional, List
    from datetime import datetime
    print("✅ Standard library imports successful")
except Exception as e:
    print(f"❌ Standard library imports failed: {e}")

try:
    print("3. Testing Redis...")
    import redis
    print("✅ Redis import successful")
except Exception as e:
    print(f"❌ Redis import failed: {e}")

try:
    print("4. Testing core modules...")
    from core.guest_id import get_guest_id
    print("✅ Core modules successful")
except Exception as e:
    print(f"❌ Core modules failed: {e}")

try:
    print("5. Testing memory modules...")
    from memory.redis_memory import append_dialog_turn, get_dialog_history
    print("✅ Memory modules successful")
except Exception as e:
    print(f"❌ Memory modules failed: {e}")

try:
    print("6. Testing WhatsApp integration...")
    from whatsapp_business_api import WhatsAppBusinessAPI
    print("✅ WhatsApp integration successful")
except Exception as e:
    print(f"❌ WhatsApp integration failed: {e}")

try:
    print("7. Testing chat assistant...")
    from chat_assistant import get_chat_agent
    print("✅ Chat assistant successful")
except Exception as e:
    print(f"❌ Chat assistant failed: {e}")

print("\n🎯 Import test complete!") 
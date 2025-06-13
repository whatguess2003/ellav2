#!/usr/bin/env python3
"""
ELLA Development Setup and Testing Script
Helps manage local development when dependencies differ from Azure
"""

import subprocess
import sys
import os

def install_dev_dependencies():
    """Install local development dependencies"""
    print("🔧 Installing local development dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"])
        print("✅ Development dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def test_imports():
    """Test if all critical imports work"""
    print("\n🔍 Testing imports...")
    
    tests = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("Redis", "import redis"),
        ("OpenAI", "import openai"),
        ("Langchain", "from langchain_openai import ChatOpenAI"),
        ("Core modules", "from core.guest_id import get_guest_id"),
        ("Memory", "from memory.redis_memory import get_dialog_history"),
        ("WhatsApp", "from whatsapp_business_api import WhatsAppBusinessAPI"),
    ]
    
    results = []
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}")
            results.append(True)
        except Exception as e:
            print(f"❌ {name}: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Import Success Rate: {success_rate:.1f}%")
    return all(results)

def run_local_server():
    """Run the local development server"""
    print("\n🚀 Starting local development server...")
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")

def create_env_template():
    """Create a .env template for local development"""
    env_template = """# ELLA Local Development Environment Variables
# Copy this to .env and fill in your actual values

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your-whatsapp-access-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-account-id
WHATSAPP_VERIFY_TOKEN=ella_verify_token_2024
WHATSAPP_API_VERSION=v22.0

# Database
REDIS_URL=redis://localhost:6379/0
MONGO_URI=mongodb://localhost:27017
MONGO_DB=ella_db
DATABASE_PATH=ella_hotel_assistant.db

# Optional: ElevenLabs for voice
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=UcqZLa941Kkt8ZhEEybf
"""
    
    with open(".env.template", "w") as f:
        f.write(env_template)
    
    print("📝 Created .env.template - copy to .env and add your API keys")

def main():
    """Main development setup menu"""
    print("🛠️ ELLA Development Setup")
    print("=" * 40)
    
    while True:
        print("\nChoose an option:")
        print("1. Install development dependencies")
        print("2. Test imports")
        print("3. Create .env template")
        print("4. Run local server")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            install_dev_dependencies()
        elif choice == "2":
            test_imports()
        elif choice == "3":
            create_env_template()
        elif choice == "4":
            if test_imports():
                run_local_server()
            else:
                print("❌ Cannot start server - fix import issues first")
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main() 
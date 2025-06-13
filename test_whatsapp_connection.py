#!/usr/bin/env python3
"""
Test WhatsApp Business API Connection
"""
import asyncio
import httpx
import json
from settings import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_VERSION
)

async def test_whatsapp_connection():
    """Test the WhatsApp Business API connection"""
    
    base_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n🔑 Configuration:")
    print(f"API Version: {WHATSAPP_API_VERSION}")
    print(f"Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"Access Token (first 20 chars): {WHATSAPP_ACCESS_TOKEN[:20]}...")
    
    # Test 1: Get phone number details
    try:
        print("\n📱 Testing phone number details...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/{WHATSAPP_PHONE_NUMBER_ID}",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"❌ Error Response ({response.status_code}):")
                print(json.dumps(response.json(), indent=2))
                return
                
            phone_details = response.json()
            print("✅ Phone number details retrieved successfully:")
            print(f"Phone Number: {phone_details.get('display_phone_number')}")
            print(f"Quality Rating: {phone_details.get('quality_rating')}")
            print(f"Verified Name: {phone_details.get('verified_name')}")
    except Exception as e:
        print(f"❌ Failed to get phone number details: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        return
    
    # Test 2: Send a test message
    try:
        test_number = input("\n📲 Enter a phone number to send test message (with country code, e.g., +1234567890): ")
        message_data = {
            "messaging_product": "whatsapp",
            "to": test_number,
            "type": "text",
            "text": {
                "body": "Hello! This is a test message from your WhatsApp Business API integration. 🚀"
            }
        }
        
        print("\n📤 Sending test message...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers=headers,
                json=message_data
            )
            
            if response.status_code != 200:
                print(f"❌ Error Response ({response.status_code}):")
                print(json.dumps(response.json(), indent=2))
                return
                
            result = response.json()
            print("\n✅ Test message sent successfully!")
            print(f"Message ID: {result.get('messages', [{}])[0].get('id')}")
    except Exception as e:
        print(f"❌ Failed to send test message: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    print("🔍 Testing WhatsApp Business API Connection...")
    asyncio.run(test_whatsapp_connection()) 
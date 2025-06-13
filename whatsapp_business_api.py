#!/usr/bin/env python3
"""
WhatsApp Business API Media Handler
Direct integration with Meta's WhatsApp Business API

Hotel Staff → WhatsApp Business API → Local Storage → Database → Guest Access
"""
import os
import json
import sqlite3
import asyncio
import tempfile
import time
import base64
import httpx
import shutil
from typing import Dict, Optional, List
from flask import Flask, request

# Optional AI imports
try:
    from langchain_openai import ChatOpenAI
    AI_AVAILABLE = True
except ImportError:
    print("⚠️ langchain_openai not available - AI features disabled")
    AI_AVAILABLE = False
    ChatOpenAI = None

# Environment variables
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "ella_verify_token_2024")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v22.0")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "ella_hotel_assistant.db")

# Initialize AI client (optional)
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0.3) if AI_AVAILABLE and OPENAI_API_KEY and ChatOpenAI else None

class WhatsAppBusinessAPI:
    """Direct WhatsApp Business API integration for hotel photo uploads"""
    
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Create local media storage directory
        self.media_dir = "media_storage/whatsapp_uploads"
        os.makedirs(self.media_dir, exist_ok=True)
        
        print("🟢 WhatsApp Business API initialized (Local Storage)")
        if not WHATSAPP_ACCESS_TOKEN:
            print("⚠️ WHATSAPP_ACCESS_TOKEN not set")
        if not WHATSAPP_PHONE_NUMBER_ID:
            print("⚠️ WHATSAPP_PHONE_NUMBER_ID not set")
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process incoming webhook from WhatsApp Business API"""
        
        try:
            print(f"📱 WhatsApp Business API webhook received")
            print(f"Data: {json.dumps(webhook_data, indent=2)}")
            
            # WhatsApp Business API webhook structure
            if "entry" not in webhook_data:
                return {"success": False, "error": "Invalid webhook format"}
            
            processed_messages = 0
            
            for entry in webhook_data["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            
                            # Process messages
                            messages = value.get("messages", [])
                            for message in messages:
                                await self._process_message(message, value)
                                processed_messages += 1
                            
                            # Mark messages as read
                            await self._mark_messages_as_read(value)
            
            return {"success": True, "processed_messages": processed_messages}
            
        except Exception as e:
            print(f"❌ Webhook processing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_message(self, message: Dict, webhook_value: Dict):
        """Process individual WhatsApp message"""
        
        try:
            message_id = message.get("id")
            from_number = message.get("from")
            message_type = message.get("type")
            timestamp = message.get("timestamp")
            
            print(f"📨 Processing message from {from_number}, type: {message_type}")
            
            if message_type == "image":
                # Handle image upload
                image_data = message.get("image", {})
                media_id = image_data.get("id")
                caption = image_data.get("caption", "")
                mime_type = image_data.get("mime_type", "image/jpeg")
                
                if media_id:
                    await self._process_image_upload(media_id, caption, from_number, mime_type)
                else:
                    print("⚠️ No media_id found in image message")
            
            elif message_type == "text":
                # Handle text message - send instructions
                text_body = message.get("text", {}).get("body", "")
                await self._send_upload_instructions(from_number)
            
            elif message_type in ["video", "document"]:
                # Handle other media types
                await self._send_message(from_number, "📸 Please send images only (JPG, PNG). Videos and documents are not supported yet.")
            
            else:
                print(f"⚠️ Unsupported message type: {message_type}")
                
        except Exception as e:
            print(f"❌ Message processing error: {e}")
    
    async def _process_image_upload(self, media_id: str, caption: str, sender: str, mime_type: str):
        """Process uploaded image from WhatsApp"""
        
        try:
            print(f"📸 Processing image upload - Media ID: {media_id}")
            print(f"💬 Caption: {caption}")
            print(f"📧 From: {sender}")
            
            # Step 1: Get media URL from WhatsApp
            media_url = await self._get_media_url(media_id)
            if not media_url:
                await self._send_message(sender, "❌ Failed to retrieve image. Please try again.")
                return
            
            # Step 2: Download media from WhatsApp servers
            temp_file_path = await self._download_media(media_url, mime_type)
            if not temp_file_path:
                await self._send_message(sender, "❌ Failed to download image. Please try again.")
                return
            
            # Step 3: AI analysis to determine hotel and category
            analysis = await self._analyze_upload_content(caption, sender)
            
            # Step 4: Generate guest-friendly description using AI
            guest_description = await self._generate_guest_description(temp_file_path, analysis)
            
            # Step 5: Save to local storage with descriptive naming
            storage_result = await self._save_to_local_storage(temp_file_path, analysis, guest_description)
            
            # Step 6: Clean up temporary file immediately
            try:
                os.unlink(temp_file_path)
                print(f"🗑️ Cleaned up temp file: {temp_file_path}")
            except:
                pass
            
            if not storage_result["success"]:
                await self._send_message(sender, f"❌ Upload failed: {storage_result['error']}")
                return
            
            # Step 7: Update database for guest access via media_sharer.py
            db_update_result = await self._update_database_for_guest_access(
                analysis, storage_result["file_url"], guest_description
            )
            
            if db_update_result["success"]:
                # Step 8: Send success confirmation
                await self._send_upload_confirmation(sender, {
                    "success": True,
                    "file_url": storage_result["file_url"],
                    "description": guest_description,
                    "hotel": analysis["hotel_name"],
                    "category": analysis["category"],
                    "features": analysis["features"]
                })
            else:
                await self._send_message(sender, f"❌ Database update failed: {db_update_result['error']}")
                
        except Exception as e:
            print(f"❌ Image processing error: {e}")
            await self._send_message(sender, f"❌ Processing failed: {str(e)}")
    
    async def _get_media_url(self, media_id: str) -> Optional[str]:
        """Get media download URL from WhatsApp Business API"""
        
        try:
            print(f"🔍 Getting media URL for ID: {media_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{media_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                media_data = response.json()
                media_url = media_data.get("url")
                
                if media_url:
                    print(f"✅ Media URL retrieved: {media_url[:50]}...")
                    return media_url
                else:
                    print("❌ No URL in media response")
                    return None
                    
        except Exception as e:
            print(f"❌ Failed to get media URL: {e}")
            return None
    
    async def _download_media(self, media_url: str, mime_type: str) -> Optional[str]:
        """Download media from WhatsApp servers to temporary file"""
        
        try:
            print(f"⬇️ Downloading media from WhatsApp servers...")
            
            # Determine file extension
            if "jpeg" in mime_type or "jpg" in mime_type:
                ext = ".jpg"
            elif "png" in mime_type:
                ext = ".png"
            else:
                ext = ".jpg"  # Default
            
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="whatsapp_")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    media_url,
                    headers=self.headers,
                    timeout=60.0
                )
                response.raise_for_status()
                
                # Write to temporary file
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    temp_file.write(response.content)
                
                file_size = len(response.content)
                print(f"✅ Media downloaded: {temp_path} ({file_size} bytes)")
                
                return temp_path
                
        except Exception as e:
            print(f"❌ Media download failed: {e}")
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except:
                pass
            return None
    
    async def _analyze_upload_content(self, caption: str, sender: str) -> Dict:
        """Analyze upload content to determine hotel and category"""
        
        # Simple analysis based on caption
        caption_lower = caption.lower()
        
        # Determine category
        if any(word in caption_lower for word in ["room", "bedroom", "suite", "bathroom", "bed"]):
            category = "room"
        elif any(word in caption_lower for word in ["pool", "spa", "gym", "restaurant", "facility"]):
            category = "facility"
        else:
            category = "hotel"
        
        # Extract hotel name (simple approach)
        hotel_name = "Default Hotel"
        if " - " in caption:
            parts = caption.split(" - ")
            hotel_name = parts[0].strip()
        elif "hotel" in caption_lower:
            words = caption.split()
            for i, word in enumerate(words):
                if "hotel" in word.lower() and i > 0:
                    hotel_name = " ".join(words[:i+1])
                    break
        
        # Generate features description
        features = caption.replace(hotel_name, "").replace(" - ", "").strip()
        if not features:
            features = f"{category} photo"
        
        return {
            "hotel_name": hotel_name,
            "hotel_id": hotel_name.lower().replace(" ", "_"),
            "category": category,
            "features": features
        }
    
    async def _generate_guest_description(self, image_path: str, analysis: Dict) -> str:
        """Generate guest-friendly description using AI (optional)"""
        
        if llm and AI_AVAILABLE:
            try:
                prompt = f"""Generate a brief, appealing description for this {analysis['category']} photo from {analysis['hotel_name']}.
                
                Features mentioned: {analysis['features']}
                Category: {analysis['category']}
                
                Write a 1-2 sentence description that would appeal to hotel guests. Be descriptive but concise."""
                
                response = llm.invoke([{
                    "role": "user", 
                    "content": prompt
                }])
                
                description = response.content.strip()[:100]  # Limit length
                print(f"🤖 AI Description: {description}")
                return description
                
            except Exception as e:
                print(f"⚠️ AI description generation failed: {e}")
        
        # Fallback description
        return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
    
    async def _save_to_local_storage(self, file_path: str, analysis: Dict, description: str) -> Dict:
        """Save to local storage with descriptive naming"""
        
        try:
            # Generate descriptive filename
            hotel_name = analysis["hotel_name"].replace(" ", "_").replace("-", "_")
            category = analysis["category"]
            timestamp = int(time.time())
            
            local_filename = f"{hotel_name}_{category}_{timestamp}.jpg"
            local_path = os.path.join(self.media_dir, local_filename)
            
            # Copy file to local storage
            shutil.copy2(file_path, local_path)
            
            # Generate URL for serving
            file_url = f"/media/{local_filename}"
            
            print(f"✅ Local storage successful: {local_path}")
            
            return {
                "success": True,
                "file_url": file_url,
                "local_path": local_path,
                "filename": local_filename
            }
            
        except Exception as e:
            print(f"❌ Local storage failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_database_for_guest_access(self, analysis: Dict, file_url: str, description: str) -> Dict:
        """Update database photo_urls column so media_sharer.py can find photos for guest requests"""
        
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # Photo entry for database
                photo_entry = {
                    "url": file_url,
                    "description": description
                }
                
                if analysis["category"] == "room":
                    # Update room_types table
                    cursor.execute("""
                        SELECT property_id, photo_urls FROM room_types rt
                        JOIN hotels h ON rt.property_id = h.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?) LIMIT 1
                    """, [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        property_id, existing_photos = result
                        
                        # Parse existing JSON or create new structure
                        if existing_photos:
                            photos_data = json.loads(existing_photos)
                        else:
                            photos_data = {"room_photos": []}
                        
                        # Add to room_photos array
                        if "room_photos" not in photos_data:
                            photos_data["room_photos"] = []
                        photos_data["room_photos"].append(photo_entry)
                        
                        # Update database
                        cursor.execute(
                            "UPDATE room_types SET photo_urls = ? WHERE property_id = ?",
                            [json.dumps(photos_data), property_id]
                        )
                        
                        print(f"✅ Updated room photos in database for property_id: {property_id}")
                    else:
                        print(f"⚠️ No room type found for hotel: {analysis['hotel_name']}")
                
                else:
                    # Update hotels table for hotel/facility photos
                    cursor.execute(
                        "SELECT photo_urls FROM hotels WHERE LOWER(hotel_name) LIKE LOWER(?)",
                        [f"%{analysis['hotel_name']}%"]
                    )
                    
                    result = cursor.fetchone()
                    if result:
                        existing_photos = result[0]
                        
                        # Parse existing JSON or create new structure
                        if existing_photos:
                            photos_data = json.loads(existing_photos)
                        else:
                            photos_data = {"hotel_photos": [], "facility_photos": []}
                        
                        # Add to appropriate category
                        if analysis["category"] == "facility":
                            if "facility_photos" not in photos_data:
                                photos_data["facility_photos"] = []
                            photos_data["facility_photos"].append(photo_entry)
                        else:  # hotel category
                            if "hotel_photos" not in photos_data:
                                photos_data["hotel_photos"] = []
                            photos_data["hotel_photos"].append(photo_entry)
                        
                        # Update database
                        cursor.execute(
                            "UPDATE hotels SET photo_urls = ? WHERE LOWER(hotel_name) LIKE LOWER(?)",
                            [json.dumps(photos_data), f"%{analysis['hotel_name']}%"]
                        )
                        
                        print(f"✅ Updated {analysis['category']} photos in database for hotel: {analysis['hotel_name']}")
                    else:
                        print(f"⚠️ No hotel found: {analysis['hotel_name']}")
                
                conn.commit()
                return {"success": True}
                
        except Exception as e:
            print(f"❌ Database update failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_upload_confirmation(self, phone_number: str, upload_result: Dict):
        """Send success confirmation to hotel staff via WhatsApp"""
        
        confirmation_message = f"""✅ Photo uploaded successfully!

🏨 Hotel: {upload_result['hotel']}
📂 Category: {upload_result['category'].title()}
🏷️ Features: {upload_result['features']}
🤖 Description: {upload_result['description']}

📋 Ready for guest access!

Guests can now request:
• "Show me {upload_result['category']} photos"
• "I want to see hotel images"
• "Share room pictures"

💾 Stored locally for fast access"""
        
        await self._send_message(phone_number, confirmation_message)
    
    async def _send_upload_instructions(self, phone_number: str):
        """Send usage instructions for photo uploads"""
        
        instructions = """📸 Hotel Photo Upload Instructions:

1. Send a photo with description
2. Example: "Grand Hyatt - Deluxe king room"
3. AI will categorize automatically
4. Photo becomes available for guest requests

Categories:
• Room: bedrooms, suites, bathrooms
• Hotel: lobby, exterior, entrance
• Facility: pool, spa, gym, restaurant

Just send your photo with a description! 📷"""
        
        await self._send_message(phone_number, instructions)
    
    async def _send_message(self, phone_number: str, message: str):
        """Send message via WhatsApp Business API"""
        
        try:
            message_data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                    headers=self.headers,
                    json=message_data,
                    timeout=30.0
                )
                response.raise_for_status()
                
                print(f"✅ Message sent to {phone_number}")
                
        except Exception as e:
            print(f"❌ Failed to send message to {phone_number}: {e}")
    
    async def _mark_messages_as_read(self, webhook_value: Dict):
        """Mark messages as read to avoid processing duplicates"""
        
        try:
            messages = webhook_value.get("messages", [])
            
            for message in messages:
                message_id = message.get("id")
                if message_id:
                    read_data = {
                        "messaging_product": "whatsapp",
                        "status": "read",
                        "message_id": message_id
                    }
                    
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"{self.base_url}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                            headers=self.headers,
                            json=read_data,
                            timeout=10.0
                        )
                        
        except Exception as e:
            print(f"⚠️ Failed to mark messages as read: {e}")

# Flask webhook server
app = Flask(__name__)
whatsapp_api = WhatsAppBusinessAPI()

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp Business API setup"""
    
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"🔍 Webhook verification: mode={mode}, token={token}")
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        print("✅ Webhook verified successfully")
        return challenge
    else:
        print("❌ Webhook verification failed")
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """WhatsApp Business API webhook endpoint"""
    
    try:
        webhook_data = request.get_json()
        
        if not webhook_data:
            return {"status": "error", "message": "No JSON data"}, 400
        
        # Process webhook asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(whatsapp_api.process_webhook(webhook_data))
        loop.close()
        
        return {"status": "ok", "result": result}, 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "whatsapp-business-api-media-handler",
        "storage": "local",
        "integrates_with": "media_sharer.py",
        "api_configured": bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)
    }, 200

if __name__ == "__main__":
    print("🚀 WHATSAPP BUSINESS API MEDIA HANDLER")
    print("="*50)
    print("📱 Direct integration with Meta's WhatsApp Business API")
    print("💾 Local storage (no AWS dependencies)")
    print("📸 Hotel Staff → WhatsApp → Local Storage → Database → Guest Access")
    print("🌐 Webhook URL: http://localhost:5000/webhook")
    print("⚙️ Configure this URL in Meta Business Manager")
    print("="*50)
    
    if not WHATSAPP_ACCESS_TOKEN:
        print("⚠️ Set WHATSAPP_ACCESS_TOKEN environment variable")
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("⚠️ Set WHATSAPP_PHONE_NUMBER_ID environment variable")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 
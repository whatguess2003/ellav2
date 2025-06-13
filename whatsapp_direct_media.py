#!/usr/bin/env python3
"""
Direct WhatsApp Business API Media Handler
Alternative to Twilio - uses Meta's WhatsApp Business API directly

Hotel Staff → WhatsApp Business API → S3 → Database → Guest Access
"""

import os
import json
import sqlite3
import asyncio
import tempfile
import time
import boto3
import base64
import requests
from typing import Dict, Optional
from flask import Flask, request

# WhatsApp Business API imports
import httpx

# AI imports
from langchain_openai import ChatOpenAI

# Configuration
WHATSAPP_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')  # From Meta Business
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
***REMOVED*** = os.getenv('***REMOVED***')
AWS_BUCKET_NAME = "ella-hotel-media"

# Initialize clients
s3_client = boto3.client('s3', region_name='ap-southeast-1')
llm = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o", temperature=0.3) if ***REMOVED*** else None

class WhatsAppDirectMediaHandler:
    """Direct WhatsApp Business API media handling"""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process webhook from WhatsApp Business API"""
        
        try:
            print(f"📱 WhatsApp Business API webhook: {json.dumps(webhook_data, indent=2)}")
            
            # Extract webhook data (different format from Twilio)
            if "entry" not in webhook_data:
                return {"success": False, "error": "Invalid webhook format"}
            
            for entry in webhook_data["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            messages = value.get("messages", [])
                            
                            for message in messages:
                                await self._process_single_message(message, value)
            
            return {"success": True}
            
        except Exception as e:
            print(f"❌ Webhook processing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_single_message(self, message: Dict, value: Dict):
        """Process individual WhatsApp message"""
        
        try:
            message_id = message.get("id")
            from_number = message.get("from")
            message_type = message.get("type")
            
            print(f"📨 Message from {from_number}, type: {message_type}")
            
            if message_type == "image":
                # Handle image message
                image_data = message.get("image", {})
                media_id = image_data.get("id")
                caption = image_data.get("caption", "")
                
                if media_id:
                    await self._process_image_media(media_id, caption, from_number)
            
            elif message_type == "text":
                # Handle text message
                text_body = message.get("text", {}).get("body", "")
                await self._send_instructions(from_number)
                
        except Exception as e:
            print(f"❌ Message processing error: {e}")
    
    async def _process_image_media(self, media_id: str, caption: str, sender: str):
        """Process image media from WhatsApp"""
        
        try:
            print(f"📸 Processing image media_id: {media_id}")
            
            # Step 1: Get media URL from WhatsApp
            media_url = await self._get_media_url(media_id)
            if not media_url:
                return
            
            # Step 2: Download media
            temp_file = await self._download_media(media_url)
            if not temp_file:
                return
            
            # Step 3: AI analysis
            analysis = await self._analyze_content(caption, sender)
            
            # Step 4: Generate guest description
            description = await self._generate_description(temp_file, analysis)
            
            # Step 5: Upload to S3
            s3_url = await self._upload_to_s3(temp_file, analysis, description)
            
            # Step 6: Update database
            if s3_url:
                await self._update_database(analysis, s3_url, description)
                await self._send_confirmation(sender, {
                    "success": True,
                    "s3_url": s3_url,
                    "description": description,
                    "hotel": analysis["hotel_name"],
                    "category": analysis["category"]
                })
            
            # Step 7: Cleanup
            try:
                os.unlink(temp_file)
            except:
                pass
                
        except Exception as e:
            print(f"❌ Image processing error: {e}")
    
    async def _get_media_url(self, media_id: str) -> Optional[str]:
        """Get media download URL from WhatsApp Business API"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{media_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                media_info = response.json()
                media_url = media_info.get("url")
                
                print(f"✅ Got media URL: {media_url}")
                return media_url
                
        except Exception as e:
            print(f"❌ Failed to get media URL: {e}")
            return None
    
    async def _download_media(self, media_url: str) -> Optional[str]:
        """Download media from WhatsApp servers"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                )
                response.raise_for_status()
                
                # Create temp file
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix='.jpg',
                    prefix=f"whatsapp_{int(time.time())}_"
                )
                
                with temp_file as f:
                    f.write(response.content)
                
                print(f"✅ Downloaded to: {temp_file.name}")
                return temp_file.name
                
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    async def _analyze_content(self, caption: str, sender: str) -> Dict:
        """AI analysis for hotel and category"""
        
        # Same analysis logic as before
        if llm:
            try:
                prompt = f"""
                Analyze WhatsApp media from hotel staff:
                
                CAPTION: {caption}
                SENDER: {sender}
                
                Return JSON:
                {{
                    "hotel_id": "grand_hyatt_kuala_lumpur",
                    "hotel_name": "Grand Hyatt Kuala Lumpur",
                    "category": "room",
                    "features": "deluxe king room"
                }}
                """
                
                response = llm.invoke([{"role": "user", "content": prompt}])
                analysis_text = response.content.strip()
                
                if "```json" in analysis_text:
                    analysis_text = analysis_text.split("```json")[1].split("```")[0]
                
                return json.loads(analysis_text)
                
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
        
        return {
            "hotel_id": "grand_hyatt_kuala_lumpur",
            "hotel_name": "Grand Hyatt Kuala Lumpur",
            "category": "room",
            "features": caption.lower()[:50] if caption else "luxury room"
        }
    
    async def _generate_description(self, image_path: str, analysis: Dict) -> str:
        """Generate guest description"""
        
        try:
            if llm and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                prompt = f"Create appealing 80-char description for {analysis['category']} photo from {analysis['hotel_name']}"
                
                llm_vision = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o-mini")
                response = llm_vision.invoke([{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }])
                
                return response.content.strip()[:100]
                
        except Exception as e:
            print(f"⚠️ Description generation failed: {e}")
        
        return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
    
    async def _upload_to_s3(self, file_path: str, analysis: Dict, description: str) -> Optional[str]:
        """Upload to S3"""
        
        try:
            timestamp = int(time.time())
            features_clean = analysis['features'].replace(' ', '_').lower()[:30]
            filename = f"{analysis['category']}_{features_clean}_{timestamp}.jpg"
            s3_key = f"hotels/{analysis['hotel_id']}/{filename}"
            
            s3_client.upload_file(
                file_path,
                AWS_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read',
                    'Metadata': {
                        'hotel': analysis['hotel_name'],
                        'category': analysis['category'],
                        'description': description,
                        'uploaded_via': 'whatsapp_direct'
                    }
                }
            )
            
            s3_url = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            print(f"✅ S3 upload: {s3_url}")
            return s3_url
            
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None
    
    async def _update_database(self, analysis: Dict, s3_url: str, description: str):
        """Update database"""
        
        # Same database update logic as before
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                photo_entry = {"url": s3_url, "description": description}
                
                if analysis["category"] == "room":
                    cursor.execute("""
                        SELECT property_id, photo_urls FROM room_types rt
                        JOIN hotels h ON rt.property_id = h.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?) LIMIT 1
                    """, [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        property_id, existing = result
                        photos = json.loads(existing) if existing else {"room_photos": []}
                        if "room_photos" not in photos:
                            photos["room_photos"] = []
                        photos["room_photos"].append(photo_entry)
                        
                        cursor.execute("UPDATE room_types SET photo_urls = ? WHERE property_id = ?",
                                     [json.dumps(photos), property_id])
                else:
                    cursor.execute("SELECT photo_urls FROM hotels WHERE LOWER(hotel_name) LIKE LOWER(?)",
                                 [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        existing = result[0]
                        photos = json.loads(existing) if existing else {"hotel_photos": [], "facility_photos": []}
                        
                        if analysis["category"] == "facility":
                            if "facility_photos" not in photos:
                                photos["facility_photos"] = []
                            photos["facility_photos"].append(photo_entry)
                        else:
                            if "hotel_photos" not in photos:
                                photos["hotel_photos"] = []
                            photos["hotel_photos"].append(photo_entry)
                        
                        cursor.execute("UPDATE hotels SET photo_urls = ? WHERE LOWER(hotel_name) LIKE LOWER(?",
                                     [json.dumps(photos), f"%{analysis['hotel_name']}%"])
                
                conn.commit()
                print("✅ Database updated")
                
        except Exception as e:
            print(f"❌ Database update failed: {e}")
    
    async def _send_confirmation(self, phone_number: str, result: Dict):
        """Send confirmation via WhatsApp Business API"""
        
        try:
            confirmation = f"""✅ Photo uploaded!

🏨 {result['hotel']}
📂 {result['category'].title()}
🤖 {result['description']}

Guests can now request this photo!"""
            
            message_data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": confirmation}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                    headers=self.headers,
                    json=message_data
                )
                response.raise_for_status()
                
            print(f"✅ Confirmation sent to {phone_number}")
            
        except Exception as e:
            print(f"❌ Confirmation failed: {e}")
    
    async def _send_instructions(self, phone_number: str):
        """Send usage instructions"""
        
        try:
            instructions = """📸 Send a photo with description:

Example: "Grand Hyatt - Deluxe room"

AI will categorize and make available for guest requests!"""
            
            message_data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": instructions}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                    headers=self.headers,
                    json=message_data
                )
                
        except Exception as e:
            print(f"❌ Instructions failed: {e}")

# Flask webhook server
app = Flask(__name__)
handler = WhatsAppDirectMediaHandler()

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp Business API"""
    
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        return challenge
    else:
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """WhatsApp Business API webhook"""
    
    webhook_data = request.get_json()
    
    # Process asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(handler.process_webhook(webhook_data))
    loop.close()
    
    return {"status": "ok"}, 200

if __name__ == "__main__":
    print("🚀 WHATSAPP BUSINESS API DIRECT MEDIA HANDLER")
    print("📱 Alternative to Twilio for media handling")
    app.run(host='0.0.0.0', port=5000, debug=True) 
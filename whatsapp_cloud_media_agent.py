#!/usr/bin/env python3
"""
Enhanced WhatsApp Media Agent for Cloud Integration
Processes WhatsApp media from hotel staff and uploads to AWS S3
Updates database with photo URLs in JSON format for guest media sharing
"""

from langchain.tools import tool
from langchain_openai import ChatOpenAI
import os
from typing import Dict, Optional, Any
import requests
import asyncio
import json
import sqlite3
from pathlib import Path
import tempfile
import time
import boto3
import base64

# Get OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize AI for content analysis
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0.3)

# AWS Configuration
AWS_BUCKET_NAME = "ella-hotel-media"
AWS_REGION = "ap-southeast-1"

class CloudWhatsAppMediaAgent:
    """Enhanced agent that processes WhatsApp media and uploads to AWS S3 with database integration"""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = AWS_BUCKET_NAME
        self.supported_media_types = {
            'image': ['.jpg', '.jpeg', '.png', '.webp'],
            'video': ['.mp4', '.avi', '.mov'],
            'document': ['.pdf', '.doc', '.docx']
        }
        
        # Initialize AWS S3
        self.initialize_aws()
    
    def initialize_aws(self):
        """Initialize AWS S3 client"""
        try:
            self.s3_client = boto3.client('s3', region_name=AWS_REGION)
            print(f"✅ AWS S3 client initialized for region: {AWS_REGION}")
        except Exception as e:
            print(f"❌ AWS initialization failed: {e}")
            self.s3_client = None
    
    async def process_whatsapp_media(
        self,
        media_url: str,
        media_type: str,
        caption: str = "",
        sender_info: str = "",
        chat_context: str = ""
    ) -> Dict[str, Any]:
        """
        Process WhatsApp media from hotel staff and upload to AWS S3
        
        Args:
            media_url: URL to download the media file
            media_type: Type of media (image, video, document)
            caption: Caption/message with the media
            sender_info: Information about who sent it
            chat_context: Recent chat context for better categorization
            
        Returns:
            Dictionary with processing results
        """
        
        try:
            print(f"📱 WHATSAPP CLOUD MEDIA: Processing {media_type} from {sender_info}")
            
            if not self.s3_client:
                return {"success": False, "error": "AWS S3 not configured"}
            
            # Download the media file temporarily
            temp_file = await self._download_media(media_url, media_type)
            if not temp_file:
                return {"success": False, "error": "Failed to download media"}
            
            # Analyze the content and context using AI
            analysis = await self._analyze_media_content(
                caption, sender_info, chat_context, media_type
            )
            
            if not analysis.get("hotel_id"):
                return {"success": False, "error": "Could not determine hotel context"}
            
            # Generate AI-powered caption for the image
            ai_caption = await self._generate_ai_caption(temp_file, analysis)
            
            # Upload to AWS S3
            s3_result = await self._upload_to_s3(temp_file, analysis, ai_caption)
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            if not s3_result["success"]:
                return {"success": False, "error": s3_result["error"]}
            
            # Update database with photo URL
            db_result = await self._update_database_with_photo_url(
                analysis, s3_result["s3_url"], ai_caption
            )
            
            if db_result["success"]:
                print(f"✅ Media uploaded and database updated successfully")
                
                return {
                    "success": True,
                    "s3_url": s3_result["s3_url"],
                    "ai_caption": ai_caption,
                    "hotel_id": analysis["hotel_id"],
                    "category": analysis["category"], 
                    "database_updated": True,
                    "message": f"""✅ Hotel photo uploaded successfully!
                    
📸 **CLOUD STORAGE**
S3 URL: {s3_result["s3_url"]}
Hotel: {analysis["hotel_name"]}
Category: {analysis["category"]}

🤖 **AI CAPTION**
{ai_caption}

📋 **DATABASE INTEGRATION**
Updated: {analysis["hotel_name"]} photo URLs
Ready for guest photo sharing system

✨ **GUEST ACCESS**
Guests can now request photos using the chat assistant:
- "Show me {analysis['category']} photos from {analysis['hotel_name']}"
- "I want to see the {analysis['features']} room"
- "Share hotel photos with me"
"""
                }
            else:
                return {"success": False, "error": db_result["error"]}
                
        except Exception as e:
            print(f"❌ WhatsApp cloud media processing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _download_media(self, media_url: str, media_type: str) -> Optional[str]:
        """Download media file to temporary location"""
        try:
            print(f"📥 Downloading media from: {media_url}")
            
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            ext_map = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png', 
                'image/webp': '.webp',
                'video/mp4': '.mp4',
                'video/quicktime': '.mov',
                'application/pdf': '.pdf'
            }
            
            file_ext = ext_map.get(content_type, '.jpg')
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_ext, 
                prefix=f"whatsapp_{int(time.time())}_"
            )
            
            with temp_file as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded to: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    async def _analyze_media_content(
        self,
        caption: str,
        sender_info: str,
        chat_context: str,
        media_type: str
    ) -> Dict[str, Any]:
        """Use AI to analyze and categorize the media content"""
        
        # Build analysis prompt
        analysis_prompt = f"""
        Analyze this WhatsApp media from hotel staff and categorize it for guest photo sharing:

        MEDIA TYPE: {media_type}
        CAPTION: {caption}
        SENDER: {sender_info}
        CHAT CONTEXT: {chat_context}

        Determine the hotel and categorize the photo for the guest photo sharing system.

        Extract:
        1. hotel_id: exact hotel identifier
        2. hotel_name: full hotel name
        3. category: "hotel", "room", or "facility"
        4. features: key descriptive features
        5. description: detailed description for photo caption

        HOTEL MAPPING:
        - Grand Hyatt, Hyatt KL → hotel_id: "grand_hyatt_kuala_lumpur", name: "Grand Hyatt Kuala Lumpur"
        - Sam Hotel → hotel_id: "sam_hotel_kl", name: "Sam Hotel Kuala Lumpur"
        - Marina Court, Kota Kinabalu → hotel_id: "marina_court_resort_kk", name: "Marina Court Resort Kota Kinabalu"

        CATEGORY RULES:
        - "hotel": exterior, lobby, entrance, general hotel areas
        - "room": bedrooms, suites, room interiors
        - "facility": pool, spa, gym, restaurant, amenities

        Return as JSON only:
        {{
            "hotel_id": "grand_hyatt_kuala_lumpur",
            "hotel_name": "Grand Hyatt Kuala Lumpur",
            "category": "room",
            "features": "king room city view",
            "description": "Detailed description for guest photo sharing"
        }}
        """
        
        try:
            response = llm.invoke([{"role": "user", "content": analysis_prompt}])
            
            # Parse the JSON response
            analysis_text = response.content.strip()
            
            # Clean up the response to extract JSON
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0]
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1]
            
            analysis = json.loads(analysis_text)
            
            print(f"🧠 AI Analysis: {analysis}")
            return analysis
            
        except Exception as e:
            print(f"⚠️ Analysis failed, using defaults: {e}")
            
            # Fallback analysis
            return {
                "hotel_id": "grand_hyatt_kuala_lumpur",
                "hotel_name": "Grand Hyatt Kuala Lumpur",
                "category": "hotel",
                "features": "luxury hotel",
                "description": f"Hotel photo shared via WhatsApp: {caption[:100]}"
            }
    
    async def _generate_ai_caption(self, image_path: str, analysis: Dict) -> str:
        """Generate AI-powered caption for the image"""
        
        if not os.path.exists(image_path):
            return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
        
        try:
            # Read and encode image for OpenAI Vision
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create hotel-specific prompt
            prompt = f"""Analyze this hotel image and create a descriptive caption for guest photo sharing.

Hotel: {analysis['hotel_name']}
Category: {analysis['category']}
Features: {analysis['features']}

Create a compelling, descriptive caption that:
1. Clearly describes what guests will see
2. Highlights appealing features
3. Uses words guests would search for
4. Keeps it under 100 characters
5. Sounds professional and inviting

Focus on guest benefits and visual appeal."""

            llm_vision = ChatOpenAI(
                openai_api_key=OPENAI_API_KEY, 
                model="gpt-4o-mini", 
                temperature=0.3
            )
            
            response = llm_vision.invoke([{
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}",
                            "detail": "high"
                        }
                    }
                ]
            }])
            
            caption = response.content.strip()
            print(f"🤖 AI Generated Caption: {caption}")
            return caption[:100]  # Limit length
            
        except Exception as e:
            print(f"⚠️ AI caption generation failed: {e}")
            return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
    
    async def _upload_to_s3(self, file_path: str, analysis: Dict, caption: str) -> Dict[str, Any]:
        """Upload file to AWS S3"""
        
        try:
            # Generate S3 key with descriptive path
            hotel_key = analysis['hotel_id'].replace(' ', '_').lower()
            timestamp = int(time.time())
            filename = f"{analysis['category']}_{analysis['features'].replace(' ', '_')}_{timestamp}.jpg"
            s3_key = f"hotels/{hotel_key}/{filename}"
            
            print(f"📤 Uploading to S3: {s3_key}")
            
            # Determine content type
            content_type = 'image/jpeg'
            if file_path.lower().endswith('.png'):
                content_type = 'image/png'
            elif file_path.lower().endswith('.mp4'):
                content_type = 'video/mp4'
            
            # Upload to S3
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read',  # Make publicly accessible
                    'Metadata': {
                        'hotel': analysis['hotel_name'],
                        'category': analysis['category'],
                        'features': analysis['features'],
                        'caption': caption,
                        'uploaded_via': 'whatsapp'
                    }
                }
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            
            print(f"✅ Successfully uploaded to: {s3_url}")
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key
            }
            
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_database_with_photo_url(
        self, 
        analysis: Dict, 
        s3_url: str, 
        caption: str
    ) -> Dict[str, Any]:
        """Update database with photo URL in JSON format"""
        
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                
                # Photo entry to add
                photo_entry = {
                    "url": s3_url,
                    "description": caption
                }
                
                if analysis["category"] == "room":
                    # Update room_types table
                    cursor.execute("""
                        SELECT property_id, photo_urls 
                        FROM room_types rt
                        JOIN hotels h ON rt.property_id = h.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?)
                        LIMIT 1
                    """, [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        property_id, existing_photos = result
                        
                        # Parse existing photos or create new structure
                        if existing_photos:
                            try:
                                photos_data = json.loads(existing_photos)
                            except:
                                photos_data = {"room_photos": []}
                        else:
                            photos_data = {"room_photos": []}
                        
                        # Add new photo
                        if "room_photos" not in photos_data:
                            photos_data["room_photos"] = []
                        photos_data["room_photos"].append(photo_entry)
                        
                        # Update room_types table
                        cursor.execute("""
                            UPDATE room_types 
                            SET photo_urls = ? 
                            WHERE property_id = ?
                        """, [json.dumps(photos_data), property_id])
                        
                        print(f"✅ Updated room photos for {analysis['hotel_name']}")
                
                else:
                    # Update hotels table for hotel/facility photos
                    cursor.execute("""
                        SELECT photo_urls 
                        FROM hotels 
                        WHERE LOWER(hotel_name) LIKE LOWER(?)
                    """, [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        existing_photos = result[0]
                        
                        # Parse existing photos or create new structure
                        if existing_photos:
                            try:
                                photos_data = json.loads(existing_photos)
                            except:
                                photos_data = {"hotel_photos": [], "facility_photos": []}
                        else:
                            photos_data = {"hotel_photos": [], "facility_photos": []}
                        
                        # Add to appropriate category
                        if analysis["category"] == "facility":
                            if "facility_photos" not in photos_data:
                                photos_data["facility_photos"] = []
                            photos_data["facility_photos"].append(photo_entry)
                        else:
                            if "hotel_photos" not in photos_data:
                                photos_data["hotel_photos"] = []
                            photos_data["hotel_photos"].append(photo_entry)
                        
                        # Update hotels table
                        cursor.execute("""
                            UPDATE hotels 
                            SET photo_urls = ? 
                            WHERE LOWER(hotel_name) LIKE LOWER(?)
                        """, [json.dumps(photos_data), f"%{analysis['hotel_name']}%"])
                        
                        print(f"✅ Updated {analysis['category']} photos for {analysis['hotel_name']}")
                
                conn.commit()
                return {"success": True}
                
        except Exception as e:
            print(f"❌ Database update failed: {e}")
            return {"success": False, "error": str(e)}

# Tool for other agents to use
@tool
async def process_whatsapp_media_upload_cloud(
    media_url: str,
    media_type: str,
    caption: str = "",
    sender_info: str = "",
    chat_context: str = ""
) -> str:
    """
    Process WhatsApp media from hotel staff and upload to AWS S3 with database integration.
    
    Args:
        media_url: URL to download the media file
        media_type: Type of media (image, video, document)
        caption: Caption/message with the media
        sender_info: Information about who sent it
        chat_context: Recent chat context for better categorization
        
    Returns:
        Status message with upload results
    """
    
    agent = CloudWhatsAppMediaAgent()
    result = await agent.process_whatsapp_media(
        media_url, media_type, caption, sender_info, chat_context
    )
    
    if result["success"]:
        return result["message"]
    else:
        return f"❌ Failed to process WhatsApp media: {result['error']}"

if __name__ == "__main__":
    # Test the cloud agent
    async def test_cloud_agent():
        print("🧪 Testing WhatsApp Cloud Media Agent")
        print("🌩️  Uploads to AWS S3 and updates database with photo URLs")
        
        # Simulate WhatsApp media sharing
        test_result = await process_whatsapp_media_upload_cloud(
            media_url="https://images.unsplash.com/photo-1566073771259-6a8506099945",
            media_type="image",
            caption="Grand Hyatt KL - Deluxe King Room with amazing city view! Perfect for business travelers.",
            sender_info="Hotel Manager",
            chat_context="Uploading room photos for guest bookings. This is the deluxe king room with city view."
        )
        
        print(test_result)
    
    # Run test
    asyncio.run(test_cloud_agent()) 
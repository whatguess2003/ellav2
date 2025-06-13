#!/usr/bin/env python3
"""
WhatsApp Media Agent for Ella - Flat Directory Structure
Automatically processes and uploads media files shared on WhatsApp
Uses semantic filenames and flat storage optimized for AI search
"""

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from config.settings import ***REMOVED***
from .hotel_tools.media_manager import hotel_media_manager
from typing import Dict, Optional, Any
import requests
import asyncio
import json
import os
from pathlib import Path
import tempfile
import re
import time

# Initialize AI for content analysis
llm = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o", temperature=0.3)

class WhatsAppMediaAgent:
    """Agent that processes WhatsApp media and uploads to flat storage with semantic filenames"""
    
    def __init__(self):
        self.supported_media_types = {
            'image': ['.jpg', '.jpeg', '.png', '.webp'],
            'video': ['.mp4', '.avi', '.mov'],
            'document': ['.pdf', '.doc', '.docx']
        }
        
        # Flat directory structure paths
        self.media_storage_root = Path("media_storage")
        self.thumbnails_dir = self.media_storage_root / "thumbnails"
        self.temp_cache_dir = self.media_storage_root / "temp-cache"
        self.uploads_dir = self.media_storage_root / "uploads"
        
        # Ensure directories exist
        self.media_storage_root.mkdir(exist_ok=True)
        self.thumbnails_dir.mkdir(exist_ok=True)
        self.temp_cache_dir.mkdir(exist_ok=True)
        self.uploads_dir.mkdir(exist_ok=True)
    
    async def process_whatsapp_media(
        self,
        media_url: str,
        media_type: str,
        caption: str = "",
        sender_info: str = "",
        chat_context: str = ""
    ) -> Dict[str, Any]:
        """
        Process media file shared on WhatsApp using flat directory structure
        
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
            print(f"📱 WHATSAPP MEDIA: Processing {media_type} from {sender_info}")
            
            # Download the media file to uploads staging area
            temp_file = await self._download_media(media_url, media_type)
            if not temp_file:
                return {"success": False, "error": "Failed to download media"}
            
            # Analyze the content and context
            analysis = await self._analyze_media_content(
                caption, sender_info, chat_context, media_type
            )
            
            if not analysis.get("hotel_id"):
                return {"success": False, "error": "Could not determine hotel context"}
            
            # Upload using production media manager with flat structure
            upload_result = await hotel_media_manager.upload_media(
                file_path=temp_file,
                original_filename=f"whatsapp_{analysis['timestamp']}.{analysis['file_ext']}",
                hotel_id=analysis["hotel_id"],
                category=analysis["category"],
                subcategory=analysis.get("subcategory", ""),
                room_type_id=analysis.get("room_type_id", ""),
                guest_id=analysis.get("guest_id", "whatsapp_user"),
                uploader_type="whatsapp",
                is_public=True,
                human_caption=analysis.get("description", "")
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            if upload_result["success"]:
                print(f"✅ Media uploaded as: {upload_result['semantic_filename']}")
                print(f"📁 Stored in: media_storage/{upload_result['semantic_filename']}")
                
                return {
                    "success": True,
                    "semantic_filename": upload_result["semantic_filename"],
                    "url": upload_result["url"],
                    "thumbnail_url": upload_result.get("thumbnail_url"),
                    "ai_caption": upload_result.get("caption"),
                    "semantic_tags": upload_result.get("semantic_tags", []),
                    "storage_location": f"media_storage/{upload_result['semantic_filename']}",
                    "analysis": analysis,
                    "message": f"""✅ Photo uploaded to flat storage structure!
📁 File: {upload_result['semantic_filename']}
📂 Location: media_storage/{upload_result['semantic_filename']}
🔍 Searchable by: {', '.join(upload_result.get('semantic_tags', [])[:5])}
🤖 AI Caption: {upload_result.get('caption', 'Generated automatically')}
✨ Ready for guest semantic search!"""
                }
            else:
                return {"success": False, "error": upload_result["error"]}
                
        except Exception as e:
            print(f"❌ WhatsApp media processing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _download_media(self, media_url: str, media_type: str) -> Optional[str]:
        """Download media file to uploads staging area"""
        try:
            response = requests.get(media_url, stream=True)
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
            
            # Save to uploads staging area
            temp_file = self.uploads_dir / f"whatsapp_{int(time.time())}_{hash(media_url)}{file_ext}"
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"📥 Downloaded to staging: {temp_file}")
            return str(temp_file)
            
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
        """Use AI to analyze and categorize the media content for semantic filename generation"""
        
        # Build analysis prompt for flat structure semantic naming
        analysis_prompt = f"""
        Analyze this WhatsApp media context and generate metadata for FLAT DIRECTORY semantic filename:

        MEDIA TYPE: {media_type}
        CAPTION: {caption}
        SENDER: {sender_info}
        CHAT CONTEXT: {chat_context}

        Create semantic filename components following this pattern:
        {{hotel}}_{{star}}_{{category}}_{{type}}_{{features}}_{{keywords}}_{{number}}.{{ext}}

        Extract:
        1. hotel_id: grand_hyatt_kuala_lumpur, sam_hotel_kl, marina_court_resort_kk
        2. star_rating: 5, 4, 3 (hotel star rating)
        3. category: room, pool, restaurant, spa, gym, lobby, exterior
        4. type: interior, exterior, view, amenity
        5. features: king, twin, infinity, fine_dining, marble, etc.
        6. keywords: luxury, spacious, modern, view, deck, elegant (guest-friendly terms)
        7. description: Full description for AI caption
        8. file_ext: jpg, png, mp4

        HOTEL MAPPING:
        - Grand Hyatt, Hyatt KL → grand_hyatt_kuala_lumpur (5 star)
        - Sam Hotel → sam_hotel_kl (3 star)  
        - Marina Court, Kota Kinabalu → marina_court_resort_kk (4 star)

        GUEST-FRIENDLY KEYWORDS (Important for search):
        - Use "view" not "panoramic" (guests search "room view")
        - Use "bathroom" not "bathtub" (guests search "bathroom")
        - Use "pool" not "swimming" (guests search "pool")
        - Use "restaurant" not "dining" (guests search "restaurant")
        - Use "lobby" not "reception" (guests search "lobby")

        Return as JSON only:
        {{
            "hotel_id": "grand_hyatt_kuala_lumpur",
            "star_rating": 5,
            "category": "room",
            "type": "interior", 
            "features": "king",
            "keywords": "luxury_spacious_view",
            "description": "Detailed description for AI caption",
            "file_ext": "jpg",
            "timestamp": {int(time.time())}
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
            
            # Add timestamp if not provided
            if "timestamp" not in analysis:
                analysis["timestamp"] = int(time.time())
            
            # Default file extension
            if "file_ext" not in analysis:
                analysis["file_ext"] = "jpg" if media_type == "image" else "mp4"
            
            print(f"🧠 AI Analysis for Flat Structure: {analysis}")
            return analysis
            
        except Exception as e:
            print(f"⚠️ Analysis failed, using defaults: {e}")
            
            # Fallback analysis
            return {
                "hotel_id": "grand_hyatt_kuala_lumpur",  # Default
                "star_rating": 5,
                "category": "room",
                "type": "interior",
                "features": "king",
                "keywords": "luxury_spacious",
                "description": f"WhatsApp shared {media_type}: {caption[:100]}",
                "file_ext": "jpg" if media_type == "image" else "mp4",
                "timestamp": int(time.time())
            }

# Tool for other agents to use
@tool
async def process_whatsapp_media_upload(
    media_url: str,
    media_type: str,
    caption: str = "",
    sender_info: str = "",
    chat_context: str = ""
) -> str:
    """
    Process and upload media shared on WhatsApp using flat directory structure with semantic naming.
    
    Args:
        media_url: URL to download the media file
        media_type: Type of media (image, video, document)
        caption: Caption/message with the media
        sender_info: Information about who sent it
        chat_context: Recent chat context for better categorization
        
    Returns:
        Status message with upload results
    """
    
    agent = WhatsAppMediaAgent()
    result = await agent.process_whatsapp_media(
        media_url, media_type, caption, sender_info, chat_context
    )
    
    if result["success"]:
        return f"""✅ WhatsApp media processed successfully!

📁 **FLAT STORAGE STRUCTURE**
File: {result['semantic_filename']}
Location: media_storage/{result['semantic_filename']}
Thumbnail: thumbnails/thumb_{result['semantic_filename']}

🔍 **SEMANTIC SEARCH READY**
AI Caption: {result.get('ai_caption', 'Generated automatically')}
Search Tags: {', '.join(result.get('semantic_tags', [])[:5])}
Hotel: {result['analysis']['hotel_id']}
Category: {result['analysis']['category']}

✨ **GUEST QUERIES THAT WILL FIND THIS:**
- "{result['analysis']['category']} {result['analysis']['features']}"
- "{result['analysis']['keywords'].replace('_', ' ')}"
- Natural language: "show me {result['analysis']['category']} photos"

🌐 The photo is now searchable by AI semantic search - guests can use natural language to find it instantly!"""
    else:
        return f"❌ Failed to process WhatsApp media: {result['error']}"

# Webhook handler for WhatsApp Business API
async def handle_whatsapp_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle WhatsApp Business API webhook for media messages
    
    Args:
        webhook_data: Webhook payload from WhatsApp
        
    Returns:
        Processing result
    """
    
    try:
        # Extract media info from webhook
        if "entry" not in webhook_data:
            return {"success": False, "error": "Invalid webhook data"}
        
        entry = webhook_data["entry"][0]
        changes = entry.get("changes", [])
        
        for change in changes:
            if change.get("field") == "messages":
                messages = change.get("value", {}).get("messages", [])
                
                for message in messages:
                    # Check if it's a media message
                    if message.get("type") in ["image", "video", "document"]:
                        media_type = message["type"]
                        media_id = message[media_type]["id"]
                        caption = message[media_type].get("caption", "")
                        
                        # Get sender info
                        sender_phone = message.get("from", "")
                        
                        # You would implement media URL retrieval here
                        # This requires WhatsApp Business API media endpoint
                        media_url = f"https://graph.facebook.com/v18.0/{media_id}"
                        
                        # Process the media using flat structure
                        agent = WhatsAppMediaAgent()
                        result = await agent.process_whatsapp_media(
                            media_url=media_url,
                            media_type=media_type,
                            caption=caption,
                            sender_info=sender_phone,
                            chat_context=""  # You could store chat history
                        )
                        
                        return result
        
        return {"success": False, "error": "No media messages found"}
        
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test the agent
    async def test_agent():
        print("🧪 Testing WhatsApp Media Agent - Flat Structure")
        print("📁 All files will be stored in media_storage/ root directory")
        print("🏷️ Semantic filenames: grand_hyatt_5_room_interior_king_view_luxury_001.jpg")
        
        # Simulate WhatsApp media sharing
        test_result = await process_whatsapp_media_upload(
            media_url="https://example.com/test_bathroom.jpg",
            media_type="image",
            caption="Luxury bathroom photo for Grand Hyatt KL - Deluxe King Room with city view",
            sender_info="Hotel Manager",
            chat_context="We need photos for the booking system. This is the bathroom from the king room."
        )
        
        print(test_result)
    
    asyncio.run(test_agent()) 
#!/usr/bin/env python3
"""
Cloud-Based Media Sharing System for WhatsApp Integration
Queries database for AWS S3 photo URLs, downloads temporarily, shares via Twilio WhatsApp
"""

import os
import json
import sqlite3
import requests
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.tools import tool
import uuid

# Database connection
def get_db_connection(db_path: str = "ella.db"):
    """Get database connection using context manager"""
    return sqlite3.connect(db_path)

class CloudMediaSharer:
    """Cloud-based media sharing for WhatsApp delivery via Twilio"""
    
    def __init__(self):
        self.aws_bucket = "ella-hotel-media"
        self.temp_files = []  # Track for cleanup
        
    def query_photo_urls_from_db(self, hotel_name: str, category: str, search_query: str = "") -> List[Dict]:
        """Query database for photo URLs based on search criteria"""
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if category == "room":
                    # Query room_types table for room photos
                    query = """
                        SELECT rt.photo_urls 
                        FROM room_types rt
                        JOIN hotels h ON rt.property_id = h.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?)
                        AND rt.photo_urls IS NOT NULL
                        AND rt.is_active = 1
                    """
                else:
                    # Query hotels table for hotel/facility photos
                    query = """
                        SELECT photo_urls 
                        FROM hotels 
                        WHERE LOWER(hotel_name) LIKE LOWER(?)
                        AND photo_urls IS NOT NULL
                        AND is_active = 1
                    """
                
                cursor.execute(query, [f"%{hotel_name}%"])
                results = cursor.fetchall()
                
                all_photos = []
                for row in results:
                    if row[0]:  # photo_urls not null
                        try:
                            photo_data = json.loads(row[0])
                            
                            # Extract relevant category
                            if category == "hotel" and "hotel_photos" in photo_data:
                                all_photos.extend(photo_data["hotel_photos"])
                            elif category == "room" and "room_photos" in photo_data:
                                all_photos.extend(photo_data["room_photos"])
                            elif category == "facility" and "facility_photos" in photo_data:
                                all_photos.extend(photo_data["facility_photos"])
                        except json.JSONDecodeError:
                            print(f"⚠️ Invalid JSON in photo_urls for {hotel_name}")
                            continue
                
                # Filter by search query if provided
                if search_query:
                    filtered_photos = []
                    search_lower = search_query.lower()
                    for photo in all_photos:
                        if search_lower in photo.get("description", "").lower():
                            filtered_photos.append(photo)
                    return filtered_photos
                
                return all_photos
                
        except Exception as e:
            print(f"❌ Database query error: {e}")
            return []
    
    def download_photos_from_s3(self, photo_urls: List[Dict]) -> List[Dict]:
        """Download photos from AWS S3 URLs to temporary files"""
        
        downloaded_files = []
        
        for photo_item in photo_urls:
            try:
                print(f"📥 Downloading: {photo_item['url']}")
                
                # Download from S3 URL
                response = requests.get(photo_item["url"], timeout=30)
                response.raise_for_status()
                
                # Create temporary file with descriptive name
                temp_dir = tempfile.mkdtemp()
                # Extract descriptive filename from URL or use description
                url_filename = photo_item["url"].split("/")[-1]
                if url_filename.endswith(('.jpg', '.jpeg', '.png')):
                    filename = url_filename
                else:
                    # Generate descriptive filename
                    desc_parts = photo_item["description"].lower().replace(" ", "_")[:50]
                    filename = f"{desc_parts}.jpg"
                
                temp_file_path = os.path.join(temp_dir, filename)
                
                # Save to temporary file
                with open(temp_file_path, 'wb') as f:
                    f.write(response.content)
                
                # Track for cleanup
                self.temp_files.append(temp_file_path)
                
                downloaded_files.append({
                    "local_path": temp_file_path,
                    "description": photo_item["description"],
                    "original_url": photo_item["url"],
                    "filename": filename
                })
                
                print(f"✅ Downloaded: {filename}")
                
            except Exception as e:
                print(f"❌ Failed to download {photo_item.get('url', 'unknown')}: {e}")
                continue
        
        return downloaded_files
    
    def cleanup_downloaded_media(self) -> None:
        """Clean up temporarily downloaded files immediately after sharing"""
        
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Cleaned up: {file_path}")
                    
                    # Also remove temp directory if empty
                    temp_dir = os.path.dirname(file_path)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                        print(f"🗑️ Removed temp dir: {temp_dir}")
            except Exception as e:
                print(f"⚠️ Cleanup failed for {file_path}: {e}")
        
        # Clear tracking list
        self.temp_files.clear()

# Global instance
cloud_media_sharer = CloudMediaSharer()

@tool
def get_hotel_photos_from_cloud(
    hotel_name: str,
    category: str = "hotel",  # "hotel", "room", "facility"
    search_query: str = "",
    max_photos: int = 3
) -> str:
    """
    Query database for hotel photo URLs, download from AWS S3, prepare for WhatsApp sharing.
    
    Args:
        hotel_name: Name of the hotel
        category: Photo category - "hotel", "room", or "facility"
        search_query: Optional search terms to filter photos
        max_photos: Maximum number of photos to retrieve
        
    Returns:
        JSON string with media ready for WhatsApp sharing
    """
    
    try:
        print(f"🔍 CLOUD MEDIA SEARCH: {category} photos for {hotel_name}")
        if search_query:
            print(f"🎯 Search Query: {search_query}")
        
        # 1. QUERY DATABASE for photo URLs
        photo_urls = cloud_media_sharer.query_photo_urls_from_db(hotel_name, category, search_query)
        
        if not photo_urls:
            return json.dumps({
                "media_ready": False, 
                "message": f"No {category} photos found for {hotel_name}",
                "search_query": search_query
            })
        
        print(f"📋 Found {len(photo_urls)} photos in database")
        
        # 2. DOWNLOAD from AWS S3 (temporary files)
        downloaded_files = cloud_media_sharer.download_photos_from_s3(photo_urls[:max_photos])
        
        if not downloaded_files:
            return json.dumps({
                "media_ready": False,
                "message": f"Failed to download {category} photos from cloud storage"
            })
        
        print(f"📥 Downloaded {len(downloaded_files)} photos successfully")
        
        # 3. PREPARE for WhatsApp sharing
        whatsapp_media = {
            "media_ready": True,
            "local_files": [file_info["local_path"] for file_info in downloaded_files],
            "descriptions": [file_info["description"] for file_info in downloaded_files],
            "filenames": [file_info["filename"] for file_info in downloaded_files],
            "message_text": f"Here are {category} photos from {hotel_name}:",
            "cleanup_required": True,  # Flag for immediate cleanup
            "photo_count": len(downloaded_files),
            "category": category
        }
        
        return json.dumps(whatsapp_media)
        
    except Exception as e:
        print(f"❌ Cloud media error: {e}")
        return json.dumps({
            "media_ready": False, 
            "error": str(e),
            "message": "Failed to retrieve photos from cloud storage"
        })

@tool
def get_room_photos_from_cloud(
    hotel_name: str,
    room_type: str,
    max_photos: int = 3
) -> str:
    """
    Get specific room photos from cloud storage with enhanced room type matching.
    
    Args:
        hotel_name: Name of the hotel
        room_type: Type of room (e.g., "king room", "deluxe suite")
        max_photos: Maximum number of photos to retrieve
        
    Returns:
        JSON string with room photos ready for WhatsApp sharing
    """
    
    try:
        # Enhanced room type matching using database room names
        enhanced_query = enhance_room_search_query(room_type, hotel_name)
        
        print(f"🏠 ROOM PHOTO SEARCH: {room_type} → {enhanced_query}")
        
        return get_hotel_photos_from_cloud(hotel_name, "room", enhanced_query, max_photos)
        
    except Exception as e:
        print(f"❌ Room photo error: {e}")
        return json.dumps({
            "media_ready": False,
            "error": str(e),
            "message": f"Failed to retrieve {room_type} photos"
        })

def enhance_room_search_query(room_type: str, hotel_name: str) -> str:
    """Enhance room search query using actual room types from database"""
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT rt.room_name 
                FROM room_types rt
                JOIN hotels h ON rt.property_id = h.property_id
                WHERE LOWER(h.hotel_name) LIKE LOWER(?)
                AND rt.is_active = 1
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            room_types = [row[0] for row in cursor.fetchall()]
            
            if not room_types:
                return room_type
            
            # Find best match using keyword matching
            room_lower = room_type.lower()
            best_match = None
            best_score = 0
            
            for db_room_type in room_types:
                db_lower = db_room_type.lower()
                
                # Count matching words
                room_words = set(room_lower.split())
                db_words = set(db_lower.split())
                matching_words = room_words.intersection(db_words)
                
                if matching_words:
                    score = len(matching_words) / len(room_words)
                    if score > best_score:
                        best_score = score
                        best_match = db_room_type
            
            if best_match and best_score >= 0.3:
                print(f"🎯 ROOM TYPE ENHANCEMENT: '{room_type}' → '{best_match}' (score: {best_score:.1%})")
                return best_match
            
            return room_type
            
    except Exception as e:
        print(f"❌ Room enhancement error: {e}")
        return room_type

@tool
def get_facility_photos_from_cloud(
    hotel_name: str,
    facility_type: str = "",
    max_photos: int = 3
) -> str:
    """
    Get hotel facility photos from cloud storage.
    
    Args:
        hotel_name: Name of the hotel
        facility_type: Type of facility (e.g., "pool", "gym", "spa", "restaurant")
        max_photos: Maximum number of photos to retrieve
        
    Returns:
        JSON string with facility photos ready for WhatsApp sharing
    """
    
    search_query = f"{facility_type} facility" if facility_type else ""
    return get_hotel_photos_from_cloud(hotel_name, "facility", search_query, max_photos)

@tool
def cleanup_shared_media() -> str:
    """Clean up temporarily downloaded media files after WhatsApp sharing"""
    
    try:
        cloud_media_sharer.cleanup_downloaded_media()
        return json.dumps({
            "cleanup_success": True,
            "message": "Temporary media files cleaned up successfully"
        })
    except Exception as e:
        return json.dumps({
            "cleanup_success": False,
            "error": str(e),
            "message": "Failed to clean up temporary files"
        })

# Legacy support tools (updated to use cloud)
@tool
def search_hotel_media(
    hotel_name: str,
    search_query: str = "",
    max_results: int = 8
) -> str:
    """Legacy support: Search hotel media using cloud storage"""
    return get_hotel_photos_from_cloud(hotel_name, "hotel", search_query, max_results)

@tool
def get_hotel_photos(
    hotel_name: str,
    category: str = "",
    max_photos: int = 5
) -> str:
    """Legacy support: Get hotel photos from cloud"""
    return get_hotel_photos_from_cloud(hotel_name, "hotel", category, max_photos)

@tool
def get_room_photos(
    hotel_name: str,
    room_type: str,
    max_photos: int = 3
) -> str:
    """Legacy support: Get room photos from cloud"""
    return get_room_photos_from_cloud(hotel_name, room_type, max_photos)

# Migration and utility functions
def migrate_local_to_aws_s3():
    """One-time migration: Upload local files to S3 with descriptive names"""
    
    try:
        import boto3
        
        s3_client = boto3.client('s3')
        bucket_name = "ella-hotel-media"
        
        print("🚀 Starting migration from local to AWS S3...")
        
        # Scan existing local media (if any)
        local_media_path = Path("media_storage")
        if not local_media_path.exists():
            print("⚠️ No local media_storage directory found")
            return
        
        hotel_photo_mapping = {}
        
        # Scan local files
        for file_path in local_media_path.glob("*.jpg"):
            try:
                # Extract hotel name and description from filename
                filename = file_path.name
                hotel_name = extract_hotel_name_from_filename(filename)
                description = filename.replace('_', ' ').replace('.jpg', '')
                
                # Generate S3 key with descriptive name
                s3_key = f"hotels/{hotel_name.replace(' ', '_').lower()}/{filename}"
                
                # Upload to S3
                s3_client.upload_file(
                    str(file_path),
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                
                # Generate S3 URL
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
                
                # Group by hotel for database update
                if hotel_name not in hotel_photo_mapping:
                    hotel_photo_mapping[hotel_name] = {
                        "hotel_photos": [], 
                        "room_photos": [], 
                        "facility_photos": []
                    }
                
                # Categorize photo based on filename
                if any(word in filename.lower() for word in ['room', 'suite', 'bedroom']):
                    hotel_photo_mapping[hotel_name]["room_photos"].append({
                        "url": s3_url,
                        "description": description
                    })
                elif any(word in filename.lower() for word in ['pool', 'gym', 'spa', 'restaurant', 'lobby']):
                    hotel_photo_mapping[hotel_name]["facility_photos"].append({
                        "url": s3_url,
                        "description": description
                    })
                else:
                    hotel_photo_mapping[hotel_name]["hotel_photos"].append({
                        "url": s3_url,
                        "description": description
                    })
                
                print(f"✅ Uploaded: {filename} → {s3_url}")
                
            except Exception as e:
                print(f"❌ Failed to upload {file_path}: {e}")
                continue
        
        # Update database with photo URLs
        for hotel, photos in hotel_photo_mapping.items():
            update_hotel_photos_in_db(hotel, photos)
            print(f"📋 Updated database for {hotel}")
        
        print(f"🎉 Migration completed! {len(hotel_photo_mapping)} hotels updated")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

def extract_hotel_name_from_filename(filename: str) -> str:
    """Extract hotel name from descriptive filename"""
    
    filename_lower = filename.lower()
    
    # Hotel name patterns
    if 'grand_hyatt' in filename_lower or 'grand hyatt' in filename_lower:
        return 'Grand Hyatt Kuala Lumpur'
    elif 'marina_court' in filename_lower or 'marina court' in filename_lower:
        return 'Marina Court Resort Kota Kinabalu'
    elif 'sam_hotel' in filename_lower or 'sam hotel' in filename_lower:
        return 'Sam Hotel Kuala Lumpur'
    elif 'mandarin_oriental' in filename_lower or 'mandarin oriental' in filename_lower:
        return 'Mandarin Oriental Kuala Lumpur'
    else:
        # Extract first two words as hotel name
        parts = filename.replace('_', ' ').split()
        if len(parts) >= 2:
            return ' '.join(parts[:2]).title()
        return 'Unknown Hotel'

def update_hotel_photos_in_db(hotel_name: str, photos: Dict) -> None:
    """Update hotel database with photo URLs"""
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update hotels table with photo URLs
            cursor.execute(
                "UPDATE hotels SET photo_urls = ? WHERE LOWER(hotel_name) LIKE LOWER(?)",
                [json.dumps(photos), f"%{hotel_name}%"]
            )
            
            conn.commit()
            print(f"✅ Database updated for {hotel_name}")
            
    except Exception as e:
        print(f"❌ Database update failed for {hotel_name}: {e}")

# Export tools for chat assistant
CLOUD_MEDIA_TOOLS = [
    get_hotel_photos_from_cloud,
    get_room_photos_from_cloud,
    get_facility_photos_from_cloud,
    cleanup_shared_media,
    # Legacy support
    search_hotel_media,
    get_hotel_photos,
    get_room_photos
]

if __name__ == "__main__":
    print("🌩️ Cloud Media Sharer - Testing...")
    
    # Test cloud media retrieval
    result = get_hotel_photos_from_cloud("Grand Hyatt", "hotel", "", 2)
    print("Test Result:", result)
    
    # Test cleanup
    cleanup_result = cleanup_shared_media()
    print("Cleanup Result:", cleanup_result) 
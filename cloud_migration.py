#!/usr/bin/env python3
"""
Cloud Media Migration Script
Uploads local media files to AWS S3 and updates database
"""

import os
import json
import sqlite3
import boto3
from pathlib import Path
from typing import Dict, List

# AWS Configuration
AWS_BUCKET_NAME = "ella-hotel-media"
AWS_REGION = "ap-southeast-1"

def create_database_schema(db_path: str = "ella.db"):
    """Add photo_urls columns to database tables"""
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("📋 Creating database schema changes...")
            
            # Add photo_urls column to hotels table
            try:
                cursor.execute("ALTER TABLE hotels ADD COLUMN photo_urls TEXT")
                print("✅ Added photo_urls column to hotels table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("⚠️  photo_urls column already exists in hotels table")
                else:
                    raise
            
            # Add photo_urls column to room_types table
            try:
                cursor.execute("ALTER TABLE room_types ADD COLUMN photo_urls TEXT")
                print("✅ Added photo_urls column to room_types table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("⚠️  photo_urls column already exists in room_types table")
                else:
                    raise
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hotels_photo_urls 
                ON hotels(photo_urls) WHERE photo_urls IS NOT NULL
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_room_types_photo_urls 
                ON room_types(photo_urls) WHERE photo_urls IS NOT NULL
            """)
            
            conn.commit()
            print("✅ Database schema updated successfully")
            return True
            
    except Exception as e:
        print(f"❌ Database schema creation failed: {e}")
        return False

def scan_local_media_files(media_dir: str = "media_storage") -> List[Dict]:
    """Scan local media files and extract metadata"""
    
    media_path = Path(media_dir)
    if not media_path.exists():
        print(f"⚠️  Media directory '{media_dir}' not found")
        return []
    
    media_files = []
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    print(f"🔍 Scanning local media in: {media_path}")
    
    for file_path in media_path.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            
            # Skip thumbnails directory
            if 'thumbnail' in str(file_path).lower():
                continue
            
            # Extract metadata from filename
            filename = file_path.name
            hotel_name = extract_hotel_name_from_filename(filename)
            description = extract_description_from_filename(filename)
            category = categorize_photo(filename)
            
            media_files.append({
                "local_path": str(file_path),
                "filename": filename,
                "hotel_name": hotel_name,
                "description": description,
                "category": category,
                "file_size": file_path.stat().st_size
            })
    
    print(f"📋 Found {len(media_files)} media files to migrate")
    return media_files

def extract_hotel_name_from_filename(filename: str) -> str:
    """Extract hotel name from filename"""
    filename_lower = filename.lower()
    
    if 'grand_hyatt' in filename_lower or 'grand hyatt' in filename_lower:
        return 'Grand Hyatt Kuala Lumpur'
    elif 'marina_court' in filename_lower or 'marina court' in filename_lower:
        return 'Marina Court Resort Kota Kinabalu'
    elif 'sam_hotel' in filename_lower or 'sam hotel' in filename_lower:
        return 'Sam Hotel Kuala Lumpur'
    elif 'mandarin_oriental' in filename_lower or 'mandarin oriental' in filename_lower:
        return 'Mandarin Oriental Kuala Lumpur'
    else:
        parts = filename.replace('_', ' ').split()
        if len(parts) >= 2:
            return ' '.join(parts[:2]).title()
        return 'Unknown Hotel'

def extract_description_from_filename(filename: str) -> str:
    """Extract description from filename"""
    # Remove extension and replace underscores with spaces
    description = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
    description = description.replace('_', ' ')
    return description.title()

def categorize_photo(filename: str) -> str:
    """Categorize photo based on filename"""
    filename_lower = filename.lower()
    
    if any(word in filename_lower for word in ['room', 'suite', 'bedroom', 'bed']):
        return 'room'
    elif any(word in filename_lower for word in ['pool', 'gym', 'spa', 'restaurant', 'lobby', 'facility']):
        return 'facility'
    else:
        return 'hotel'

def update_database_with_sample_data():
    """Update database with sample photo URL data for testing"""
    
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Sample data for Grand Hyatt
            grand_hyatt_photos = {
                "hotel_photos": [
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_exterior_luxury_entrance.jpg",
                        "description": "Grand Hyatt luxury entrance with valet service"
                    },
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_lobby_marble_chandelier.jpg",
                        "description": "Marble lobby with crystal chandelier and concierge desk"
                    }
                ],
                "facility_photos": [
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_infinity_pool_rooftop_sunset.jpg",
                        "description": "Rooftop infinity pool with sunset city views and poolside bar"
                    },
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_spa_wellness_treatment_rooms.jpg",
                        "description": "Luxurious spa with private treatment rooms and wellness facilities"
                    }
                ]
            }
            
            # Update hotels table
            cursor.execute("""
                UPDATE hotels 
                SET photo_urls = ? 
                WHERE LOWER(hotel_name) LIKE LOWER(?)
            """, [json.dumps(grand_hyatt_photos), "%grand hyatt%"])
            
            # Sample room photos for Grand Hyatt
            room_photos = {
                "room_photos": [
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_king_room_city_view_luxury_amenities.jpg",
                        "description": "King room with panoramic city view and luxury amenities including marble bathroom"
                    },
                    {
                        "url": "https://ella-hotel-media.s3.amazonaws.com/grand_hyatt_deluxe_suite_living_area_balcony_klcc.jpg",
                        "description": "Deluxe suite living area with private balcony overlooking KLCC twin towers"
                    }
                ]
            }
            
            # Update room_types table
            cursor.execute("""
                UPDATE room_types 
                SET photo_urls = ? 
                WHERE property_id IN (
                    SELECT property_id FROM hotels 
                    WHERE LOWER(hotel_name) LIKE LOWER(?)
                )
            """, [json.dumps(room_photos), "%grand hyatt%"])
            
            conn.commit()
            print("✅ Sample photo data added to database")
            return True
            
    except Exception as e:
        print(f"❌ Sample data update failed: {e}")
        return False

def test_cloud_media_system():
    """Test the cloud media system with sample data"""
    
    try:
        # Import the cloud media sharer
        from chat_assistant.chat_tools.media_sharer import get_hotel_photos_from_cloud, get_room_photos_from_cloud
        
        print("🧪 Testing cloud media system...")
        
        # Test hotel photos
        print("\n1. Testing hotel photos:")
        hotel_result = get_hotel_photos_from_cloud("Grand Hyatt", "hotel", "", 2)
        result_data = json.loads(hotel_result)
        print(f"Result: {result_data.get('media_ready', False)}")
        if result_data.get('media_ready'):
            print(f"Found {len(result_data.get('descriptions', []))} photos")
        
        # Test room photos
        print("\n2. Testing room photos:")
        room_result = get_room_photos_from_cloud("Grand Hyatt", "king room", 2)
        result_data = json.loads(room_result)
        print(f"Result: {result_data.get('media_ready', False)}")
        if result_data.get('media_ready'):
            print(f"Found {len(result_data.get('descriptions', []))} photos")
        
        print("✅ Cloud media system test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def main():
    """Main migration process"""
    
    print("🌩️  CLOUD MEDIA SETUP")
    print("="*40)
    
    # Step 1: Create database schema
    print("\n📋 Step 1: Creating database schema...")
    if not create_database_schema():
        print("❌ Database schema creation failed.")
        return
    
    # Step 2: Scan local media files
    print("\n🔍 Step 2: Scanning local media files...")
    media_files = scan_local_media_files("media_storage")
    
    if media_files:
        # Show preview
        print(f"\n📊 FOUND LOCAL MEDIA:")
        hotels = set(file_info['hotel_name'] for file_info in media_files)
        for hotel in hotels:
            hotel_files = [f for f in media_files if f['hotel_name'] == hotel]
            print(f"  {hotel}: {len(hotel_files)} files")
        
        print(f"\n💡 To upload these files to AWS S3:")
        print("1. Configure AWS credentials")
        print("2. Create S3 bucket: ella-hotel-media")
        print("3. Use boto3 to upload files")
    else:
        print("No local media files found.")
    
    # Step 3: Add sample data for testing
    print("\n📋 Step 3: Adding sample photo data...")
    update_database_with_sample_data()
    
    # Step 4: Test the system
    print("\n🧪 Step 4: Testing cloud media system...")
    test_cloud_media_system()
    
    print("\n🎉 CLOUD MEDIA SETUP COMPLETED!")
    print("="*40)
    print("\nYour cloud media system is ready to use!")

if __name__ == "__main__":
    main() 
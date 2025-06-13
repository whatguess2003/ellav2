#!/usr/bin/env python3
"""
Complete Migration Script: Local Media to AWS S3 Cloud Storage
1. Creates database schema changes
2. Uploads local media files to S3 with descriptive names
3. Updates database with S3 URLs
4. Verifies migration success
"""

import os
import json
import sqlite3
import boto3
from pathlib import Path
from typing import Dict, List
import argparse
from datetime import datetime

# AWS Configuration
AWS_BUCKET_NAME = "ella-hotel-media"
AWS_REGION = "ap-southeast-1"  # Singapore region for Malaysia

class CloudMediaMigration:
    """Complete migration from local files to AWS S3 cloud storage"""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
        self.s3_client = None
        self.bucket_name = AWS_BUCKET_NAME
        self.migration_log = []
        
    def initialize_aws(self):
        """Initialize AWS S3 client"""
        try:
            self.s3_client = boto3.client('s3', region_name=AWS_REGION)
            print(f"✅ AWS S3 client initialized for region: {AWS_REGION}")
            
            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ S3 bucket '{self.bucket_name}' confirmed accessible")
            except:
                print(f"⚠️  S3 bucket '{self.bucket_name}' not accessible")
                print(f"Please create bucket or check AWS credentials")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ AWS initialization failed: {e}")
            print("Please configure AWS credentials:")
            print("- Set AWS_ACCESS_KEY_ID environment variable")
            print("- Set AWS_SECRET_ACCESS_KEY environment variable")
            print("- Or configure AWS CLI: aws configure")
            return False
    
    def create_database_schema(self):
        """Add photo_urls columns to database tables"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
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
    
    def scan_local_media_files(self, media_dir: str = "media_storage") -> List[Dict]:
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
                hotel_name = self.extract_hotel_name_from_filename(filename)
                description = self.extract_description_from_filename(filename)
                category = self.categorize_photo(filename)
                
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
    
    def upload_files_to_s3(self, media_files: List[Dict]) -> Dict[str, List[Dict]]:
        """Upload media files to S3 and organize by hotel"""
        
        hotel_photos = {}
        upload_count = 0
        
        for file_info in media_files:
            try:
                # Generate S3 key with descriptive path
                hotel_key = file_info['hotel_name'].replace(' ', '_').lower()
                s3_key = f"hotels/{hotel_key}/{file_info['filename']}"
                
                print(f"📤 Uploading: {file_info['filename']}")
                
                # Upload to S3 with metadata
                self.s3_client.upload_file(
                    file_info['local_path'],
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': self.get_content_type(file_info['filename']),
                        'Metadata': {
                            'hotel': file_info['hotel_name'],
                            'description': file_info['description'],
                            'category': file_info['category']
                        }
                    }
                )
                
                # Generate S3 URL
                s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
                
                # Organize by hotel and category
                hotel = file_info['hotel_name']
                if hotel not in hotel_photos:
                    hotel_photos[hotel] = {
                        "hotel_photos": [],
                        "room_photos": [],
                        "facility_photos": []
                    }
                
                photo_entry = {
                    "url": s3_url,
                    "description": file_info['description']
                }
                
                # Add to appropriate category
                if file_info['category'] == 'room':
                    hotel_photos[hotel]["room_photos"].append(photo_entry)
                elif file_info['category'] == 'facility':
                    hotel_photos[hotel]["facility_photos"].append(photo_entry)
                else:
                    hotel_photos[hotel]["hotel_photos"].append(photo_entry)
                
                upload_count += 1
                print(f"✅ Uploaded: {file_info['filename']} → {s3_url}")
                
                # Log migration
                self.migration_log.append({
                    "local_file": file_info['local_path'],
                    "s3_url": s3_url,
                    "hotel": hotel,
                    "category": file_info['category'],
                    "status": "success"
                })
                
            except Exception as e:
                print(f"❌ Upload failed for {file_info['filename']}: {e}")
                self.migration_log.append({
                    "local_file": file_info['local_path'],
                    "error": str(e),
                    "status": "failed"
                })
                continue
        
        print(f"🎉 Successfully uploaded {upload_count} files to S3")
        return hotel_photos
    
    def update_database_with_s3_urls(self, hotel_photos: Dict[str, Dict]) -> bool:
        """Update database with S3 photo URLs"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for hotel_name, photos in hotel_photos.items():
                    
                    # Update hotels table with hotel and facility photos
                    hotel_data = {
                        "hotel_photos": photos["hotel_photos"],
                        "facility_photos": photos["facility_photos"]
                    }
                    
                    cursor.execute("""
                        UPDATE hotels 
                        SET photo_urls = ? 
                        WHERE LOWER(hotel_name) LIKE LOWER(?)
                    """, [json.dumps(hotel_data), f"%{hotel_name}%"])
                    
                    # Update room_types table with room photos
                    if photos["room_photos"]:
                        room_data = {"room_photos": photos["room_photos"]}
                        
                        cursor.execute("""
                            UPDATE room_types 
                            SET photo_urls = ? 
                            WHERE property_id IN (
                                SELECT property_id FROM hotels 
                                WHERE LOWER(hotel_name) LIKE LOWER(?)
                            )
                        """, [json.dumps(room_data), f"%{hotel_name}%"])
                    
                    print(f"✅ Database updated for {hotel_name}")
                    print(f"   - Hotel photos: {len(photos['hotel_photos'])}")
                    print(f"   - Room photos: {len(photos['room_photos'])}")
                    print(f"   - Facility photos: {len(photos['facility_photos'])}")
                
                conn.commit()
                print("✅ All database updates completed successfully")
                return True
                
        except Exception as e:
            print(f"❌ Database update failed: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify migration completed successfully"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check hotels with photos
                cursor.execute("""
                    SELECT hotel_name, photo_urls 
                    FROM hotels 
                    WHERE photo_urls IS NOT NULL
                """)
                hotels_with_photos = cursor.fetchall()
                
                # Check room types with photos
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM room_types 
                    WHERE photo_urls IS NOT NULL
                """)
                room_types_with_photos = cursor.fetchone()[0]
                
                print(f"\n📊 MIGRATION VERIFICATION:")
                print(f"✅ Hotels with photos: {len(hotels_with_photos)}")
                print(f"✅ Room types with photos: {room_types_with_photos}")
                
                # Show sample data
                if hotels_with_photos:
                    print(f"\n📋 Sample hotel with photos:")
                    sample_hotel = hotels_with_photos[0]
                    print(f"Hotel: {sample_hotel[0]}")
                    
                    try:
                        sample_photos = json.loads(sample_hotel[1])
                        for category, photos in sample_photos.items():
                            print(f"  - {category}: {len(photos)} photos")
                    except:
                        print("  - Photo data format issue")
                
                return True
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
    
    def save_migration_log(self):
        """Save migration log to file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"migration_log_{timestamp}.json"
        
        log_data = {
            "migration_date": timestamp,
            "total_files": len(self.migration_log),
            "successful_uploads": len([x for x in self.migration_log if x.get("status") == "success"]),
            "failed_uploads": len([x for x in self.migration_log if x.get("status") == "failed"]),
            "files": self.migration_log
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📝 Migration log saved to: {log_file}")
    
    # Helper methods
    def extract_hotel_name_from_filename(self, filename: str) -> str:
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
    
    def extract_description_from_filename(self, filename: str) -> str:
        """Extract description from filename"""
        # Remove extension and replace underscores with spaces
        description = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
        description = description.replace('_', ' ')
        return description.title()
    
    def categorize_photo(self, filename: str) -> str:
        """Categorize photo based on filename"""
        filename_lower = filename.lower()
        
        if any(word in filename_lower for word in ['room', 'suite', 'bedroom', 'bed']):
            return 'room'
        elif any(word in filename_lower for word in ['pool', 'gym', 'spa', 'restaurant', 'lobby', 'facility']):
            return 'facility'
        else:
            return 'hotel'
    
    def get_content_type(self, filename: str) -> str:
        """Get content type for file"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return content_types.get(ext, 'image/jpeg')

def main():
    """Main migration process"""
    
    parser = argparse.ArgumentParser(description='Migrate local media to AWS S3 cloud storage')
    parser.add_argument('--media-dir', default='media_storage', 
                       help='Local media directory (default: media_storage)')
    parser.add_argument('--db-path', default='ella.db', 
                       help='Database path (default: ella.db)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Scan files without uploading')
    
    args = parser.parse_args()
    
    print("🌩️  CLOUD MEDIA MIGRATION STARTING")
    print("="*50)
    
    migration = CloudMediaMigration(args.db_path)
    
    # Step 1: Initialize AWS
    if not args.dry_run:
        print("\n📡 Step 1: Initializing AWS S3...")
        if not migration.initialize_aws():
            print("❌ AWS initialization failed. Aborting migration.")
            return
    
    # Step 2: Create database schema
    print("\n📋 Step 2: Creating database schema...")
    if not migration.create_database_schema():
        print("❌ Database schema creation failed. Aborting migration.")
        return
    
    # Step 3: Scan local media files
    print("\n🔍 Step 3: Scanning local media files...")
    media_files = migration.scan_local_media_files(args.media_dir)
    
    if not media_files:
        print("⚠️  No media files found to migrate.")
        return
    
    # Show preview
    print(f"\n📊 MIGRATION PREVIEW:")
    hotels = set(file_info['hotel_name'] for file_info in media_files)
    for hotel in hotels:
        hotel_files = [f for f in media_files if f['hotel_name'] == hotel]
        print(f"  {hotel}: {len(hotel_files)} files")
    
    if args.dry_run:
        print("\n🔍 DRY RUN COMPLETE - No files uploaded")
        return
    
    # Confirm upload
    confirm = input(f"\nProceed with uploading {len(media_files)} files to S3? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return
    
    # Step 4: Upload to S3
    print("\n📤 Step 4: Uploading files to AWS S3...")
    hotel_photos = migration.upload_files_to_s3(media_files)
    
    # Step 5: Update database
    print("\n📋 Step 5: Updating database with S3 URLs...")
    if not migration.update_database_with_s3_urls(hotel_photos):
        print("❌ Database update failed.")
        return
    
    # Step 6: Verify migration
    print("\n✅ Step 6: Verifying migration...")
    migration.verify_migration()
    
    # Step 7: Save log
    migration.save_migration_log()
    
    print("\n🎉 CLOUD MEDIA MIGRATION COMPLETED SUCCESSFULLY!")
    print("="*50)
    print("\nNext steps:")
    print("1. Test the new cloud media sharing system")
    print("2. Update your chat assistant configuration")
    print("3. Remove local media files after verification")

if __name__ == "__main__":
    main() 
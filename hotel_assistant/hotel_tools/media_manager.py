#!/usr/bin/env python3
"""
Hotel Media Manager - Upload & Storage Operations
AI-Powered Image Captioning, Cloud Storage & Media Processing
"""

from langchain.tools import tool
from typing import Dict, Optional, List, Union, Any, Tuple
import sqlite3
import json
import os
import uuid
import hashlib
from datetime import datetime
import asyncio
import aiofiles
from pathlib import Path
import re
import mimetypes
from PIL import Image, ImageOps
import io
import base64

# Import API keys from config
try:
    from config.settings import ***REMOVED***
    print("[OK] OpenAI API key imported from config/settings.py")
except ImportError:
    ***REMOVED*** = os.getenv('***REMOVED***')
    print("[WARN] Using OpenAI API key from environment variable")

# Optional cloud storage imports
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    print("[CLOUD] boto3 not available - cloud storage disabled")
    BOTO3_AVAILABLE = False
    ClientError = Exception

# AI Captioning imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    print("[AI] OpenAI not available - AI captioning disabled")
    OPENAI_AVAILABLE = False

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    import torch
    BLIP_AVAILABLE = True
except ImportError:
    print("[AI] BLIP not available - fallback captioning only")
    BLIP_AVAILABLE = False

# Configuration
CLOUD_STORAGE_ENABLED = os.getenv('CLOUD_STORAGE_ENABLED', 'True').lower() == 'true' and BOTO3_AVAILABLE
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'ella-media-storage')
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
CLOUDFRONT_DOMAIN = os.getenv('CLOUDFRONT_DOMAIN', '')

# Local storage paths
LOCAL_MEDIA_PATH = Path("media_storage")
LOCAL_THUMBNAILS_PATH = Path("media_storage/thumbnails")
LOCAL_MEDIA_PATH.mkdir(exist_ok=True)
LOCAL_THUMBNAILS_PATH.mkdir(exist_ok=True)

# File type configurations
SUPPORTED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
SUPPORTED_VIDEO_TYPES = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'}
SUPPORTED_DOCUMENT_TYPES = {'.pdf', '.doc', '.docx', '.txt', '.xlsx', '.pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
THUMBNAIL_SIZE = (300, 300)

class AIImageCaptioner:
    """AI-powered image captioning using multiple models."""
    
    def __init__(self):
        self.openai_client = None
        self.blip_model = None
        self.blip_processor = None
        
        # Initialize OpenAI if available
        if OPENAI_AVAILABLE and ***REMOVED***:
            try:
                self.openai_client = openai.OpenAI(api_key=***REMOVED***)
                print("[OK] OpenAI Vision API initialized")
            except Exception as e:
                print(f"[WARN] OpenAI initialization failed: {e}")
        
        # Initialize BLIP if available
        if BLIP_AVAILABLE:
            try:
                self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
                print("[OK] BLIP captioning model initialized")
            except Exception as e:
                print(f"[WARN] BLIP initialization failed: {e}")
    
    async def generate_caption(self, image_path: str, hotel_context: str = "") -> Dict[str, Any]:
        """Generate AI caption for an image with hotel context."""
        
        try:
            # Try OpenAI Vision API first (best quality)
            if self.openai_client:
                caption_data = await self._openai_caption(image_path, hotel_context)
                if caption_data['success']:
                    return caption_data
            
            # Fallback to BLIP
            if self.blip_model and self.blip_processor:
                caption_data = await self._blip_caption(image_path, hotel_context)
                if caption_data['success']:
                    return caption_data
            
            # Ultimate fallback - simple description
            return await self._fallback_caption(image_path, hotel_context)
            
        except Exception as e:
            print(f"[ERROR] Caption generation failed: {e}")
            return {
                'success': False,
                'caption': f"Hotel image - {Path(image_path).stem}",
                'semantic_tags': ['hotel', 'image'],
                'confidence': 0.1,
                'method': 'fallback'
            }
    
    async def _openai_caption(self, image_path: str, hotel_context: str) -> Dict[str, Any]:
        """Generate caption using OpenAI Vision API."""
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create hotel-specific prompt
            prompt = f"""Analyze this hotel image and provide a detailed, professional description for hotel booking guests.

Hotel Context: {hotel_context}

Generate a clear, descriptive caption that includes:
1. The specific type of space (room type, amenity, area)
2. Key features and what makes it appealing
3. Notable design elements or luxury features
4. Overall impression that helps guests visualize the experience

Write the caption as a complete, descriptive phrase that would help potential guests understand exactly what they're looking at and why they'd want to book it.

Keep it under 120 characters but make it vivid and appealing."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
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
                    }
                ],
                max_tokens=300
            )
            
            caption = response.choices[0].message.content.strip()
            
            # Generate semantic tags from caption
            semantic_tags = self._extract_semantic_tags(caption, hotel_context)
            
            return {
                'success': True,
                'caption': caption[:150],  # Limit caption length
                'semantic_tags': semantic_tags,
                'confidence': 0.9,
                'method': 'openai_vision'
            }
            
        except Exception as e:
            print(f"[ERROR] OpenAI captioning failed: {e}")
            return {'success': False}
    
    async def _blip_caption(self, image_path: str, hotel_context: str) -> Dict[str, Any]:
        """Generate caption using BLIP model."""
        
        try:
            # Load and process image
            image = Image.open(image_path).convert('RGB')
            
            # Generate caption with hotel context
            text_prompt = f"a luxurious hotel {hotel_context.lower()}"
            inputs = self.blip_processor(image, text_prompt, return_tensors="pt")
            
            # Generate caption
            with torch.no_grad():
                out = self.blip_model.generate(**inputs, max_length=60, num_beams=5)
                caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            
            # Clean up and enhance caption
            caption = caption.replace(text_prompt, "").strip()
            if not caption or len(caption) < 10:
                # Generate a better fallback caption based on context
                if "room" in hotel_context.lower():
                    caption = f"Elegant hotel room with luxury amenities and modern design"
                elif "bathroom" in hotel_context.lower():
                    caption = f"Luxurious bathroom with premium fixtures and marble finishes"
                elif "pool" in hotel_context.lower():
                    caption = f"Beautiful swimming pool area with stunning views"
                elif "restaurant" in hotel_context.lower():
                    caption = f"Fine dining restaurant with elegant ambiance"
                else:
                    caption = f"Luxury hotel space with premium amenities and modern design"
            
            # Generate semantic tags
            semantic_tags = self._extract_semantic_tags(caption, hotel_context)
            
            return {
                'success': True,
                'caption': caption,
                'semantic_tags': semantic_tags,
                'confidence': 0.7,
                'method': 'blip'
            }
            
        except Exception as e:
            print(f"[ERROR] BLIP captioning failed: {e}")
            return {'success': False}
    
    async def _fallback_caption(self, image_path: str, hotel_context: str) -> Dict[str, Any]:
        """Generate basic caption using filename and context."""
        
        try:
            filename = Path(image_path).stem
            # Clean filename for caption
            cleaned_name = re.sub(r'[_-]', ' ', filename)
            cleaned_name = re.sub(r'\d+', '', cleaned_name).strip()
            
            # Generate contextual caption based on hotel context and filename
            if hotel_context:
                if "room" in hotel_context.lower() or "room" in cleaned_name.lower():
                    if "king" in cleaned_name.lower():
                        caption = f"Spacious king room with luxury amenities and city views"
                    elif "deluxe" in cleaned_name.lower():
                        caption = f"Deluxe hotel room featuring modern design and premium comfort"
                    else:
                        caption = f"Comfortable hotel room with modern amenities and elegant decor"
                elif "bathroom" in hotel_context.lower() or "bathroom" in cleaned_name.lower():
                    caption = f"Luxurious bathroom with marble finishes and premium amenities"
                elif "pool" in hotel_context.lower() or "pool" in cleaned_name.lower():
                    caption = f"Resort-style swimming pool with stunning views and relaxation area"
                elif "restaurant" in hotel_context.lower() or "restaurant" in cleaned_name.lower():
                    caption = f"Elegant dining restaurant with fine cuisine and sophisticated ambiance"
                elif "lobby" in hotel_context.lower() or "lobby" in cleaned_name.lower():
                    caption = f"Grand hotel lobby with luxurious decor and welcoming atmosphere"
                else:
                    caption = f"Premium hotel facility with elegant design and luxury amenities"
            else:
                caption = f"Luxury hotel space featuring modern design and premium amenities"
            
            # Basic semantic tags
            semantic_tags = ['hotel', 'hospitality']
            if 'room' in cleaned_name.lower():
                semantic_tags.extend(['room', 'accommodation'])
            if 'bathroom' in cleaned_name.lower():
                semantic_tags.extend(['bathroom', 'amenities'])
            if 'pool' in cleaned_name.lower():
                semantic_tags.extend(['pool', 'recreation'])
            if 'restaurant' in cleaned_name.lower():
                semantic_tags.extend(['restaurant', 'dining'])
            
            return {
                'success': True,
                'caption': caption,
                'semantic_tags': semantic_tags,
                'confidence': 0.3,
                'method': 'fallback'
            }
            
        except Exception as e:
            print(f"[ERROR] Fallback captioning failed: {e}")
            return {
                'success': False,
                'caption': 'Hotel image',
                'semantic_tags': ['hotel'],
                'confidence': 0.1,
                'method': 'error'
            }
    
    def _extract_semantic_tags(self, caption: str, hotel_context: str) -> List[str]:
        """Extract semantic tags optimized for guest search queries."""
        
        tags = set(['hotel', 'hospitality'])
        
        # Add context tags
        if hotel_context:
            context_words = re.findall(r'\w+', hotel_context.lower())
            tags.update(context_words)
        
        # Extract from caption
        caption_lower = caption.lower()
        
        # Guest-friendly search terms (prioritized)
        guest_search_terms = {
            'view': ['panoramic', 'skyline', 'city_view', 'scenic', 'overlook', 'vista'],
            'bathroom': ['bathtub', 'washroom', 'restroom', 'toilet', 'lavatory', 'marble_bathroom'],
            'pool': ['swimming', 'swim', 'infinity_pool', 'pool_area'],
            'restaurant': ['dining', 'eatery', 'cafe', 'fine_dining'],
            'lobby': ['reception', 'foyer', 'entrance', 'grand_lobby'],
            'gym': ['workout', 'exercise', 'fitness', 'fitness_center'],
            'balcony': ['terrace', 'deck', 'patio', 'outdoor_space'],
            'spa': ['wellness', 'massage', 'relaxation', 'spa_treatment'],
            'room': ['accommodation', 'bedroom', 'suite', 'space'],
            'luxury': ['premium', 'elegant', 'sophisticated', 'upscale'],
            'modern': ['contemporary', 'stylish', 'updated', 'renovated'],
            'spacious': ['large', 'roomy', 'expansive', 'generous'],
            'comfortable': ['cozy', 'relaxing', 'welcoming', 'pleasant']
        }
        
        # Map descriptive terms to guest search terms
        for guest_term, descriptive_terms in guest_search_terms.items():
            # Check if guest term appears directly
            if guest_term in caption_lower:
                tags.add(guest_term)
            
            # Check if any descriptive terms appear (map them to guest term)
            for desc_term in descriptive_terms:
                if desc_term in caption_lower:
                    tags.add(guest_term)
                    break
        
        # Room types (guest-friendly)
        room_types = ['deluxe', 'suite', 'standard', 'premium', 'executive', 'king', 'queen', 'twin']
        for room_type in room_types:
            if room_type in caption_lower:
                tags.add(room_type)
        
        # Views and features
        view_features = ['city', 'sea', 'mountain', 'garden', 'klcc', 'tower']
        for feature in view_features:
            if feature in caption_lower:
                tags.add(feature)
                tags.add('view')  # Always add 'view' when specific views are mentioned
        
        return list(tags)[:20]  # Limit to 20 tags

class MediaProcessor:
    """Process and optimize media files."""
    
    @staticmethod
    async def generate_thumbnail(image_path: str, thumbnail_path: str) -> bool:
        """Generate thumbnail for image."""
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Generate thumbnail maintaining aspect ratio
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
                return True
                
        except Exception as e:
            print(f"[ERROR] Thumbnail generation failed: {e}")
            return False
    
    @staticmethod
    def validate_file(file_path: str, file_size: int) -> Dict[str, Any]:
        """Validate uploaded file."""
        
        file_ext = Path(file_path).suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return {
                'valid': False,
                'error': f'File size {file_size/1024/1024:.1f}MB exceeds maximum {MAX_FILE_SIZE/1024/1024}MB'
            }
        
        # Check file type
        if file_ext in SUPPORTED_IMAGE_TYPES:
            file_type = 'image'
        elif file_ext in SUPPORTED_VIDEO_TYPES:
            file_type = 'video'
        elif file_ext in SUPPORTED_DOCUMENT_TYPES:
            file_type = 'document'
        else:
            return {
                'valid': False,
                'error': f'File type {file_ext} not supported'
            }
        
        return {
            'valid': True,
            'file_type': file_type,
            'file_extension': file_ext,
            'mime_type': mime_type
        }

class CloudStorageManager:
    """Cloud storage with multi-provider support."""
    
    def __init__(self):
        self.s3_client = None
        
        # Initialize AWS S3
        if CLOUD_STORAGE_ENABLED and BOTO3_AVAILABLE:
            try:
                self.s3_client = boto3.client(
                    's3',
                    region_name=AWS_REGION,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                # Test connection
                self.s3_client.head_bucket(Bucket=AWS_S3_BUCKET)
                print("[OK] AWS S3 storage connected successfully")
            except Exception as e:
                print(f"[WARN] AWS S3 initialization failed: {e}")
                self.s3_client = None
    
    async def upload_file(self, file_path: str, s3_key: str, content_type: str, is_public: bool = True) -> Optional[str]:
        """Upload file to S3 and return URL."""
        
        if not self.s3_client:
            return None
        
        try:
            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'max-age=31536000',  # 1 year cache
            }
            
            if is_public:
                extra_args['ACL'] = 'public-read'
            
            self.s3_client.upload_file(
                file_path,
                AWS_S3_BUCKET,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Generate URL
            if CLOUDFRONT_DOMAIN:
                return f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
            else:
                return f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
                
        except Exception as e:
            print(f"[ERROR] S3 upload failed: {e}")
            return None

class HotelMediaManager:
    """Main media management system for hotel operations."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
        self.captioner = AIImageCaptioner()
        self.processor = MediaProcessor()
        self.cloud_storage = CloudStorageManager()
        self._init_database()
    
    def _init_database(self):
        """Initialize media database schema."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS production_media_files (
                    file_id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    semantic_filename TEXT,
                    file_type TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    mime_type TEXT,
                    file_size INTEGER NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hotel_id TEXT NOT NULL,
                    room_type_id TEXT,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    guest_id TEXT,
                    uploader_type TEXT DEFAULT 'guest',
                    is_public BOOLEAN DEFAULT 1,
                    is_featured BOOLEAN DEFAULT 0,
                    local_path TEXT,
                    cloud_url TEXT,
                    thumbnail_path TEXT,
                    thumbnail_url TEXT,
                    ai_caption TEXT,
                    human_caption TEXT,
                    semantic_tags TEXT,
                    caption_confidence REAL,
                    caption_method TEXT,
                    image_width INTEGER,
                    image_height INTEGER,
                    processing_status TEXT DEFAULT 'pending',
                    view_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    checksum TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for fast retrieval
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_media_hotel_category ON production_media_files(hotel_id, category, is_public)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_media_semantic ON production_media_files(semantic_tags)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_media_upload_date ON production_media_files(upload_date DESC)")
            
            conn.commit()
            print("[OK] Hotel media database schema initialized")
    
    def _generate_file_id(self) -> str:
        """Generate unique file ID."""
        return str(uuid.uuid4())
    
    def _generate_semantic_filename(self, original_filename: str, caption: str, hotel_context: str) -> str:
        """Generate semantic filename."""
        
        # Extract key words from caption
        caption_words = re.findall(r'\w+', caption.lower())
        
        # Hotel context words
        context_words = re.findall(r'\w+', hotel_context.lower()) if hotel_context else []
        
        # Guest-friendly keywords
        guest_query_keywords = [
            'view', 'bathroom', 'pool', 'spa', 'restaurant', 'lobby', 'balcony',
            'king', 'queen', 'twin', 'deluxe', 'suite', 'luxury', 'spacious',
            'modern', 'gym', 'fitness', 'rooftop', 'amenities', 'interior', 'exterior'
        ]
        
        # Build semantic filename
        semantic_parts = []
        
        # Add hotel name (cleaned)
        hotel_name = ""
        if context_words:
            for word in context_words:
                if word not in ['star', 'hotel', 'in', 'kuala', 'lumpur']:
                    hotel_name += word + "_"
                    if len(hotel_name) > 20:
                        break
            if hotel_name:
                semantic_parts.append(hotel_name.rstrip('_'))
        
        # Add guest-friendly keywords from caption
        for word in caption_words:
            if word in guest_query_keywords and word not in semantic_parts:
                semantic_parts.append(word)
                if len(semantic_parts) >= 4:
                    break
        
        # Add other descriptive words
        for word in caption_words:
            if (len(word) > 3 and word not in semantic_parts and 
                word.isalpha() and word not in ['with', 'hotel', 'room', 'featuring']):
                semantic_parts.append(word)
                if len(semantic_parts) >= 6:
                    break
        
        # Get file extension
        file_ext = Path(original_filename).suffix.lower()
        
        # Create base semantic filename
        if semantic_parts:
            base_name = '_'.join(semantic_parts[:6])
        else:
            base_name = "hotel_media"
        
        # Get next sequential number
        sequence_number = self._get_next_sequence_number(base_name)
        
        # Create final semantic filename
        final_filename = f"{base_name}_{sequence_number:03d}{file_ext}"
        
        return final_filename
    
    def _get_next_sequence_number(self, base_name: str) -> int:
        """Get the next sequential number for similar filenames."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT semantic_filename 
                    FROM production_media_files 
                    WHERE semantic_filename LIKE ?
                    ORDER BY semantic_filename DESC
                    LIMIT 1
                """, (f"{base_name}_%",))
                
                result = cursor.fetchone()
                
                if result:
                    existing_filename = result[0]
                    match = re.search(r'_(\d{3})\.\w+$', existing_filename)
                    if match:
                        last_number = int(match.group(1))
                        return last_number + 1
                
                return 1
                
        except Exception as e:
            print(f"[WARN] Error getting sequence number: {e}")
            return 1
    
    async def upload_media(
        self,
        file_path: str,
        original_filename: str,
        hotel_id: str,
        category: str,
        subcategory: str = "",
        room_type_id: str = "",
        guest_id: str = "",
        uploader_type: str = "guest",
        is_public: bool = True,
        human_caption: str = ""
    ) -> Dict[str, Any]:
        """Upload and process media file with AI captioning."""
        
        try:
            # Validate file
            file_size = os.path.getsize(file_path)
            validation = self.processor.validate_file(file_path, file_size)
            
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error']
                }
            
            # Generate file ID
            file_id = self._generate_file_id()
            
            # Get hotel context
            hotel_context = await self._get_hotel_context(hotel_id, category, subcategory)
            
            # Process image and generate AI caption
            ai_caption_data = {'caption': '', 'semantic_tags': [], 'confidence': 0, 'method': 'none'}
            
            if validation['file_type'] == 'image':
                ai_caption_data = await self.captioner.generate_caption(file_path, hotel_context)
            
            # Use human caption if provided, otherwise use AI caption
            final_caption = human_caption or ai_caption_data.get('caption', 'Hotel media')
            
            # Generate semantic filename
            semantic_filename = self._generate_semantic_filename(
                original_filename, final_caption, hotel_context
            )
            
            # Setup file paths
            local_media_path = LOCAL_MEDIA_PATH / semantic_filename
            thumbnail_path = None
            thumbnail_url = None
            
            # Generate thumbnail for images
            if validation['file_type'] == 'image':
                thumbnail_filename = f"thumb_{semantic_filename}"
                thumbnail_path = LOCAL_THUMBNAILS_PATH / thumbnail_filename
                
                await self.processor.generate_thumbnail(file_path, str(thumbnail_path))
                
                # Upload thumbnail to cloud
                if self.cloud_storage.s3_client:
                    thumbnail_url = await self.cloud_storage.upload_file(
                        str(thumbnail_path), 
                        f"thumbnails/{thumbnail_filename}",
                        'image/jpeg'
                    )
            
            # Copy file to local storage
            import shutil
            shutil.copy2(file_path, local_media_path)
            
            # Upload to cloud storage
            cloud_url = None
            if self.cloud_storage.s3_client:
                cloud_url = await self.cloud_storage.upload_file(
                    str(local_media_path),
                    f"media/{semantic_filename}",
                    validation['mime_type'],
                    is_public
                )
            
            # Get image dimensions if applicable
            image_width, image_height = None, None
            if validation['file_type'] == 'image':
                try:
                    with Image.open(local_media_path) as img:
                        image_width, image_height = img.size
                except:
                    pass
            
            # Calculate file checksum
            checksum = self._calculate_checksum(str(local_media_path))
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO production_media_files (
                        file_id, original_filename, semantic_filename, file_type, 
                        file_extension, mime_type, file_size, hotel_id, room_type_id,
                        category, subcategory, guest_id, uploader_type, is_public,
                        local_path, cloud_url, thumbnail_path, thumbnail_url,
                        ai_caption, human_caption, semantic_tags, caption_confidence,
                        caption_method, image_width, image_height, checksum,
                        processing_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """, (
                    file_id, original_filename, semantic_filename, validation['file_type'],
                    validation['file_extension'], validation['mime_type'], file_size,
                    hotel_id, room_type_id or None, category, subcategory or None,
                    guest_id or None, uploader_type, is_public,
                    str(local_media_path), cloud_url, 
                    str(thumbnail_path) if thumbnail_path else None, thumbnail_url,
                    ai_caption_data.get('caption'), human_caption or None,
                    json.dumps(ai_caption_data.get('semantic_tags', [])),
                    ai_caption_data.get('confidence'), ai_caption_data.get('method'),
                    image_width, image_height, checksum
                ))
                
                conn.commit()
            
            return {
                'success': True,
                'file_id': file_id,
                'semantic_filename': semantic_filename,
                'url': cloud_url or f"/media/{semantic_filename}",
                'thumbnail_url': thumbnail_url or f"/thumbnails/thumb_{semantic_filename}",
                'caption': final_caption,
                'semantic_tags': ai_caption_data.get('semantic_tags', []),
                'file_type': validation['file_type'],
                'file_size': file_size,
                'ai_confidence': ai_caption_data.get('confidence'),
                'processing_status': 'completed'
            }
            
        except Exception as e:
            print(f"[ERROR] Media upload failed: {e}")
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }
    
    async def _get_hotel_context(self, hotel_id: str, category: str, subcategory: str) -> str:
        """Get hotel context for better AI captioning."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hotel_name, star_rating, city_name 
                    FROM hotels 
                    WHERE property_id = ?
                """, (hotel_id,))
                
                result = cursor.fetchone()
                if result:
                    hotel_name, star_rating, city = result
                    context = f"{hotel_name} {star_rating}-star hotel in {city} {category}"
                    if subcategory:
                        context += f" {subcategory}"
                    return context
                
        except Exception as e:
            print(f"[WARN] Could not get hotel context: {e}")
        
        return f"{category} {subcategory}".strip()
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum for integrity checking."""
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]

# Initialize hotel media manager
hotel_media_manager = HotelMediaManager()

@tool
def upload_hotel_media(
    file_path: str,
    original_filename: str,
    hotel_name: str,
    category: str,
    subcategory: str = "",
    room_type: str = "",
    description: str = "",
    is_featured: bool = False
) -> str:
    """
    Upload media file to hotel gallery with AI captioning.
    
    Args:
        file_path: Path to the media file
        original_filename: Original filename
        hotel_name: Name of the hotel
        category: Media category (room_interior, hotel_exterior, amenity, restaurant)
        subcategory: Specific subcategory (optional)
        room_type: Room type if applicable (optional)
        description: Human-provided description (optional)
        is_featured: Whether to feature this media (optional)
    
    Returns:
        Upload result with media details
    """
    
    try:
        # Get hotel ID
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT property_id FROM hotels 
                WHERE LOWER(hotel_name) LIKE LOWER(?)
                LIMIT 1
            """, (f"%{hotel_name}%",))
            
            result = cursor.fetchone()
            if not result:
                return f"❌ Hotel '{hotel_name}' not found"
            
            hotel_id = result[0]
        
        # Upload media asynchronously
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        upload_result = loop.run_until_complete(
            hotel_media_manager.upload_media(
                file_path=file_path,
                original_filename=original_filename,
                hotel_id=hotel_id,
                category=category,
                subcategory=subcategory,
                room_type_id=room_type,
                uploader_type="admin",
                is_public=True,
                human_caption=description
            )
        )
        
        loop.close()
        
        if upload_result['success']:
            response = f"✅ **MEDIA UPLOADED SUCCESSFULLY**\n\n"
            response += f"📸 **File:** {upload_result['semantic_filename']}\n"
            response += f"🔗 **URL:** {upload_result['url']}\n"
            
            if upload_result.get('thumbnail_url'):
                response += f"🖼️ **Thumbnail:** {upload_result['thumbnail_url']}\n"
            
            response += f"📝 **Caption:** {upload_result['caption']}\n"
            response += f"🏷️ **Tags:** {', '.join(upload_result['semantic_tags'][:5])}\n"
            response += f"📊 **AI Confidence:** {upload_result['ai_confidence']:.2f}\n"
            response += f"📁 **Type:** {upload_result['file_type']}\n"
            response += f"📏 **Size:** {upload_result['file_size']/1024:.1f} KB\n"
            
            return response
        else:
            return f"❌ Upload failed: {upload_result['error']}"
            
    except Exception as e:
        return f"❌ Media upload error: {str(e)}"

# Initialize media database
def init_hotel_media_database():
    """Initialize the hotel media database"""
    try:
        hotel_media_manager._init_database()
        print("Hotel media database schema initialized")
        return True
    except Exception as e:
        print(f"Failed to initialize hotel media database: {e}")
        return False

if __name__ == "__main__":
    print("[INIT] Hotel Media Manager initialized")
    print("[INIT] AI Captioning available:", OPENAI_AVAILABLE or BLIP_AVAILABLE)
    print("[INIT] Cloud Storage available:", CLOUD_STORAGE_ENABLED)
    print("[INIT] Hotel media upload tools ready") 
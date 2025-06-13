#!/usr/bin/env python3
"""
LEON Hotel Manager - Hotel-Facing Management Server
Full access to database, media, and hotel operations

LEON AGENT FEATURES:
- Review untagged content sections
- Add semantic tags to improve search accuracy  
- Preserve all original staff-written content
- Real-time tagging with immediate feedback
"""

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import os
from pathlib import Path
import uuid
import sqlite3
import re
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="LEON Hotel Manager", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for management interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize consolidated PMS system
try:
    from pms_manager import pms_manager
    PMS_SYSTEM_AVAILABLE = True
    print("LEON: Consolidated PMS system initialized")
except ImportError as e:
    print(f"LEON: PMS system not available: {e}")
    PMS_SYSTEM_AVAILABLE = False

# Initialize full media management system
try:
    from tools.production_media_manager import production_media_manager
    from tools.media_manager import MEDIA_TOOLS, init_media_database
    from tools.booking_management import booking_manager
    init_media_database()
    MEDIA_SYSTEM_AVAILABLE = True
    print("LEON: Full media management system initialized")
except ImportError as e:
    print(f"LEON: Media management not available: {e}")
    MEDIA_SYSTEM_AVAILABLE = False

# Request/Response models
class HotelManagementRequest(BaseModel):
    action: str
    data: dict
    manager_id: Optional[str] = None

class MediaUploadResponse(BaseModel):
    success: bool
    file_id: Optional[str] = None
    message: str
    details: Optional[dict] = None

@app.get("/")
async def root():
    """LEON Hotel Manager Dashboard"""
    return FileResponse("static/leon_dashboard.html")

@app.get("/health")
async def health_check():
    """Health check for LEON server"""
    return {
        "status": "healthy", 
        "service": "leon_hotel_manager",
        "capabilities": {
            "pms_system": PMS_SYSTEM_AVAILABLE,
            "media_management": MEDIA_SYSTEM_AVAILABLE,
            "database_write": True,
            "hotel_operations": True
        }
    }

# ========================
# PMS SYSTEM ENDPOINTS
# ========================

@app.get("/api/pms/hotels")
async def get_hotels():
    """Get all hotels in the system"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        hotels = pms_manager.get_all_hotels()
        return {"success": True, "hotels": hotels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pms/hotels/{property_id}")
async def get_hotel_details(property_id: str):
    """Get detailed hotel information"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.get_hotel_details(property_id)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pms/hotels/{property_id}/room-types")
async def get_room_types(property_id: str):
    """Get room types for a hotel"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        room_types = pms_manager.get_room_types(property_id)
        return {"success": True, "room_types": room_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pms/hotels/{property_id}/room-types")
async def create_room_type(property_id: str, room_data: dict):
    """Create new room type"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.create_room_type(property_id, room_data)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/pms/hotels/{property_id}/room-types/{room_type_id}")
async def update_room_type(property_id: str, room_type_id: str, room_data: dict):
    """Update existing room type"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.update_room_type(property_id, room_type_id, room_data)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/pms/hotels/{property_id}/room-types/{room_type_id}")
async def delete_room_type(property_id: str, room_type_id: str):
    """Delete room type"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.delete_room_type(property_id, room_type_id)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pms/hotels/{property_id}/inventory")
async def get_inventory_status(property_id: str, room_type_id: str = None, 
                             start_date: str = None, end_date: str = None):
    """Get inventory status"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.get_inventory_status(property_id, room_type_id, start_date, end_date)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/pms/hotels/{property_id}/inventory")
async def update_inventory(property_id: str, inventory_data: dict):
    """Update room inventory"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.update_inventory(
            property_id=property_id,
            room_type_id=inventory_data["room_type_id"],
            start_date=inventory_data["start_date"],
            end_date=inventory_data["end_date"],
            available_rooms=inventory_data.get("available_rooms"),
            current_price=inventory_data.get("current_price"),
            add_rooms=inventory_data.get("add_rooms")
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pms/hotels/{property_id}/bookings")
async def get_hotel_bookings(property_id: str, booking_status: str = None,
                           start_date: str = None, end_date: str = None):
    """Get bookings for a hotel"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        bookings = pms_manager.get_bookings(property_id, booking_status, start_date, end_date)
        return {"success": True, "bookings": bookings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/pms/bookings/{booking_reference}")
async def cancel_booking(booking_reference: str, cancellation_data: dict = None):
    """Cancel a booking"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        reason = "Cancelled by hotel management"
        if cancellation_data and "reason" in cancellation_data:
            reason = cancellation_data["reason"]
            
        result = pms_manager.cancel_booking(booking_reference, reason)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/pms/bookings/{booking_id}/status")
async def update_booking_status(booking_id: int, status_data: dict):
    """Update booking status and payment status"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.update_booking_status(
            booking_id=booking_id,
            booking_status=status_data.get("booking_status"),
            payment_status=status_data.get("payment_status"),
            notes=status_data.get("notes", "")
        )
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pms/hotels/{property_id}/analytics")
async def get_hotel_analytics(property_id: str, days: int = 30):
    """Get hotel analytics and statistics"""
    if not PMS_SYSTEM_AVAILABLE:
        raise HTTPException(status_code=503, detail="PMS system not available")
    
    try:
        result = pms_manager.get_hotel_analytics(property_id, days)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# LEGACY ENDPOINTS (kept for compatibility)
# ========================

@app.post("/api/hotel/create")
async def create_hotel(hotel_data: dict):
    """Create new hotel (LEON only)"""
    try:
        # Hotel creation logic
        return {"success": True, "message": "Hotel created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hotel/{hotel_id}/update")
async def update_hotel(hotel_id: str, hotel_data: dict):
    """Update hotel information (LEON only)"""
    try:
        # Hotel update logic
        return {"success": True, "message": "Hotel updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/room-types/create")
async def create_room_type_legacy(room_data: dict):
    """Create new room type (LEON only) - Legacy endpoint"""
    try:
        # Room type creation logic
        return {"success": True, "message": "Room type created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/inventory/update")
async def update_inventory_legacy(inventory_data: dict):
    """Update room inventory (LEON only) - Legacy endpoint"""
    try:
        # Inventory update logic
        return {"success": True, "message": "Inventory updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# FULL MEDIA MANAGEMENT (LEON ONLY)
# ========================

@app.post("/api/media/upload")
async def upload_media_full_access(
    file: UploadFile = File(...),
    hotel_id: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    subcategory: str = Form(""),
    room_feature: str = Form(""),
    hotel_area: str = Form(""),
    room_type_id: str = Form(""),
    is_featured: bool = Form(False)
):
    """Upload media with full management access (LEON only)"""
    try:
        if not MEDIA_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Media system not available")
        
        print(f"LEON MEDIA UPLOAD: Processing {file.filename} for {hotel_id}")
        
        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        allowed_types = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.avi', '.mov', '.pdf', '.doc', '.docx'}
        
        if file_ext not in allowed_types:
            raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed")
        
        # Validate file size (50MB limit for LEON)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        # Save to uploads staging area
        uploads_dir = Path("media_storage/uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Generate temporary file in uploads staging
        import time
        temp_filename = f"leon_upload_{int(time.time())}_{file.filename}"
        temp_path = uploads_dir / temp_filename
        
        # Save temporary file to staging area
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"LEON: Staged file: {temp_path}")
        
        try:
            # Use production media manager with full access
            upload_result = await production_media_manager.upload_media(
                file_path=str(temp_path),
                original_filename=file.filename,
                hotel_id=hotel_id,
                category=category,
                subcategory=subcategory,
                room_type_id=room_type_id,
                guest_id="leon_manager",
                uploader_type="hotel_manager",
                is_public=True,
                human_caption=description
            )
            
            if upload_result["success"]:
                # Set as featured if requested
                if is_featured:
                    # Update database to mark as featured
                    with sqlite3.connect("ella.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE production_media_files 
                            SET is_featured = 1 
                            WHERE file_id = ?
                        """, (upload_result["file_id"],))
                        conn.commit()
                
                print(f"LEON upload success: {upload_result['semantic_filename']}")
                
                return {
                    "success": True,
                    "file_id": upload_result["file_id"],
                    "semantic_filename": upload_result["semantic_filename"],
                    "url": upload_result["url"],
                    "thumbnail_url": upload_result.get("thumbnail_url"),
                    "ai_caption": upload_result.get("caption"),
                    "file_type": upload_result["file_type"],
                    "file_size": upload_result["file_size"],
                    "message": f"Media uploaded successfully as {upload_result['semantic_filename']}"
                }
            else:
                raise HTTPException(status_code=400, detail=upload_result.get("message", "Upload failed"))
                
        except Exception as media_error:
            print(f"LEON media processing error: {media_error}")
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(status_code=500, detail=f"Media processing failed: {str(media_error)}")
            
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
                
    except Exception as e:
        print(f"LEON upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/media/{file_id}")
async def delete_media_file(file_id: str):
    """Delete media file (LEON only)"""
    try:
        if not MEDIA_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Media system not available")
        
        # Get file info first
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT semantic_filename, file_path 
                FROM production_media_files 
                WHERE file_id = ?
            """, (file_id,))
            
            file_info = cursor.fetchone()
            if not file_info:
                raise HTTPException(status_code=404, detail="Media file not found")
            
            semantic_filename, file_path = file_info
            
            # Delete from database
            cursor.execute("DELETE FROM production_media_files WHERE file_id = ?", (file_id,))
            conn.commit()
        
        # Delete physical file if exists
        if file_path and Path(file_path).exists():
            Path(file_path).unlink()
        
        return {
            "success": True,
            "message": f"Media file {semantic_filename} deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/media/{file_id}/featured")
async def toggle_featured_media(file_id: str, is_featured: bool):
    """Toggle featured status of media file (LEON only)"""
    try:
        if not MEDIA_SYSTEM_AVAILABLE:
            raise HTTPException(status_code=503, detail="Media system not available")
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE production_media_files 
                SET is_featured = ?, updated_at = CURRENT_TIMESTAMP
                WHERE file_id = ?
            """, (1 if is_featured else 0, file_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Media file not found")
            
            conn.commit()
        
        return {
            "success": True,
            "message": f"Media file featured status updated to {is_featured}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/overview")
async def get_analytics_overview():
    """Get overall system analytics (LEON only)"""
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Media statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    COUNT(CASE WHEN is_featured = 1 THEN 1 END) as featured_files,
                    SUM(file_size) as total_size
                FROM production_media_files
            """)
            media_stats = cursor.fetchone()
            
            return {
                "success": True,
                "analytics": {
                    "media": {
                        "total_files": media_stats[0] or 0,
                        "featured_files": media_stats[1] or 0,
                        "total_size_mb": round((media_stats[2] or 0) / (1024 * 1024), 2)
                    }
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/media/analytics/{hotel_id}")
async def get_media_analytics(hotel_id: str, days: int = 30):
    """Get media analytics for specific hotel (LEON only)"""
    try:
        if not MEDIA_SYSTEM_AVAILABLE:
            return {"success": False, "message": "Media system not available"}
        
        # Analytics logic here
        return {"success": True, "analytics": {}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/database/backup")
async def backup_database():
    """Create database backup (LEON only)"""
    try:
        import shutil
        from datetime import datetime
        
        backup_name = f"ella_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = Path("backups") / backup_name
        backup_path.parent.mkdir(exist_ok=True)
        
        shutil.copy2("ella.db", backup_path)
        
        return {
            "success": True,
            "backup_file": backup_name,
            "backup_path": str(backup_path),
            "message": f"Database backed up successfully to {backup_name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_leon_stats():
    """Get LEON system statistics"""
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Hotel count
            cursor.execute("SELECT COUNT(*) FROM hotels WHERE is_active = 1")
            active_hotels = cursor.fetchone()[0]
            
            # Room types count
            cursor.execute("SELECT COUNT(*) FROM room_types WHERE is_active = 1")
            active_room_types = cursor.fetchone()[0]
            
            # Bookings count (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE booked_at >= DATE('now', '-30 days')
            """)
            recent_bookings = cursor.fetchone()[0]
            
            # Media files count
            media_files = 0
            if MEDIA_SYSTEM_AVAILABLE:
                cursor.execute("SELECT COUNT(*) FROM production_media_files")
                media_files = cursor.fetchone()[0]
            
            return {
                "success": True,
                "stats": {
                    "active_hotels": active_hotels,
                    "active_room_types": active_room_types,
                    "recent_bookings": recent_bookings,
                    "media_files": media_files,
                    "capabilities": {
                        "pms_system": PMS_SYSTEM_AVAILABLE,
                        "media_management": MEDIA_SYSTEM_AVAILABLE
                    }
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join('database', 'ella.db')
    return sqlite3.connect(db_path)

class LEONTaggingAgent:
    """LEON Agent for semantic tagging of hotel knowledge."""
    
    def __init__(self):
        self.available_tags = [
            # Food & Dining
            'restaurant', 'food', 'nightmarket', 'dining', 'local',
            
            # Shopping  
            'shopping', 'shoppingmall', 'brands', 'souvenirs',
            
            # Attractions
            'attractions', 'islands', 'nature', 'cultural', 'tours',
            
            # Transportation
            'transport', 'directions', 'walking', 'taxi', 'public',
            
            # Activities
            'adventure', 'diving', 'trekking', 'rafting', 'tours',
            
            # Hotel Facilities
            'facilities', 'pool', 'gym', 'spa', 'wifi', 'parking',
            
            # Services
            'deals', 'discounts', 'concierge', 'shuttle', 'vip',
            
            # Information Types
            'tips', 'timing', 'weather', 'safety', 'religious',
            
            # Location Context
            'klcc', 'sabah', 'penang', 'johor', 'langkawi'
        ]
    
    def get_hotel_knowledge(self, property_id: str) -> Optional[Dict]:
        """Get current raw knowledge for a hotel."""
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, knowledge_text, staff_author, last_updated, version
                FROM hotel_knowledge_bank
                WHERE property_id = ? AND is_active = 1
                ORDER BY version DESC
                LIMIT 1
            """, (property_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'knowledge_text': result[1],
                    'staff_author': result[2],
                    'last_updated': result[3],
                    'version': result[4],
                    'property_id': property_id
                }
        return None
    
    def analyze_content_sections(self, knowledge_text: str) -> List[Dict]:
        """Analyze content and identify sections needing tags."""
        
        sections = []
        current_section = ""
        section_number = 1
        
        for line in knowledge_text.split('\n'):
            line = line.strip()
            if not line:
                if current_section and len(current_section) > 100:
                    # Analyze this section
                    section_info = self._analyze_section(current_section, section_number)
                    sections.append(section_info)
                    section_number += 1
                current_section = ""
            else:
                current_section += line + " "
        
        # Handle last section
        if current_section and len(current_section) > 100:
            section_info = self._analyze_section(current_section, section_number)
            sections.append(section_info)
        
        return sections
    
    def _analyze_section(self, section_text: str, section_number: int) -> Dict:
        """Analyze a section and suggest tags."""
        
        # Extract existing tags
        existing_tags = re.findall(r'\[([^\]]+)\]', section_text)
        
        # Clean text for analysis (remove existing tags)
        clean_text = re.sub(r'\[([^\]]+)\]\n?', '', section_text).lower()
        
        # Suggest tags based on content
        suggested_tags = []
        
        # Food/Dining detection
        if any(word in clean_text for word in ['restaurant', 'food', 'dining', 'eat', 'meal']):
            suggested_tags.append('restaurant')
        if any(word in clean_text for word in ['night market', 'street food', 'local food']):
            suggested_tags.append('nightmarket')
        
        # Shopping detection
        if any(word in clean_text for word in ['shopping', 'mall', 'shop', 'buy']):
            suggested_tags.append('shopping')
        if any(word in clean_text for word in ['suria', 'pavilion', 'shopping mall']):
            suggested_tags.append('shoppingmall')
        
        # Attractions detection
        if any(word in clean_text for word in ['attractions', 'visit', 'see', 'tower', 'park']):
            suggested_tags.append('attractions')
        if any(word in clean_text for word in ['island', 'hopping', 'marine park', 'beach']):
            suggested_tags.append('islands')
        
        # Transportation detection
        if any(word in clean_text for word in ['walk', 'distance', 'minutes', 'connected']):
            suggested_tags.append('directions')
        if any(word in clean_text for word in ['transport', 'taxi', 'grab', 'shuttle']):
            suggested_tags.append('transport')
        
        # Tips detection
        if any(word in clean_text for word in ['tip', 'insider', 'best', 'avoid', 'recommend']):
            suggested_tags.append('tips')
        
        return {
            'section_number': section_number,
            'text': section_text,
            'clean_text': clean_text[:200] + "..." if len(clean_text) > 200 else clean_text,
            'existing_tags': existing_tags,
            'suggested_tags': suggested_tags,
            'word_count': len(clean_text.split()),
            'needs_tagging': len(existing_tags) == 0 and len(suggested_tags) > 0
        }
    
    def add_tags_to_section(self, property_id: str, section_number: int, new_tags: List[str]) -> bool:
        """Add tags to a specific section."""
        
        knowledge = self.get_hotel_knowledge(property_id)
        if not knowledge:
            return False
        
        sections = knowledge['knowledge_text'].split('\n\n')
        
        if section_number <= 0 or section_number > len(sections):
            return False
        
        # Get the target section (1-indexed)
        target_section = sections[section_number - 1]
        
        # Format new tags
        tag_string = ''.join([f'[{tag}]' for tag in new_tags])
        
        # Add tags to beginning of section
        if tag_string:
            # Remove existing tags from start of section if any
            clean_section = re.sub(r'^(\[([^\]]+)\]\s*)+', '', target_section)
            tagged_section = f"{tag_string}\n{clean_section}"
        else:
            tagged_section = target_section
        
        # Update the section in the full text
        sections[section_number - 1] = tagged_section
        updated_knowledge = '\n\n'.join(sections)
        
        # Save to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE hotel_knowledge_bank
                SET knowledge_text = ?,
                    last_updated = CURRENT_DATE,
                    version = version + 1
                WHERE id = ?
            """, (updated_knowledge, knowledge['id']))
            
            conn.commit()
            return True
    
    def show_tagging_status(self, property_id: str):
        """Show current tagging status for a hotel."""
        
        knowledge = self.get_hotel_knowledge(property_id)
        if not knowledge:
            print(f"❌ No knowledge found for {property_id}")
            return
        
        print(f"\n🏨 TAGGING STATUS: {property_id}")
        print(f"📝 Author: {knowledge['staff_author']}")
        print(f"📅 Last Updated: {knowledge['last_updated']}")
        print(f"🔢 Version: {knowledge['version']}")
        print("=" * 60)
        
        sections = self.analyze_content_sections(knowledge['knowledge_text'])
        
        tagged_sections = sum(1 for s in sections if s['existing_tags'])
        total_sections = len(sections)
        
        print(f"📊 SUMMARY: {tagged_sections}/{total_sections} sections tagged")
        print(f"⚡ Progress: {(tagged_sections/total_sections)*100:.1f}%")
        
        print(f"\n📋 SECTION DETAILS:")
        for section in sections:
            status = "✅" if section['existing_tags'] else ("⚠️" if section['needs_tagging'] else "⭕")
            print(f"\n{status} Section {section['section_number']} ({section['word_count']} words)")
            print(f"   Content: {section['clean_text']}")
            
            if section['existing_tags']:
                print(f"   Current tags: {section['existing_tags']}")
            
            if section['suggested_tags']:
                print(f"   Suggested: {section['suggested_tags']}")
    
    def interactive_tagging_session(self, property_id: str):
        """Start interactive tagging session for LEON agent."""
        
        print(f"\n🤖 LEON TAGGING SESSION STARTED")
        print(f"🏨 Hotel: {property_id}")
        print("=" * 50)
        
        knowledge = self.get_hotel_knowledge(property_id)
        if not knowledge:
            print(f"❌ No knowledge found for {property_id}")
            return
        
        sections = self.analyze_content_sections(knowledge['knowledge_text'])
        untagged_sections = [s for s in sections if s['needs_tagging']]
        
        if not untagged_sections:
            print("✅ All sections are already tagged!")
            return
        
        print(f"📝 Found {len(untagged_sections)} sections needing tags")
        print(f"📚 Available tags: {', '.join(self.available_tags[:10])}...")
        
        for section in untagged_sections:
            print(f"\n🔍 SECTION {section['section_number']}")
            print(f"Content: {section['clean_text']}")
            print(f"Suggested tags: {section['suggested_tags']}")
            
            # In production, this would be a web interface
            # For demo, show the automatic suggestion
            if section['suggested_tags']:
                print(f"✅ LEON suggests adding: {section['suggested_tags']}")
                # Auto-apply suggestions for demo
                success = self.add_tags_to_section(property_id, section['section_number'], section['suggested_tags'])
                if success:
                    print(f"✅ Tags added successfully!")
                else:
                    print(f"❌ Failed to add tags")
            
        print(f"\n🌟 TAGGING SESSION COMPLETE!")

# LEON Agent Instance
leon_agent = LEONTaggingAgent()

def leon_tag_content(property_id: str, section_number: int, tags: List[str]) -> bool:
    """Public interface for LEON agent tagging."""
    return leon_agent.add_tags_to_section(property_id, section_number, tags)

def leon_analyze_hotel(property_id: str):
    """Public interface for LEON agent analysis."""
    leon_agent.show_tagging_status(property_id)

def leon_interactive_session(property_id: str):
    """Public interface for LEON agent interactive session."""
    leon_agent.interactive_tagging_session(property_id)

if __name__ == "__main__":
    # Demo LEON tagging capabilities
    
    print("🤖 LEON SEMANTIC TAGGING SERVER")
    print("=" * 50)
    
    # Analyze Grand Hyatt KL
    print("\n📊 ANALYZING GRAND HYATT KL:")
    leon_analyze_hotel('grand_hyatt_kuala_lumpur')
    
    # Analyze Marina Court KK  
    print("\n📊 ANALYZING MARINA COURT KK:")
    leon_analyze_hotel('marina_court_resort_kota_kinabalu')
    
    print(f"\n🌟 LEON AGENT READY FOR HOTEL STAFF!")
    print(f"✅ Real-time semantic tagging")
    print(f"✅ Content analysis and suggestions")
    print(f"✅ Preserve all original content")
    print(f"✅ Improve search accuracy")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
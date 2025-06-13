#!/usr/bin/env python3
"""
Concierge Session Management
Caches hotel context for seamless amenity/service queries
"""

import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict
from .guest_id import get_guest_id

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def store_concierge_session(
    guest_id: str,
    hotel_name: str,
    hotel_context: Optional[Dict] = None
) -> bool:
    """
    Store concierge session with hotel context
    
    Args:
        guest_id: Guest identifier
        hotel_name: Identified hotel name
        hotel_context: Additional hotel context (optional)
    
    Returns:
        Success status
    """
    try:
        session_data = {
            'hotel_name': hotel_name,
            'identified_at': datetime.now().isoformat(),
            'guest_id': guest_id,
            'context': hotel_context or {}
        }
        
        key = f"concierge_session:{guest_id}"
        
        # Store with 24-hour expiration (guest stay duration)
        redis_client.setex(
            key, 
            timedelta(hours=24),
            json.dumps(session_data)
        )
        
        print(f"🏨 CONCIERGE SESSION STORED: {guest_id} → {hotel_name}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to store concierge session: {e}")
        return False

def get_concierge_session(guest_id: str) -> Optional[Dict]:
    """
    Get cached concierge session for guest
    
    Args:
        guest_id: Guest identifier
        
    Returns:
        Session data or None if not found
    """
    try:
        key = f"concierge_session:{guest_id}"
        session_json = redis_client.get(key)
        
        if session_json:
            session_data = json.loads(session_json)
            print(f"🏨 CONCIERGE SESSION FOUND: {guest_id} → {session_data['hotel_name']}")
            return session_data
        
        print(f"🏨 CONCIERGE SESSION NOT FOUND: {guest_id}")
        return None
        
    except Exception as e:
        print(f"❌ Failed to get concierge session: {e}")
        return None

def update_concierge_session(
    guest_id: str, 
    updates: Dict
) -> bool:
    """
    Update existing concierge session
    
    Args:
        guest_id: Guest identifier
        updates: Updates to apply
        
    Returns:
        Success status
    """
    try:
        session = get_concierge_session(guest_id)
        if not session:
            return False
        
        # Apply updates
        session.update(updates)
        session['updated_at'] = datetime.now().isoformat()
        
        key = f"concierge_session:{guest_id}"
        
        # Store updated session with fresh expiration
        redis_client.setex(
            key,
            timedelta(hours=24),
            json.dumps(session)
        )
        
        print(f"🏨 CONCIERGE SESSION UPDATED: {guest_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update concierge session: {e}")
        return False

def clear_concierge_session(guest_id: str) -> bool:
    """
    Clear concierge session for guest
    
    Args:
        guest_id: Guest identifier
        
    Returns:
        Success status
    """
    try:
        key = f"concierge_session:{guest_id}"
        redis_client.delete(key)
        
        print(f"🏨 CONCIERGE SESSION CLEARED: {guest_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear concierge session: {e}")
        return False

def identify_hotel_from_text(text: str) -> Optional[str]:
    """
    Extract hotel name from guest text using database matching
    
    Args:
        text: Guest message text
        
    Returns:
        Identified hotel name or None
    """
    try:
        import sqlite3
        
        # Get database connection
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get all active hotel names
            cursor.execute("""
                SELECT hotel_name FROM hotels 
                WHERE is_active = 1
                ORDER BY LENGTH(hotel_name) DESC
            """)
            
            hotels = [row[0] for row in cursor.fetchall()]
            
            text_lower = text.lower()
            
            # Try exact matches first
            for hotel in hotels:
                if hotel.lower() in text_lower:
                    print(f"🎯 HOTEL IDENTIFIED: '{hotel}' from '{text}'")
                    return hotel
            
            # Try partial matches with common abbreviations
            for hotel in hotels:
                hotel_lower = hotel.lower()
                
                # Handle "Grand Hyatt KL" → "Grand Hyatt Kuala Lumpur"
                if 'grand hyatt' in text_lower and 'grand hyatt' in hotel_lower:
                    if ('kl' in text_lower or 'kuala lumpur' in text_lower) and 'kuala lumpur' in hotel_lower:
                        print(f"🎯 HOTEL IDENTIFIED (abbreviation): '{hotel}' from '{text}'")
                        return hotel
                
                # Other hotel matching logic can be added here
                
            print(f"🔍 NO HOTEL IDENTIFIED from: '{text}'")
            return None
            
    except Exception as e:
        print(f"❌ Hotel identification failed: {e}")
        return None

def get_or_request_hotel_context(guest_id: str, query: str) -> tuple[Optional[str], bool]:
    """
    Get cached hotel context or determine if we need to request it
    
    Args:
        guest_id: Guest identifier
        query: Current guest query
        
    Returns:
        (hotel_name, needs_hotel_request) tuple
    """
    
    # First, try to identify hotel from current query
    identified_hotel = identify_hotel_from_text(query)
    if identified_hotel:
        # Store the identified hotel in session
        store_concierge_session(guest_id, identified_hotel)
        return identified_hotel, False
    
    # Check if we have cached hotel context
    session = get_concierge_session(guest_id)
    if session and session.get('hotel_name'):
        return session['hotel_name'], False
    
    # No hotel context - need to request it
    return None, True

# Helper function for easy import
def get_guest_hotel_context(guest_id: Optional[str] = None) -> Optional[str]:
    """
    Quick helper to get guest's cached hotel context
    
    Args:
        guest_id: Guest identifier (uses current guest if None)
        
    Returns:
        Hotel name or None
    """
    if guest_id is None:
        guest_id = get_guest_id()
    
    session = get_concierge_session(guest_id)
    return session.get('hotel_name') if session else None 
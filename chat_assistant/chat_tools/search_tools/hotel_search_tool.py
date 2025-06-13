#!/usr/bin/env python3
"""
Hotel Search Tool for Ella (Read-Only)
Main search functionality with intelligent extraction and session management
"""

from langchain_core.tools import tool
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import json
import re
import uuid
import sqlite3

# Simple database connection - same pattern as rest of codebase
def get_db_connection(db_path: str = "ella.db"):
    """Get database connection."""
    return sqlite3.connect(db_path)

# Import media tools for photo integration
try:
    from ..media_sharer import get_hotel_photos, get_room_photos
    print("Media tools loaded successfully")
    MEDIA_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"Media tools not available: {e}")
    MEDIA_TOOLS_AVAILABLE = False

@tool
def search_hotels(query: str, conversation_context: str = "") -> str:
    """
    Search for hotels based on natural language query (READ-ONLY).
    REQUIRES check-in dates and guest count for accurate availability pricing.
    
    Args:
        query: Natural language hotel search query (e.g., "hotel in KK for tomorrow, sea view")
        conversation_context: Previous conversation context to help with understanding
        
    Returns:
        Formatted search results with hotel recommendations OR request for dates
    """
    
    try:
        print(f"ELLA HOTEL SEARCH (READ-ONLY): '{query}'")
        
        # ENHANCED: LLM-based keyword and filter extraction
        keywords, filters, check_in, check_out = extract_search_criteria_with_llm(query, conversation_context)
        
        # CHECK IF DATES ARE MISSING FROM QUERY
        query_lower = query.lower()
        has_date_info = any(word in query_lower for word in [
            'today', 'tomorrow', 'harini', 'esok', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
            'januari', 'februari', 'mac', 'april', 'mei', 'jun', 'julai', 'ogos', 'september', 'oktober', 'november', 'disember',
            '2025', '2026', 'next week', 'minggu depan', 'bulan depan', 'next month'
        ])
        
        # If no date information in query, ask for it
        if not has_date_info:
            city_name = keywords.get('city', 'hotel yang anda cari')
            return (
                f"Untuk check harga dan availability untuk {city_name}, "
                f"bila tarikh check-in anda? Dan berapa ramai tetamu dewasa? "
                f"(Contoh: '15 June, 2 orang')"
            )
        
        # ENHANCED: Track guest preferences for learning
        from memory.redis_memory import track_search_preference, get_guest_preferences
        from core.guest_id import get_guest_id
        
        guest_id = get_guest_id()
        
        # === CRITICAL PREFERENCE INTEGRATION ===
        try:
            from memory.mongo_memory import process_guest_message_for_critical_preferences, get_persistent_profile, get_critical_preferences_for_search
            
            # Process current query for critical preferences
            process_guest_message_for_critical_preferences(guest_id, query)
            
            # Get persistent critical preferences
            persistent_profile = get_persistent_profile(guest_id)
            critical_filters = get_critical_preferences_for_search(guest_id)
            
            if persistent_profile:
                print(f"APPLYING CRITICAL PREFERENCES: {persistent_profile}")
            
            # Merge critical filters with extracted filters (critical preferences take priority)
            filters.update(critical_filters)
        except ImportError:
            print("MongoDB preferences not available")
        
        # Track this search for future personalization
        if keywords.get('city'):
            budget_range = None
            # Could extract budget from query in future
            track_search_preference(
                guest_id, 
                keywords['city'],
                view_type=filters.get('view_type'),
                bed_type=filters.get('bed_type'),
                budget_range=budget_range
            )
        
        # Get learned preferences for enhanced search
        preferences = get_guest_preferences(guest_id)
        print(f"LEARNED PREFERENCES: {preferences}")
        
        print(f"SEARCH CRITERIA (LLM-extracted):")
        print(f"   City: {keywords.get('city', 'Any')}")
        print(f"   Check-in: {check_in}")
        print(f"   Check-out: {check_out}")
        print(f"   View: {filters.get('view_type', 'Any')}")
        print(f"   Bed: {filters.get('bed_type', 'Any')}")
        print(f"   Guests: {filters.get('max_occupancy', 'Any')}")
        
        # Search hotels using refactored function
        results = search_hotels_with_availability(keywords, filters, check_in, check_out)
        
        print(f"FOUND {len(results)} hotels")
        
        # 💾 STORE SEARCH SESSION for persistence across tools
        from memory.redis_memory import store_search_session_with_invalidation
        if keywords.get('city') and check_in and filters.get('max_occupancy'):
            store_search_session_with_invalidation(
                guest_id,
                city=keywords['city'],
                check_in=check_in.strftime('%Y-%m-%d'),
                check_out=check_out.strftime('%Y-%m-%d'),
                adults=filters['max_occupancy'],
                room_type=filters.get('bed_type'),  # Critical slot
                preferences=filters.get('view_type')  # Critical slot
            )
        
        # Generate response
        if not results:
            # ENHANCED: Suggest based on preferences if no results
            suggestion = ""
            if preferences.get('recent_city') and preferences['recent_city'] != keywords.get('city'):
                suggestion = f" Cuba cari di {preferences['recent_city']} ke?"
            
            return f"SEARCH_RESULT:NO_CRITERIA_MATCH|{keywords.get('city', 'any')}|{suggestion}"
        
        response = f"Ada {len(results)} hotel yang sesuai:\n\n"
        
        for i, hotel in enumerate(results[:3], 1):  # Show top 3
            response += f"{i}. 🏨 {hotel['hotel_name']} ({hotel['star_rating']}⭐)\n"
            response += f"   📍 {hotel['city_name']}\n"
            response += f"   🛏️ {hotel['room_count']} bilik tersedia\n"
            response += f"   💰 Dari {hotel['price_display']}\n"
            if hotel['distance_to_airport_km']:
                response += f"   ✈️ {hotel['distance_to_airport_km']} km dari airport\n"
            
            # ENHANCED: Add personalized notes based on preferences
            if preferences.get('preferred_view') and any(room['view_type'] == preferences['preferred_view'] for room in hotel['available_rooms']):
                response += f"   ⭐ Ada {preferences['preferred_view']} view yang awak suka!\n"
            
            response += "\n"
        
        if len(results) > 3:
            response += f"...dan {len(results) - 3} hotel lagi tersedia.\n\n"
        
        response += "Nak saya tunjukkan details atau book mana satu?"
        
        return response
        
    except Exception as e:
        print(f"HOTEL SEARCH ERROR: {e}")
        return f"❌ Search failed: {str(e)}"

def extract_search_criteria_with_llm(query: str, conversation_context: str = "") -> tuple:
    """
    Use LLM to intelligently extract search criteria from natural language query.
    
    Returns:
        tuple: (keywords dict, filters dict, check_in date, check_out date)
    """
    from langchain_openai import ChatOpenAI
    from config.settings import ***REMOVED***
    import json
    from datetime import date, timedelta
    
    llm = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o", temperature=0.0)
    
    # Build context-aware prompt
    context_info = f"\n\nCONVERSATION CONTEXT:\n{conversation_context}" if conversation_context.strip() else ""
    
    extraction_prompt = f"""You are a hotel search query analyzer. Extract search criteria from this query: "{query}"{context_info}

You must return ONLY a valid JSON object with these exact fields. Use null for unknown values:

{{
  "city": "Kuala Lumpur" or "Kota Kinabalu" or "Georgetown" or null,
  "view_type": "Sea" or "Pool" or "City" or "Garden" or null, 
  "bed_type": "Single" or "Double" or "Queen" or "King" or "Twin" or null,
  "max_occupancy": 1 or 2 or 3 or 4 or null,
  "check_in_offset": 0,
  "stay_duration": 1
}}

RULES:
- For "KK" use "Kota Kinabalu"
- For "KL" use "Kuala Lumpur" 
- For "today/harini" use check_in_offset: 0
- For "tomorrow/esok" use check_in_offset: 1
- For "3 nights" use stay_duration: 3
- For "2 people" use max_occupancy: 2
- Only return the JSON object, no explanation
- Ensure all strings are in quotes
- Use exact spelling for cities and values"""

    try:
        response = llm.invoke([{"role": "user", "content": extraction_prompt}])
        response_content = response.content.strip()
        
        # Clean up response to ensure it's valid JSON
        if response_content.startswith('```json'):
            response_content = response_content.replace('```json', '').replace('```', '').strip()
        elif response_content.startswith('```'):
            response_content = response_content.replace('```', '').strip()
        
        print(f"LLM RAW RESPONSE: {response_content}")
        
        extracted_data = json.loads(response_content)
        print(f"LLM PARSED DATA: {extracted_data}")
        
        # Process extracted data
        keywords = {}
        filters = {}
        
        # City extraction
        if extracted_data.get('city'):
            keywords['city'] = extracted_data['city']
        
        # Date calculations
        today = date.today()
        check_in_offset = extracted_data.get('check_in_offset', 1)  # Default tomorrow
        stay_duration = extracted_data.get('stay_duration', 1)    # Default 1 night
        
        check_in = today + timedelta(days=check_in_offset)
        check_out = check_in + timedelta(days=stay_duration)
        
        # Filter extraction
        if extracted_data.get('view_type'):
            filters['view_type'] = extracted_data['view_type']
        
        if extracted_data.get('bed_type'):
            filters['bed_type'] = extracted_data['bed_type']
        
        if extracted_data.get('max_occupancy'):
            filters['max_occupancy'] = extracted_data['max_occupancy']
        
        return keywords, filters, check_in, check_out
        
    except Exception as e:
        print(f"LLM EXTRACTION ERROR: {e}")
        # Fallback to simple extraction
        return extract_search_criteria_simple(query)

def extract_search_criteria_simple(query: str) -> tuple:
    """
    Simple fallback extraction if LLM fails
    """
    keywords = {}
    filters = {}
    
    query_lower = query.lower()
    
    # City detection
    if 'kl' in query_lower or 'kuala lumpur' in query_lower:
        keywords['city'] = 'Kuala Lumpur'
    elif 'kk' in query_lower or 'kota kinabalu' in query_lower:
        keywords['city'] = 'Kota Kinabalu'
    elif 'georgetown' in query_lower or 'penang' in query_lower:
        keywords['city'] = 'Georgetown'
    
    # Guest count
    if '2 people' in query_lower or '2 orang' in query_lower or '2 guests' in query_lower:
        filters['max_occupancy'] = 2
    elif '1 person' in query_lower or '1 orang' in query_lower or '1 guest' in query_lower:
        filters['max_occupancy'] = 1
    
    # Date calculations (simple)
    today = date.today()
    check_in = today + timedelta(days=1)  # Default tomorrow
    check_out = check_in + timedelta(days=1)  # 1 night
    
    return keywords, filters, check_in, check_out

def search_hotels_with_availability(keywords: Dict, filters: Dict, check_in: date, check_out: date) -> List[Dict]:
    """Search hotels with real availability checking using simple database queries."""
    try:
        print(f"   City filter: {keywords.get('city', 'Any')}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Simple hotel search query
            query = """
            SELECT DISTINCT h.property_id, h.hotel_name, h.star_rating,
                   h.city_name, h.state_name, h.distance_to_airport_km
            FROM hotels h
            WHERE h.is_active = 1 AND h.star_rating >= 3
            """
            params = []
            
            # Add city filter if specified
            if keywords.get('city'):
                query += " AND LOWER(h.city_name) LIKE LOWER(?)"
                params.append(f"%{keywords['city']}%")
            
            query += " ORDER BY h.star_rating DESC, h.distance_to_airport_km ASC LIMIT 20"
            
            cursor.execute(query, params)
            hotels = cursor.fetchall()
            
            print(f"Found {len(hotels)} hotels matching criteria")
            
            # Check availability for each hotel
            available_hotels = []
            for hotel in hotels:
                property_id, hotel_name, star_rating, city_name, state_name, distance = hotel
                
                print(f"\nChecking: {hotel_name}")
                
                # Get available rooms
                available_rooms = get_available_rooms_for_hotel(
                    property_id, check_in, check_out, filters.get('max_occupancy', 2)
                )
                
                if available_rooms:
                    print(f"   Found {len(available_rooms)} rooms matching filters")
                    
                    # Calculate pricing
                    min_price = min(room['price'] for room in available_rooms)
                    max_price = max(room['price'] for room in available_rooms)
                    
                    price_display = f"RM{min_price:.0f}/malam" if min_price == max_price else f"RM{min_price:.0f}-{max_price:.0f}/malam"
                    
                    available_hotels.append({
                        'property_id': property_id,
                        'hotel_name': hotel_name,
                        'star_rating': star_rating,
                        'city_name': city_name,
                        'state_name': state_name,
                        'distance_to_airport_km': distance,
                        'available_rooms': available_rooms,
                        'room_count': len(available_rooms),
                        'price_display': price_display,
                        'min_price': min_price,
                        'max_price': max_price
                    })
            
            print(f"\nFINAL RESULTS: {len(available_hotels)} hotels with availability")
            return available_hotels
        
    except Exception as e:
        print(f"AVAILABILITY SEARCH ERROR: {e}")
        return []

def get_available_rooms_for_hotel(property_id: str, check_in: date, check_out: date, max_occupancy: int = 2) -> List[Dict]:
    """
    Get available rooms for a specific hotel on given dates.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all room types for this hotel
            cursor.execute("""
                SELECT room_type_id, room_name, bed_type, view_type, 
                       max_occupancy, base_price_per_night, amenities, room_features
                FROM room_types 
                WHERE property_id = ? AND is_active = 1
                ORDER BY base_price_per_night ASC
            """, [property_id])
            
            room_types = cursor.fetchall()
            available_rooms = []
            
            for room_type in room_types:
                room_type_id, room_name, bed_type, view_type, occupancy, price, amenities, features = room_type
                
                # Check occupancy filter
                if occupancy < max_occupancy:
                    continue
                
                print(f"   Occupancy filter: >={max_occupancy}")
                
                # Check availability using simple function
                availability = check_room_availability_simple(property_id, room_type_id, check_in, check_out)
                
                if availability['available']:
                    available_rooms.append({
                        'room_type_id': room_type_id,
                        'room_name': room_name,
                        'bed_type': bed_type,
                        'view_type': view_type,
                        'max_occupancy': occupancy,
                        'price': price,
                        'available_rooms': availability['available_rooms'],
                        'amenities': amenities,
                        'features': features
                    })
            
            return available_rooms
            
    except Exception as e:
        print(f"ROOM AVAILABILITY ERROR: {e}")
        return []

def check_room_availability_simple(property_id: str, room_type_id: str, check_in: date, check_out: date) -> Dict:
    """Check room availability for dates - simple version."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total rooms
            cursor.execute("""
                SELECT total_rooms, base_price_per_night 
                FROM room_types 
                WHERE property_id = ? AND room_type_id = ? AND is_active = 1
            """, [property_id, room_type_id])
            
            room_info = cursor.fetchone()
            if not room_info:
                return {"available": False, "reason": "Room type not found"}
            
            total_rooms, base_price = room_info
            
            # Check confirmed bookings
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE property_id = ? AND room_type_id = ? 
                AND booking_status = 'CONFIRMED'
                AND ((check_in_date <= ? AND check_out_date > ?) 
                     OR (check_in_date < ? AND check_out_date >= ?))
            """, [property_id, room_type_id, check_in, check_in, check_out, check_out])
            
            booked_rooms = cursor.fetchone()[0]
            available_rooms = total_rooms - booked_rooms
            
            return {
                "available": available_rooms > 0,
                "available_rooms": max(0, available_rooms),
                "total_rooms": total_rooms,
                "price_per_night": base_price,
                "booked_rooms": booked_rooms
            }
            
    except Exception as e:
        print(f"AVAILABILITY CHECK ERROR: {e}")
        return {"available": False, "reason": f"Error: {str(e)}"}

@tool
def identify_hotel(hotel_name: str, include_photos: bool = True) -> str:
    """Identify and get comprehensive hotel details by name (READ-ONLY)."""
    
    try:
        print(f"🎯 IDENTIFY HOTEL: '{hotel_name}'")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Improve hotel name matching with common abbreviations
            search_patterns = [
                f"%{hotel_name}%",  # Original search
            ]
            
            # Handle common abbreviations
            normalized_name = hotel_name.lower()
            if ' kl' in normalized_name or normalized_name.endswith(' kl'):
                # Replace KL with Kuala Lumpur
                expanded_name = normalized_name.replace(' kl', ' kuala lumpur').replace('kl ', 'kuala lumpur ')
                search_patterns.append(f"%{expanded_name}%")
            elif 'kuala lumpur' in normalized_name:
                # Also try KL abbreviation
                abbreviated_name = normalized_name.replace('kuala lumpur', 'kl')
                search_patterns.append(f"%{abbreviated_name}%")
            
            # Try each search pattern
            hotel_result = None
            for pattern in search_patterns:
                cursor.execute("""
                SELECT property_id, hotel_name, hotel_brand, star_rating,
                       city_name, state_name, address, phone, email, website,
                       check_in_time, check_out_time, description
                FROM hotels 
                WHERE LOWER(hotel_name) LIKE LOWER(?) AND is_active = 1
                LIMIT 1
                """, [pattern])
                
                hotel_result = cursor.fetchone()
                if hotel_result:
                    print(f"✅ Found hotel using pattern: '{pattern}'")
                    break
            
            if not hotel_result:
                return f"HOTEL_ERROR:NOT_FOUND|{hotel_name}"
            
            property_id, name, brand, rating, city, state, address, phone, email, website, checkin, checkout, description = hotel_result
            
            response = f"### {name}\n\n"
            response += f"#### Overview\n"
            response += f"- **Rating:** {rating}⭐\n"
            response += f"- **Location:** {address}, {city}, {state}\n"
            
            if phone:
                response += f"- **Phone:** {phone}\n"
            if email:
                response += f"- **Email:** {email}\n"
            
            response += f"- **Check-in:** {checkin} | **Check-out:** {checkout}\n\n"
            
            if description:
                response += f"#### Description\n{description}\n\n"
            
            # Get room types
            cursor.execute("""
            SELECT room_name, bed_type, view_type, max_occupancy, base_price_per_night
            FROM room_types 
            WHERE property_id = ? AND is_active = 1
            ORDER BY base_price_per_night ASC
            LIMIT 5
            """, [property_id])
            
            rooms = cursor.fetchall()
            if rooms:
                response += f"#### Room Types ({len(rooms)} available)\n"
                for i, room in enumerate(rooms, 1):
                    room_name, bed_type, view_type, max_occupancy, price = room
                    response += f"{i}. **{room_name}** - RM{price:.0f}/night\n"
                    response += f"   - {bed_type} bed, {max_occupancy} guests"
                    if view_type:
                        response += f", {view_type} view"
                    response += "\n"
                response += "\n"
            
            response += f"#### Contact & Booking\n"
            response += f"Ready to book? I can help you check availability and pricing for specific dates.\n"
            
            return response
        
    except Exception as e:
        print(f"HOTEL IDENTIFICATION ERROR: {e}")
        return "HOTEL_ERROR:IDENTIFICATION"

@tool
def check_room_availability(city: str, check_in: str, check_out: str, room_preferences: str = "") -> str:
    """
    Check real-time room availability for specific dates (READ-ONLY).
    
    Args:
        city: City to search in
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        room_preferences: Optional room preferences (view, bed type, etc.)
        
    Returns:
        Available rooms with pricing for the specified dates
    """
    
    try:
        print(f"ELLA AVAILABILITY CHECK (READ-ONLY): {city} from {check_in} to {check_out}")
        
        # Parse dates
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            return "HOTEL_ERROR:INVALID_DATE"
        
        # 🔄 UPDATE SEARCH SESSION - So compare_with_otas uses correct dates
        try:
            from ..discovery_agent import update_search_context
            from core.guest_id import get_guest_id
            
            guest_id = get_guest_id()
            
            # Update session with new search criteria  
            update_result = update_search_context(
                guest_id=guest_id,
                city=city,
                check_in=check_in,
                check_out=check_out,
                guests=2,  # Default for availability check
                preferences=room_preferences or None
            )
            print(f"🔄 Session update: {update_result}")
            
        except Exception as session_error:
            print(f"⚠️ Session update failed: {session_error}")
            # Continue with availability check even if session update fails
        
        # Parse preferences
        filters = {}
        if room_preferences:
            pref_lower = room_preferences.lower()
            if 'sea' in pref_lower:
                filters['view_type'] = 'Sea'
            elif 'city' in pref_lower:
                filters['view_type'] = 'City'
            elif 'pool' in pref_lower:
                filters['view_type'] = 'Pool'
            
            if 'king' in pref_lower:
                filters['bed_type'] = 'King'
            elif 'queen' in pref_lower:
                filters['bed_type'] = 'Queen'
            elif 'twin' in pref_lower:
                filters['bed_type'] = 'Twin'
        
        # Search with availability
        keywords = {'city': city}
        results = search_hotels_with_availability(keywords, filters, check_in_date, check_out_date)
        
        if not results:
            return f"HOTEL_ERROR:NO_AVAILABILITY|{city}|{check_in}|{check_out}"
        
        # Format response
        nights = (check_out_date - check_in_date).days
        response = f"### Availability in {city} for {check_in_date.strftime('%B %d, %Y')} - {check_out_date.strftime('%B %d, %Y')}\n\n"
        response += f"Here are the options available for {nights} night(s):\n\n"
        
        for i, hotel in enumerate(results[:5], 1):  # Show top 5
            response += f"**{i}. {hotel['hotel_name']}** ({hotel['star_rating']}⭐)\n"
            response += f"📍 {hotel['city_name']}\n"
            response += f"💰 {hotel['price_display']}\n"
            response += f"🛏️ {hotel['room_count']} room types available\n"
            
            if hotel['distance_to_airport_km']:
                response += f"✈️ {hotel['distance_to_airport_km']}km from airport\n"
            
            response += "\n"
        
        response += f"Would you like detailed information about any of these hotels or help with booking?"
        
        return response
        
    except Exception as e:
        print(f"AVAILABILITY CHECK ERROR: {e}")
        return "HOTEL_ERROR:AVAILABILITY_CHECK"

# List of main hotel search tools - SEARCH & DISCOVERY ONLY
HOTEL_SEARCH_TOOLS = [
    search_hotels,
    identify_hotel,
    check_room_availability
]

TOOL_SUMMARY = f"""
AVAILABLE HOTEL SEARCH TOOLS ({len(HOTEL_SEARCH_TOOLS)} total):

SEARCH & DISCOVERY:
• search_hotels - Primary hotel search with session management
• identify_hotel - Comprehensive hotel information
• check_room_availability - Real-time availability checking

Note: Booking functionality is handled by dedicated booking tools in booking_agent.py
"""

print(TOOL_SUMMARY) 
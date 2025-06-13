"""
Voice Hotel Functions - Simplified Direct Database Implementation
Clean, fast functions without complex caching logic
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
import os
import requests
from typing import Dict, List, Optional, Any

def search_hotels(location=None, budget_max=None, guest_id=None, **kwargs):
    """Search hotels - Return up to 5 results"""
    start_time = time.time()
    guest_id = guest_id or "default"
    
    # Validate required parameters
    if not location:
        return "Nak cari hotel kat mana? Tolong sebut lokasi dulu."
    
    print(f"[VOICE] Hotel search for {location} (budget: {budget_max}) [Guest: {guest_id}]")
    
    try:
        # Get connection with optimizations
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Simple query - essential data for LLM
        query = """
            SELECT h.hotel_name, h.star_rating, h.city_name,
                   MIN(rt.base_price_per_night) as min_price
            FROM hotels h
            LEFT JOIN room_types rt ON h.property_id = rt.property_id
            WHERE h.is_active = 1 
            AND (h.city_name LIKE ? OR h.state_name LIKE ? OR h.hotel_name LIKE ?)
        """
        params = [f"%{location}%", f"%{location}%", f"%{location}%"]
        
        if budget_max:
            query += " AND rt.base_price_per_night <= ?"
            params.append(budget_max)
        
        # Limit to 5 results for optimal processing
        query += " GROUP BY h.property_id ORDER BY h.star_rating DESC, min_price ASC LIMIT 5"
        
        cursor.execute(query, params)
        hotels = cursor.fetchall()
        
        return_db_connection(conn)
        
        if not hotels:
            return f"Maaf, tiada hotel dijumpai di {location}. Cuba lokasi lain?"
        
        # Generate response
        if len(hotels) == 1:
            hotel = hotels[0]
            name, star_rating, city, price = hotel[0], hotel[1], hotel[2], hotel[3]
            price = price or 200
            stars = f"{star_rating} bintang " if star_rating else ""
            return f"Hotel {name} di {city}, {stars}RM{price} semalam. Nak tahu lanjut?"
        
        # Multiple hotels
        hotel_list = []
        max_hotels = min(len(hotels), 5)
        for h in hotels[:max_hotels]:
            name, star_rating, city, price = h[0], h[1] or 3, h[2], h[3] or 200
            hotel_list.append(f"{name} {star_rating}★ RM{price}")
        
        processing_time = (time.time() - start_time) * 1000
        print(f"[VOICE] Search completed: {len(hotels)} hotels ({processing_time:.1f}ms)")
        
        if len(hotels) <= 3:
            return f"Hotel yang saya jumpa: " + ", ".join(hotel_list) + ". Yang mana nak tahu lanjut?"
        else:
            return f"Antara pilihan: " + ", ".join(hotel_list) + f". Ada {len(hotels)} hotel lagi. Nak tahu yang mana?"
        
    except Exception as e:
        print(f"[VOICE] Search error: {e}")
        return f"Ada masalah cari hotel di {location}. Cuba lagi?"

def get_hotel_details(hotel_name=None, guest_id=None, **kwargs):
    """Get hotel details - Return essential information"""
    start_time = time.time()
    guest_id = guest_id or "default"
    
    # Validate required parameters
    if not hotel_name:
        return "Hotel mana nak tahu details? Tolong sebut nama hotel dulu."
    
    print(f"[VOICE] Getting hotel details for '{hotel_name}' [Guest: {guest_id}]")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hotel info query
        query = """
            SELECT h.hotel_name, h.star_rating, h.city_name, 
                   MIN(rt.base_price_per_night) as min_price,
                   COUNT(rt.room_type_id) as room_count
            FROM hotels h
            LEFT JOIN room_types rt ON h.property_id = rt.property_id
            WHERE h.is_active = 1 AND h.hotel_name LIKE ?
            GROUP BY h.property_id
            LIMIT 1
        """
        
        cursor.execute(query, [f"%{hotel_name}%"])
        result = cursor.fetchone()
        
        return_db_connection(conn)
        
        if not result:
            return f"Maaf, tak jumpa hotel '{hotel_name}'. Cuba sebut nama yang lain?"
        
        name, star_rating, city, min_price, room_count = result
        min_price = min_price or 200
        star_rating = star_rating or 3
        
        processing_time = (time.time() - start_time) * 1000
        print(f"[VOICE] Hotel details completed: {name} ({processing_time:.1f}ms)")
        
        # Generate response
        return f"{name}, {star_rating} bintang di {city}. Dari RM{min_price} semalam. Ada {room_count} jenis bilik. Nak tahu bilik apa tersedia?"
        
    except Exception as e:
        print(f"[VOICE] Hotel details error: {e}")
        return f"Ada masalah dapatkan info {hotel_name}. Cuba lagi?"

def get_room_types(hotel_name=None, guest_id=None, **kwargs):
    """Get room types - Return up to 5 room types"""
    start_time = time.time()
    guest_id = guest_id or "default"
    
    # Validate required parameters
    if not hotel_name:
        return "Hotel mana nak check jenis bilik? Tolong sebut nama hotel dulu."
    
    print(f"[VOICE] Getting room types for '{hotel_name}' [Guest: {guest_id}]")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Room types query - using correct column names from schema
        query = """
            SELECT rt.room_name, rt.base_price_per_night, rt.max_occupancy
            FROM room_types rt
            JOIN hotels h ON rt.property_id = h.property_id
            WHERE h.hotel_name LIKE ? AND rt.is_active = 1
            ORDER BY rt.base_price_per_night ASC
            LIMIT 5
        """
        
        cursor.execute(query, [f"%{hotel_name}%"])
        rooms = cursor.fetchall()
        
        return_db_connection(conn)
        
        if not rooms:
            return f"Maaf, tiada maklumat bilik untuk {hotel_name}"
        
        processing_time = (time.time() - start_time) * 1000
        print(f"[VOICE] Room types completed: {len(rooms)} rooms ({processing_time:.1f}ms)")
        
        # Generate response
        if len(rooms) == 1:
            name, price, occupancy = rooms[0]
            return f"Bilik {name}, RM{price} semalam, untuk {occupancy} orang. Nak check availability?"
        
        # Multiple rooms
        room_list = []
        for room in rooms:
            name, price, occupancy = room
            room_list.append(f"{name} RM{price}")
        
        return f"Jenis bilik: " + ", ".join(room_list) + ". Yang mana nak check availability?"
        
    except Exception as e:
        print(f"[VOICE] Room types error: {e}")
        return f"Ada masalah dapatkan info bilik {hotel_name}. Cuba lagi?"

def check_availability(hotel_name=None, check_date=None, date=None, **kwargs):
    """Check availability - Return essential availability info"""
    start_time = time.time()
    
    # Validate required parameters
    if not hotel_name:
        return "Hotel mana nak check availability? Tolong sebut nama hotel dulu."
    
    # Handle both 'date' and 'check_date' parameter names for flexibility
    actual_date = check_date or date
    
    print(f"[VOICE] Checking availability for '{hotel_name}' on {actual_date or 'today'}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Availability check - count available rooms
        query = """
            SELECT COUNT(rt.room_type_id) as available_rooms,
                   MIN(rt.base_price_per_night) as min_price
            FROM room_types rt
            JOIN hotels h ON rt.property_id = h.property_id
            WHERE h.hotel_name LIKE ? AND rt.is_active = 1
        """
        
        cursor.execute(query, [f"%{hotel_name}%"])
        result = cursor.fetchone()
        
        return_db_connection(conn)
        
        if not result or result[0] == 0:
            return f"Maaf, tiada bilik tersedia di {hotel_name}"
        
        available_rooms, min_price = result
        min_price = min_price or 200
        
        processing_time = (time.time() - start_time) * 1000
        print(f"[VOICE] Availability check completed: {available_rooms} rooms ({processing_time:.1f}ms)")
        
        # Generate response
        date_text = f" untuk {actual_date}" if actual_date else ""
        return f"Ada {available_rooms} jenis bilik tersedia di {hotel_name}{date_text}. Harga dari RM{min_price}. Nak book sekarang?"
        
    except Exception as e:
        print(f"[VOICE] Availability check error: {e}")
        return f"Ada masalah check availability {hotel_name}. Cuba lagi?"

def check_booking_status(booking_reference=None, guest_name=None, guest_email=None, guest_id=None, **kwargs):
    """Check booking status - Automatically uses phone number from caller ID for seamless validation"""
    start_time = time.time()
    guest_id = guest_id or "default"
    
    # Extract phone number from guest_id if it contains phone pattern
    phone_number = None
    if guest_id and guest_id != "default":
        # Extract digits from guest_id - phone numbers are embedded in guest_id
        phone_digits = ''.join(c for c in guest_id if c.isdigit())
        if len(phone_digits) >= 8:  # Minimum phone number length
            phone_number = phone_digits
    
    print(f"[VOICE] Checking booking status [Guest: {guest_id}]")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Priority 1: If booking reference provided, search by it
        if booking_reference:
            query = """
                SELECT b.booking_reference, b.guest_name, b.guest_email, 
                       h.hotel_name, rt.room_name,
                       b.check_in_date, b.check_out_date, b.nights, b.total_price,
                       b.booking_status, b.payment_status
                FROM bookings b
                JOIN hotels h ON b.property_id = h.property_id
                JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE b.booking_reference LIKE ?
                LIMIT 1
            """
            cursor.execute(query, [f"%{booking_reference}%"])
        
        # Priority 2: If phone number available from caller ID, search by it
        elif phone_number:
            # Create multiple phone formats to search for
            phone_formats = [
                phone_number,           # Raw digits: 60123456999
                f"+{phone_number}",     # With + prefix: +60123456999
                f"%{phone_number}%",    # Embedded in reference
                f"%+{phone_number}%"    # Embedded with + prefix
            ]
            
            query = """
                SELECT b.booking_reference, b.guest_name, b.guest_email, 
                       h.hotel_name, rt.room_name,
                       b.check_in_date, b.check_out_date, b.nights, b.total_price,
                       b.booking_status, b.payment_status
                FROM bookings b
                JOIN hotels h ON b.property_id = h.property_id
                JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE (b.booking_reference LIKE ? OR b.booking_reference LIKE ? OR 
                       b.guest_phone LIKE ? OR b.guest_phone = ?)
                AND b.booking_status != 'CANCELLED'
                ORDER BY b.booked_at DESC
                LIMIT 5
            """
            cursor.execute(query, [phone_formats[2], phone_formats[3], phone_formats[1], phone_formats[1]])
        
        # Priority 3: Search by guest details if provided
        elif guest_name or guest_email:
            query = """
                SELECT b.booking_reference, b.guest_name, b.guest_email, 
                       h.hotel_name, rt.room_name,
                       b.check_in_date, b.check_out_date, b.nights, b.total_price,
                       b.booking_status, b.payment_status
                FROM bookings b
                JOIN hotels h ON b.property_id = h.property_id
                JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE (b.guest_name LIKE ? OR b.guest_email LIKE ?)
                AND b.booking_status != 'CANCELLED'
                ORDER BY b.booked_at DESC
                LIMIT 3
            """
            search_name = f"%{guest_name}%" if guest_name else "%"
            search_email = f"%{guest_email}%" if guest_email else "%"
            cursor.execute(query, [search_name, search_email])
        
        # Priority 4: No search criteria provided
        else:
            return "Nak check booking mana? Sila sebut booking reference."
        
        results = cursor.fetchall()
        return_db_connection(conn)
        
        if not results:
            if booking_reference:
                return f"Maaf, tak jumpa booking dengan reference '{booking_reference}'. Cuba check reference tu betul ke?"
            elif phone_number:
                return f"Maaf, tak jumpa booking untuk nombor phone ini. Mungkin booking dibuat dengan nombor lain?"
            else:
                return f"Maaf, tak jumpa booking untuk {guest_name or guest_email}. Cuba bagi booking reference?"
        
        processing_time = (time.time() - start_time) * 1000
        print(f"[VOICE] Booking check completed: {len(results)} results ({processing_time:.1f}ms)")
        
        # Generate response based on number of results
        if len(results) == 1:
            # Single booking found - show full details
            booking = results[0]
            ref, name, email, hotel, room, checkin, checkout, nights, amount, status, payment = booking
            
            # Format status in Bahasa Malaysia
            status_bm = {
                'CONFIRMED': 'Disahkan',
                'CHECKED_IN': 'Dah check-in',
                'CHECKED_OUT': 'Dah check-out', 
                'CANCELLED': 'Dibatalkan',
                'PENDING': 'Menunggu'
            }.get(status, status)
            
            payment_bm = {
                'PAID': 'Dah bayar',
                'PENDING': 'Belum bayar',
                'REFUNDED': 'Dah refund'
            }.get(payment, payment)
            
            return f"Booking anda: {name} di {hotel}, bilik {room}. Check-in {checkin}, check-out {checkout} ({nights} malam). Status: {status_bm}, Bayaran: {payment_bm}. Total RM{amount}."
        
        else:
            # Multiple bookings found - show summary list
            booking_list = []
            for booking in results:
                ref, name, email, hotel, room, checkin, checkout, nights, amount, status, payment = booking
                status_bm = {
                    'CONFIRMED': 'Disahkan',
                    'CHECKED_IN': 'Check-in',
                    'CHECKED_OUT': 'Check-out', 
                    'CANCELLED': 'Batal'
                }.get(status, status)
                # Use hotel name and dates for easier identification
                booking_list.append(f"{hotel} ({checkin}, {status_bm})")
            
            return f"Jumpa {len(results)} booking untuk nombor ini: " + ", ".join(booking_list) + ". Yang mana nak tahu details lengkap?"
        
    except Exception as e:
        print(f"[VOICE] Booking check error: {e}")
        return f"Ada masalah check booking. Cuba lagi?"

# Database connection functions
def get_db_connection():
    """Get database connection with proper path handling."""
    # Check if we're in voice_hotel directory or parent directory
    if os.path.exists("ella.db"):
        db_path = "ella.db"
    elif os.path.exists("../ella.db"):
        db_path = "../ella.db"
    else:
        # Fallback to absolute path
        current_dir = os.path.dirname(__file__)
        db_path = os.path.join(current_dir, "..", "ella.db")
    
    return sqlite3.connect(db_path)

def return_db_connection(conn):
    """Close database connection."""
    conn.close()

def initiate_chat_handoff(scenario: str, context: str = "", guest_id: str = "default") -> str:
    """
    Initiate handoff from voice to chat when complex operations are needed
    Voice ELLA calls this when guest needs booking, payment, media, or modifications
    """
    start_time = time.time()
    
    print(f"[HANDOFF] Initiating chat transfer for {guest_id}: {scenario}")
    
    # Handoff message templates based on scenario
    handoff_messages = {
        "booking_new": """📞 **Voice Call Recap**: You called asking to make a hotel booking{context}

During our voice conversation, you expressed interest in making a reservation. Since booking involves secure payment processing and document generation, I've transferred you to our chat system where I can:

✅ **Complete your booking securely**
✅ **Process payment safely** 
✅ **Generate official confirmation PDF**
✅ **Show you hotel photos and room details**

Let me help you finalize this booking! Could you confirm the dates and number of guests for your reservation?""",
        
        "booking_modify": """📞 **Voice Call Recap**: You called asking to modify your existing booking{context}

During our conversation, you wanted to make changes to your reservation. Since booking modifications require secure verification and processing, I've transferred you here where I can:

✅ **Safely verify your booking details**
✅ **Process changes securely**
✅ **Update your reservation** 
✅ **Generate new confirmation documents**

Please provide your booking reference number so I can pull up your current reservation and make the changes you requested.""",
        
        "booking_cancel": """📞 **Voice Call Recap**: You called asking to cancel your booking{context}

During our voice conversation, you requested to cancel your reservation. Since cancellations involve policy review and potential refund processing, I've transferred you here where I can:

✅ **Securely verify your booking**
✅ **Review cancellation policies**
✅ **Process cancellation safely**
✅ **Handle refunds if applicable**

Please provide your booking reference number and I'll help you process this cancellation according to the terms.""",
        
        "payment_needed": """📞 **Voice Call Recap**: You called asking about payment for your booking{context}

During our conversation, you wanted to complete payment for your reservation. Since payment processing requires secure handling, I've transferred you to our chat system where I can:

✅ **Process payment securely with encryption**
✅ **Handle multiple payment methods**
✅ **Generate instant confirmation receipt**
✅ **Send booking documents immediately**

Which booking were you wanting to pay for? I'll set up secure payment for you right now.""",
        
        "media_request": """📞 **Voice Call Recap**: You called asking to see hotel photos and visuals{context}

During our voice conversation, you wanted to view hotel images, room photos, and facility pictures. Since visual content works much better in chat format, I've transferred you here where I can:

✅ **Show beautiful hotel photo galleries**
✅ **Display room types with images**
✅ **Present facility tours and amenities**
✅ **Provide virtual hotel walkthroughs**

Which hotel were you interested in seeing? I'll show you all the visual details right now!""",
        
        "complex_search": """📞 **Voice Call Recap**: You called asking for detailed hotel search and comparison{context}

During our conversation, you wanted comprehensive hotel options with detailed comparisons. Since complex search works better with visual displays, I've transferred you here where I can:

✅ **Show hotels with photos and details**
✅ **Compare prices across booking sites**
✅ **Display amenities and reviews**
✅ **Provide interactive maps and locations**

Let me search and show you the best options with all the visual details you need!""",
        
        "document_generation": """📞 **Voice Call Recap**: You called asking for booking documents and confirmations{context}

During our voice conversation, you requested your booking confirmation PDF and official documents. Since document generation and delivery works better in chat, I've transferred you here where I can:

✅ **Generate official booking confirmation PDF**
✅ **Create documents with QR codes**
✅ **Send vouchers and receipts instantly**
✅ **Provide downloadable travel documents**

What booking reference do you need documents for? I'll generate and send them to you immediately."""
    }
    
    # Get appropriate message or use generic fallback
    base_message = handoff_messages.get(scenario, f"""📞 **Voice Call Recap**: You called asking for assistance{context}

During our voice conversation, you requested help that requires our advanced chat features. Since your request involves capabilities beyond voice calls, I've transferred you to our chat system where I can:

✅ **Access secure payment processing**
✅ **Display photos and visual content**
✅ **Generate and send documents**
✅ **Provide detailed interactive features**

How can I help you complete what we discussed during your call?""")
    
    # Add context if provided
    formatted_message = base_message.format(context=f" {context}" if context else "")
    
    try:
        # Call the chat bridge API to initiate conversation
        bridge_url = "http://localhost:8000/bridge/initiate_chat"
        payload = {
            "guest_id": guest_id,
            "message": formatted_message,
            "sender": "assistant",
            "source": f"voice_handoff_{scenario}"
        }
        
        response = requests.post(bridge_url, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            processing_time = (time.time() - start_time) * 1000
            print(f"[HANDOFF] Successfully initiated chat for {guest_id} ({processing_time:.1f}ms)")
            
            return f"Perfect! Saya dah start chat conversation untuk anda. Buka WhatsApp atau chat interface, dan saya dah siap sedia dengan maklumat yang kita bincang tadi. Saya tunggu anda di sana! 💬"
        else:
            print(f"[HANDOFF] Bridge API error: {response.status_code} - {response.text}")
            return "Maaf, ada masalah technical sikit. Boleh cuba buka chat system secara manual? Saya akan ready untuk sambung conversation kita."
            
    except requests.exceptions.Timeout:
        print(f"[HANDOFF] Bridge API timeout")
        return "Chat system agak slow sikit sekarang. Boleh cuba buka chat interface dalam beberapa saat? Saya akan sambung conversation kita di sana."
        
    except Exception as e:
        print(f"[HANDOFF] Bridge error: {e}")
        return "Ada technical issue sikit dengan handoff. Boleh cuba buka chat system dan mention apa yang kita bincang tadi? Saya akan ingat conversation kita." 
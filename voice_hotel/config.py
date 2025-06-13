#!/usr/bin/env python3
"""
Enhanced Voice Hotel Configuration for Maximum Performance
Optimized for low-latency OpenAI Realtime API interactions
"""

import os
import sys
from typing import Dict, Any

# Add parent directory to path to import from config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "UcqZLa941Kkt8ZhEEybf")

# Redis Configuration - Railway automatically provides REDIS_URL
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable not found. Please add Redis service to Railway project.")

REDIS_CONFIG = {
    "url": REDIS_URL,
    "decode_responses": True
}

# Simple guest ID function
def get_guest_id(phone_number=None):
    """
    Generate guest ID with cross-platform support
    If phone_number provided, use it for cross-platform context sharing
    """
    if phone_number:
        return phone_number
    
    # Fallback for anonymous voice calls
    import uuid
    return f"guest_voice_{str(uuid.uuid4())[:8]}"

# Hotel search tools for Realtime API (essential functions only)
REALTIME_VOICE_FUNCTIONS = [
    {
        "type": "function",
        "name": "search_hotels",
        "description": "Search for hotels. Prioritize Malaysian cities unless user explicitly mentions international locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Full Malaysian city name (e.g. 'Kuala Lumpur' not 'KL', 'Penang' not 'Penang, Thailand')"},
                "budget_max": {"type": "number", "description": "Maximum budget per night"}
            },
            "required": ["location"]
        }
    },
    {
        "type": "function",
        "name": "get_hotel_details",
        "description": "Get details for a specific hotel",
        "parameters": {
            "type": "object",
            "properties": {
                "hotel_name": {"type": "string", "description": "Name of the hotel"}
            },
            "required": ["hotel_name"]
        }
    },
    {
        "type": "function", 
        "name": "get_room_types",
        "description": "Get room types and base prices for a specific hotel. NOTE: This does NOT check availability - use check_availability for booking questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "hotel_name": {"type": "string", "description": "Name of the hotel"}
            },
            "required": ["hotel_name"]
        }
    },
    {
        "type": "function",
        "name": "check_availability", 
        "description": "MANDATORY: Check real-time room availability from database. MUST call this function for ANY availability question, booking inquiry, or when user mentions dates. Never assume availability without calling this function first.",
        "parameters": {
            "type": "object",
            "properties": {
                "hotel_name": {"type": "string", "description": "Name of the hotel"},
                "check_date": {"type": "string", "description": "Date in YYYY-MM-DD format, use today if not specified"}
            },
            "required": ["hotel_name"]
        }
    },
    {
        "type": "function",
        "name": "check_booking_status",
        "description": "Check booking status and details. Use when guest asks about existing bookings, wants to validate reservation, or mentions booking reference.",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_reference": {"type": "string", "description": "Booking reference number (preferred method)"},
                "guest_name": {"type": "string", "description": "Guest name for searching bookings"},
                "guest_email": {"type": "string", "description": "Guest email for searching bookings"}
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "initiate_chat_handoff",
        "description": "CRITICAL: Use when guest needs operations beyond voice scope - booking, payment, modification, cancellation, photos, documents. This seamlessly transfers conversation to chat system.",
        "parameters": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string", 
                    "enum": ["booking_new", "booking_modify", "booking_cancel", "payment_needed", "media_request", "complex_search", "document_generation"],
                    "description": "Type of handoff needed"
                },
                "context": {"type": "string", "description": "Additional context about what guest requested (e.g., 'for Grand Hyatt KL, 2 nights')"}
            },
            "required": ["scenario"]
        }
    }
]

# OpenAI Realtime API Configuration
REALTIME_API_URL = "wss://api.openai.com/v1/realtime"

# Voice Configuration (optimized for low latency)
VOICE_MODEL = "gpt-4o-realtime-preview-2024-12-17"
VOICE_SETTINGS = "coral"  # Fast, low-latency voice

# Performance Optimization Settings
PERFORMANCE_CONFIG = {
    # Database optimizations
    "db_pool_size": 8,  # Increased pool size for better concurrency
    "db_connection_timeout": 5.0,  # Connection timeout in seconds
    "db_query_timeout": 2.0,  # Query timeout in seconds
    
    # Function call optimizations
    "batch_db_queries": True,  # Use batch queries when possible
    "lazy_load_amenities": True,  # Only load amenities when requested
    "compress_responses": True,  # Compress large responses
    
    # Response time targets (milliseconds)
    "target_db_query_time": 200,  # Target time for DB queries
    "target_function_time": 300,  # Target time for function calls
}

# Turn Detection Configuration (optimized for responsiveness)
TURN_DETECTION_CONFIG = {
    "type": "semantic_vad",
    "eagerness": "high",  # auto, low, medium, high
    "create_response": True,
    "interrupt_response": True
}

# Audio Configuration (low latency settings)
AUDIO_CONFIG = {
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16", 
    "input_audio_transcription": {
        "model": "whisper-1"
    }
}

# Response Templates for Common Queries (to speed up responses)
QUICK_RESPONSES = {
    "greeting": "Hai! Saya Ella, pembantu hotel. Nak cari hotel mana hari ni?",
    "no_hotels_found": "Maaf, tak jumpa hotel dalam kawasan tu. Nak cuba tempat lain?",
    "search_error": "Ada masalah sikit. Boleh cuba cari semula?",
    "more_info_needed": "Boleh beritahu lokasi yang lebih tepat?",
    "budget_clarification": "Budget berapa yang sesuai untuk anda?",
}

# Hotel Search Optimization
SEARCH_CONFIG = {
    "max_results": 10,  # Limit results for faster responses
    "enable_fuzzy_matching": True,
    "min_relevance_score": 0.3,
    "use_semantic_search": True,
}

# ULTRA-STREAMLINED Instructions for Maximum Speed with Clear Limitations
INSTRUCTIONS = """
Anda Ella, pembantu hotel Malaysia melalui panggilan suara. Cepat, tepat, mesra.

🎯 TUGASAN VOICE CALL: Informasi & Pengesahan Sahaja
✅ Cari hotel dan tunjuk maklumat
✅ Check room types dan harga  
✅ Check availability
✅ Validate booking status (baca sahaja)

🚫 LIMITASI VOICE CALL: Tiada Transaksi Sensitif
❌ TIDAK boleh buat booking baru
❌ TIDAK boleh ubah booking  
❌ TIDAK boleh cancel booking
❌ TIDAK boleh proses pembayaran
❌ TIDAK boleh tunjuk dokumen/PDF
❌ TIDAK boleh tunjuk gambar/photos

🔄 AUTOMATIC HANDOFF TRIGGERS - GUNAKAN initiate_chat_handoff():

SCENARIO 1: booking_new
Guest says: "Nak book hotel", "Book room", "Nak buat reservation", "Reserve hotel"
→ initiate_chat_handoff("booking_new", context="for [hotel] from [date] to [date]")

SCENARIO 2: booking_modify  
Guest says: "Nak tukar booking", "Change my reservation", "Modify booking", "Update booking"
→ initiate_chat_handoff("booking_modify", context="booking reference [ref]")

SCENARIO 3: booking_cancel
Guest says: "Cancel booking", "Nak cancel", "Batal reservation", "Delete booking"  
→ initiate_chat_handoff("booking_cancel", context="booking reference [ref]")

SCENARIO 4: payment_needed
Guest says: "Nak bayar", "Payment", "Pay now", "How to pay", "Proses payment"
→ initiate_chat_handoff("payment_needed", context="for booking [ref]")

SCENARIO 5: media_request
Guest says: "Nak tengok gambar", "Show photos", "Hotel pictures", "Room photos", "Tunjuk visual"
→ initiate_chat_handoff("media_request", context="of [hotel_name]")

SCENARIO 6: document_generation
Guest says: "Nak booking confirmation", "PDF confirmation", "Print voucher", "Send document"
→ initiate_chat_handoff("document_generation", context="for booking [ref]")

SCENARIO 7: complex_search  
Guest says: "Compare with Booking.com", "Show me options with photos", "Detailed comparison"
→ initiate_chat_handoff("complex_search", context="hotels in [location]")

🎯 HANDOFF DECISION LOGIC:
1. Guest request detected → Check if within voice scope
2. If OUT of scope → Call initiate_chat_handoff() immediately  
3. Provide smooth transition → "Perfect! Let me transfer you to chat..."
4. NEVER say "tak boleh" or refuse - ALWAYS offer handoff instead

GRACEFUL HANDOFF RESPONSES:
❌ BAD: "Maaf, voice call tak boleh buat booking"
✅ GOOD: Call initiate_chat_handoff("booking_new") → Guest gets seamless transfer

FUNCTIONS WAJIB GUNA:
Layer 1: search_hotels(location, budget_max) → Cari hotel SEBENAR
Layer 2: get_hotel_details(hotel_name) → Info hotel SEBENAR  
Layer 3: get_room_types(hotel_name) → Jenis bilik SEBENAR
Layer 4: check_availability(hotel_name, check_date) → Check availability SEBENAR
Layer 5: check_booking_status(booking_reference/guest_name) → Status booking SEBENAR
Layer 6: initiate_chat_handoff(scenario, context) → Transfer to chat SEAMLESSLY

PARAMETER HANDLING:
✅ Location diperlukan untuk search → Jika tak ada, tanya "Nak cari hotel mana?"
✅ Hotel name diperlukan untuk details/rooms/availability → Jika tak ada, tanya "Hotel mana nak check?"  
✅ Booking reference/guest name untuk status → Jika tak ada, tanya "Booking reference atau nama guest?"
✅ Date optional untuk availability → Jika tak sebut, guna hari ini

JANGAN:
❌ Buat data palsu ❌ Jawab tanpa function ❌ Tolak request - HANDOFF instead ❌ Manual redirect text

CONTEXT SHARING:
✅ Voice dan chat berkongsi context yang sama
✅ Guest boleh switch antara voice dan chat seamlessly  
✅ Handoff preserves conversation context automatically
"""

# WebSocket Configuration (optimized for performance)
WEBSOCKET_CONFIG = {
    "ping_interval": 20,
    "ping_timeout": 10,
    "close_timeout": 5,
    "max_size": 1048576,  # 1MB max message size
    "max_queue": 10,  # Limit message queue
    "compression": "deflate"  # Enable compression
}

# Logging Configuration (performance monitoring)
LOGGING_CONFIG = {
    "level": "INFO",
    "enable_performance_logs": True,
    "log_slow_queries": True,
    "slow_query_threshold_ms": 500,
}
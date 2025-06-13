"""
Voice Hotel Module - Simplified Voice Assistant for Hotel Search

This module provides:
- OpenAI Realtime API integration
- Hotel search functions with direct database queries
- WebSocket endpoints for real-time voice interaction
"""

from .server import app
from .functions import search_hotels, get_hotel_details, get_room_types, check_availability
from .config import REALTIME_VOICE_FUNCTIONS

__version__ = "2.0.0"
__all__ = [
    "app",
    "search_hotels", 
    "get_hotel_details", 
    "get_room_types", 
    "check_availability",
    "REALTIME_VOICE_FUNCTIONS"
] 
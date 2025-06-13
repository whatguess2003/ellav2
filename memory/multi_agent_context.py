#!/usr/bin/env python3
"""
🤝 MULTI-AGENT SHARED CONTEXT SYSTEM
Replaces limited search_session with comprehensive shared context for all agents

ARCHITECTURE:
• Each agent extracts relevance from guest input
• Each agent processes and updates the shared context
• Agents refer to shared context, not direct agent calls
• Chat assistant orchestrates agents with shared context

SHARED CONTEXT STRUCTURE:
{
    "guest_info": {...},           # Guest details and preferences
    "search_context": {...},       # Hotel search and discovery
    "room_context": {...},         # Room intelligence and details
    "hotel_context": {...},        # Hotel facilities and information  
    "service_context": {...},      # Services (breakfast, spa, etc.)
    "booking_context": {...},      # Booking details and pricing
    "conversation_state": {...}    # Current conversation state
}
"""

import redis
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import os

# Initialize Redis connection - Railway automatically provides REDIS_URL
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable not found. Please add Redis service to Railway project.")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class MultiAgentContext:
    """Shared context system for multi-agent coordination"""
    
    def __init__(self, guest_id: str):
        self.guest_id = guest_id
        self.context_key = f"multi_agent_context:{guest_id}"
    
    def get_context(self) -> Dict[str, Any]:
        """Get the complete multi-agent context"""
        context_data = redis_client.get(self.context_key)
        if context_data:
            return json.loads(context_data)
        return self._create_empty_context()
    
    def _create_empty_context(self) -> Dict[str, Any]:
        """Create empty context structure - LEAN & FOCUSED on inter-agent coordination"""
        return {
            "guest_info": {
                "guest_id": self.guest_id,
                "preferences": {},  # Only essential preferences that affect all agents
                "budget_range": None,  # Critical for all agents
                "special_requirements": []  # Accessibility, dietary, etc.
            },
            "search_context": {
                # ESSENTIAL SEARCH COORDINATION DATA ONLY
                "destination": None,  # City/location - needed by all agents
                "check_in": None,     # Critical for availability & pricing
                "check_out": None,    # Critical for availability & pricing  
                "adults": 1,          # Affects room selection & service pricing
                "children": 0,        # Affects room selection & service pricing
                "rooms": 1,           # Critical for booking calculations
                
                # SEARCH RESULTS (lean summary only)
                "hotels_found": 0,           # Count for other agents
                "selected_hotel": None,      # Hotel name - needed by all agents
                "selected_property_id": None, # Database ID - needed for booking
                "search_status": "pending",   # pending/completed/failed
                
                # NO: Full hotel list, detailed search criteria, search history
            },
            "room_context": {
                # ESSENTIAL ROOM COORDINATION DATA ONLY
                "room_type": None,           # Selected room type - needed for booking
                "room_type_id": None,        # Database ID - needed for booking
                "bed_configuration": None,   # Twin/King - affects service planning
                "max_occupancy": None,       # Important for service calculations
                
                # PRICING (essential for booking calculations)
                "base_price_per_night": None,  # Critical for booking agent
                "currency": "RM",               # For pricing coordination
                
                # NO: Full room amenities list, detailed features, room photos
            },
            "hotel_context": {
                # ESSENTIAL HOTEL COORDINATION DATA ONLY  
                "hotel_name": None,          # For booking confirmations
                "property_id": None,         # Database ID - critical for booking
                "location": {},              # Basic location for context
                
                # CRITICAL POLICIES (affect booking)
                "check_in_time": None,       # Affects booking instructions
                "check_out_time": None,      # Affects booking instructions
                "cancellation_policy": None, # Critical for booking decisions
                
                # NO: Full facilities list, detailed policies, hotel history
            },
            "service_context": {
                # ESSENTIAL SERVICE COORDINATION DATA ONLY
                "breakfast": {
                    "available": None,       # Boolean - affects booking options
                    "included": None,        # Boolean - affects pricing
                    "cost_per_person": None, # Critical for booking calculations
                    "policy": None           # Brief policy for booking
                },
                "services_requested": [],    # List of requested services
                "total_service_cost": 0,    # Critical for booking calculations
                
                # NO: Full service catalogs, detailed service descriptions
            },
            "booking_context": {
                # ESSENTIAL BOOKING COORDINATION DATA ONLY
                "booking_intent": False,     # Boolean - triggers booking workflow
                "booking_stage": "inquiry",  # inquiry/pricing/confirmation/booked
                
                # GUEST DETAILS (minimal for booking)
                "guest_name": None,          # Required for booking
                "guest_email": None,         # Required for confirmation
                "guest_phone": None,         # Required for booking
                
                # PRICING SUMMARY (coordination between agents)
                "room_cost": 0,              # From room context
                "service_cost": 0,           # From service context  
                "tax_amount": 0,             # Calculated
                "total_cost": 0,             # Final total for booking
                
                "booking_reference": None,   # Generated booking ID
                
                # NO: Detailed billing breakdown, payment methods, booking history
            },
            "conversation_state": {
                # ESSENTIAL CONVERSATION COORDINATION ONLY
                "current_intent": "general", # What guest is trying to do
                "active_agent": None,        # Which agent should handle next
                "completion_status": {},     # Which workflows are complete
                "last_updated": time.time()  # For staleness checking
                
                # NO: Full conversation history, detailed turn tracking
            }
        }
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update specific parts of the context"""
        current_context = self.get_context()
        
        # Deep merge updates
        for section, section_data in updates.items():
            if section in current_context:
                if isinstance(section_data, dict):
                    current_context[section].update(section_data)
                else:
                    current_context[section] = section_data
        
        # Update timestamp
        current_context["conversation_state"]["last_updated"] = time.time()
        
        # Store updated context
        redis_client.set(self.context_key, json.dumps(current_context))
        redis_client.expire(self.context_key, 3600)  # 1 hour TTL
        
        print(f"🤝 CONTEXT UPDATED: {self.guest_id} → {list(updates.keys())}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get specific section of the context"""
        context = self.get_context()
        return context.get(section, {})
    
    def update_section(self, section: str, data: Dict[str, Any]) -> None:
        """Update specific section of the context"""
        self.update_context({section: data})
    
    def clear_context(self) -> None:
        """Clear the entire context (start fresh)"""
        redis_client.delete(self.context_key)
        print(f"🗑️ CONTEXT CLEARED: {self.guest_id}")
    
    def is_stale(self, max_age_hours: int = 2) -> bool:
        """Check if context is stale and should be cleared"""
        context = self.get_context()
        last_updated = context["conversation_state"]["last_updated"]
        age_hours = (time.time() - last_updated) / 3600
        return age_hours > max_age_hours

# AGENT-SPECIFIC CONTEXT MANAGERS

class DiscoveryAgentContext:
    """Discovery Agent context manager"""
    
    def __init__(self, guest_id: str):
        self.context = MultiAgentContext(guest_id)
    
    def extract_search_criteria(self, user_input: str) -> Dict[str, Any]:
        """Extract search criteria from user input"""
        # Basic extraction logic - in real implementation, use NLP
        search_criteria = {}
        
        # Extract location
        cities = ["kuala lumpur", "kl", "penang", "johor bahru", "melaka"]
        for city in cities:
            if city in user_input.lower():
                search_criteria["destination"] = city.title()
                break
        
        # Extract dates (basic pattern matching)
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'tomorrow|next week|this weekend'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, user_input)
            if matches:
                search_criteria["dates_mentioned"] = matches
                break
        
        # Extract guest count
        guest_matches = re.findall(r'(\d+)\s*(?:guest|person|people|adult)', user_input.lower())
        if guest_matches:
            search_criteria["adults"] = int(guest_matches[0])
        
        return search_criteria
    
    def update_search_results(self, hotels: List[Dict], search_criteria: Dict) -> None:
        """Update context with search results"""
        search_update = {
            "search_criteria": search_criteria,
            "available_hotels": hotels,
            "last_search": time.time()
        }
        
        # Update destination if found
        if search_criteria.get("destination"):
            search_update["destination"] = search_criteria["destination"]
        
        # Update guest count if found
        if search_criteria.get("adults"):
            search_update["adults"] = search_criteria["adults"]
        
        self.context.update_section("search_context", search_update)
    
    def get_search_context(self) -> Dict[str, Any]:
        """Get current search context"""
        return self.context.get_section("search_context")

class RoomIntelligenceContext:
    """Room Intelligence Agent context manager"""
    
    def __init__(self, guest_id: str):
        self.context = MultiAgentContext(guest_id)
    
    def extract_room_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract room preferences from user input"""
        preferences = {}
        
        # Room types
        room_types = ["deluxe", "superior", "suite", "standard", "executive"]
        for room_type in room_types:
            if room_type in user_input.lower():
                preferences["room_type"] = room_type.title()
                break
        
        # Bed configuration
        if "king" in user_input.lower():
            preferences["bed_configuration"] = "King Bed"
        elif "twin" in user_input.lower():
            preferences["bed_configuration"] = "Twin Beds"
        
        # View preferences
        views = ["city view", "pool view", "sea view", "garden view"]
        for view in views:
            if view in user_input.lower():
                preferences["view_preference"] = view.title()
                break
        
        return preferences
    
    def update_room_details(self, room_info: Dict) -> None:
        """Update context with room details"""
        self.context.update_section("room_context", room_info)
    
    def get_room_context(self) -> Dict[str, Any]:
        """Get current room context"""
        return self.context.get_section("room_context")

class ServiceAgentContext:
    """Service Agent context manager"""
    
    def __init__(self, guest_id: str):
        self.context = MultiAgentContext(guest_id)
    
    def extract_service_requests(self, user_input: str) -> Dict[str, Any]:
        """Extract service requests from user input"""
        services = {}
        
        # Breakfast
        if "breakfast" in user_input.lower():
            services["breakfast_requested"] = True
        
        # Spa
        if "spa" in user_input.lower():
            services["spa_requested"] = True
        
        # Room service
        if "room service" in user_input.lower():
            services["room_service_requested"] = True
        
        return services
    
    def update_service_info(self, service_data: Dict) -> None:
        """Update context with service information"""
        self.context.update_section("service_context", service_data)
    
    def get_service_context(self) -> Dict[str, Any]:
        """Get current service context"""
        return self.context.get_section("service_context")

class BookingAgentContext:
    """Booking Agent context manager"""
    
    def __init__(self, guest_id: str):
        self.context = MultiAgentContext(guest_id)
    
    def extract_booking_intent(self, user_input: str) -> Dict[str, Any]:
        """Extract booking intent from user input"""
        booking_info = {}
        
        # Booking keywords
        booking_keywords = ["book", "reserve", "confirm", "make a booking"]
        has_booking_intent = any(keyword in user_input.lower() for keyword in booking_keywords)
        
        if has_booking_intent:
            booking_info["booking_intent"] = True
            booking_info["booking_stage"] = "pricing"
        
        # Extract guest details
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\b\d{10,12}\b'
        
        emails = re.findall(email_pattern, user_input)
        phones = re.findall(phone_pattern, user_input)
        
        if emails:
            booking_info["guest_details"] = {"email": emails[0]}
        if phones:
            booking_info.setdefault("guest_details", {})["phone"] = phones[0]
        
        return booking_info
    
    def calculate_total_pricing(self) -> Dict[str, Any]:
        """Calculate total pricing from all context sources"""
        context = self.context.get_context()
        
        room_pricing = context["room_context"].get("pricing", {})
        service_pricing = context["service_context"]
        
        # Calculate room cost
        base_price = room_pricing.get("base_price_per_night", 0)
        nights = room_pricing.get("nights", 1)
        rooms = context["search_context"].get("rooms", 1)
        
        room_total = base_price * nights * rooms
        
        # Calculate service costs
        service_total = 0
        breakfast_cost = service_pricing.get("breakfast", {}).get("cost", 0)
        if breakfast_cost:
            service_total += breakfast_cost * nights
        
        # Calculate total
        subtotal = room_total + service_total
        tax_rate = 0.06  # 6% tax
        tax_amount = subtotal * tax_rate
        grand_total = subtotal + tax_amount
        
        total_pricing = {
            "room_cost": room_total,
            "service_cost": service_total,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "grand_total": grand_total
        }
        
        return total_pricing
    
    def update_booking_context(self, booking_data: Dict) -> None:
        """Update context with booking information"""
        self.context.update_section("booking_context", booking_data)
    
    def get_booking_context(self) -> Dict[str, Any]:
        """Get current booking context"""
        return self.context.get_section("booking_context")

# UTILITY FUNCTIONS FOR CHAT ASSISTANT

def get_shared_context(guest_id: str) -> MultiAgentContext:
    """Get shared context for guest (main entry point for chat assistant)"""
    return MultiAgentContext(guest_id)

def extract_all_intents(user_input: str, guest_id: str) -> Dict[str, Any]:
    """Extract all intents from user input across all agents"""
    
    # Initialize agent contexts
    discovery_ctx = DiscoveryAgentContext(guest_id)
    room_ctx = RoomIntelligenceContext(guest_id)
    service_ctx = ServiceAgentContext(guest_id)
    booking_ctx = BookingAgentContext(guest_id)
    
    # Extract intents from all agents
    intents = {
        "search_criteria": discovery_ctx.extract_search_criteria(user_input),
        "room_preferences": room_ctx.extract_room_preferences(user_input),
        "service_requests": service_ctx.extract_service_requests(user_input),
        "booking_intent": booking_ctx.extract_booking_intent(user_input)
    }
    
    return intents

def determine_active_agent(intents: Dict[str, Any]) -> str:
    """Determine which agent should be active based on extracted intents"""
    
    # Priority order for agent activation
    if intents["booking_intent"].get("booking_intent"):
        return "booking_agent"
    elif intents["service_requests"]:
        return "service_agent"
    elif intents["room_preferences"]:
        return "room_intelligence_agent"
    elif intents["search_criteria"]:
        return "discovery_agent"
    else:
        return "discovery_agent"  # Default

def cleanup_stale_contexts():
    """Cleanup stale multi-agent contexts"""
    pattern = "multi_agent_context:*"
    cleaned = 0
    
    try:
        for key in redis_client.scan_iter(match=pattern):
            guest_id = key.replace("multi_agent_context:", "")
            context = MultiAgentContext(guest_id)
            
            if context.is_stale():
                context.clear_context()
                cleaned += 1
                print(f"🧹 CLEANUP: Removed stale context for {guest_id}")
    except Exception as e:
        print(f"❌ Context cleanup error: {e}")
    
    if cleaned > 0:
        print(f"🧹 CONTEXT CLEANUP: Removed {cleaned} stale contexts")
    
    return cleaned

print("🤝 Multi-Agent Shared Context System initialized")
print("✅ Agents can now coordinate through shared context instead of direct calls")
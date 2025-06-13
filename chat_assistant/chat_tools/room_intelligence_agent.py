#!/usr/bin/env python3
"""
🛏️ ROOM INTELLIGENCE AGENT - Room Expert
Following agent_workflow.md architecture: Tell guests everything about rooms

WORKFLOW STEPS:
1. 🎯 Identify which room guest is asking about
2. 📝 Get room details and amenities
3. 🍳 Check breakfast and meal policies  
4. 💰 Show pricing options
5. 📊 Compare with other rooms if needed

AGENT BOUNDARIES:
✅ Room-specific questions and amenities
✅ Room pricing and comparisons
❌ Hotel-wide questions → Route to Hotel Intelligence Agent
❌ Service questions (breakfast, spa, dining) → Route to Service Agent
❌ Booking operations → Route to Booking Agent
❌ Hotel discovery → Route to Discovery Agent
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, date, timedelta

import os

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_CONFIG = {
    "chat_assistant": "gpt-4o-mini",
    "function_execution": "gpt-4o",
    "prediction": "gpt-4o",
    "ultra_fast": "gpt-4o"
}
from core.guest_id import get_guest_id
import sqlite3
import os

def get_db_connection(db_path: str = "ella.db"):
    """Get database connection using context manager"""
    return sqlite3.connect(db_path)

# ROOM INTELLIGENCE AGENT ARCHITECTURE - Following agent_workflow.md

@tool
def identify_room_type(hotel_name: str, room_query: str) -> str:
    """
    ROOM INTELLIGENCE TOOL 1: Find specific room type by hotel and description
    
    Identifies the exact room the guest is asking about based on hotel name and room description.
    
    Args:
        hotel_name: Hotel name to search in
        room_query: Room description (e.g., "deluxe king", "suite with balcony", "twin room")
        
    Returns:
        JSON string with identified room details
    """
    print(f"🎯 ROOM IDENTIFICATION: '{room_query}' at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Find rooms matching the description
            query = """
                SELECT h.hotel_name, rt.room_name, rt.bed_type, rt.view_type, 
                       rt.base_price_per_night, rt.max_occupancy, rt.room_type_id
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            # Add room search criteria
            room_lower = room_query.lower()
            room_conditions = []
            
            # Room type keywords
            if any(keyword in room_lower for keyword in ['deluxe', 'suite', 'junior', 'executive', 'standard', 'premium']):
                room_conditions.append("LOWER(rt.room_name) LIKE LOWER(?)")
                params.append(f"%{room_query}%")
            
            # Bed type keywords
            if any(keyword in room_lower for keyword in ['king', 'queen', 'twin', 'double']):
                room_conditions.append("LOWER(rt.bed_type) LIKE LOWER(?)")
                params.append(f"%{room_query}%")
            
            # View type keywords
            if any(keyword in room_lower for keyword in ['sea', 'city', 'garden', 'pool', 'mountain', 'river']):
                room_conditions.append("LOWER(rt.view_type) LIKE LOWER(?)")
                params.append(f"%{room_query}%")
            
            # If no specific conditions, search in room name
            if not room_conditions:
                room_conditions.append("LOWER(rt.room_name) LIKE LOWER(?)")
                params.append(f"%{room_query}%")
            
            query += " AND (" + " OR ".join(room_conditions) + ")"
            query += " ORDER BY rt.base_price_per_night ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No rooms found matching '{room_query}' at {hotel_name}"
                })
            
            # Format results
            rooms = []
            for hotel, room_name, bed_type, view_type, price, occupancy, room_id in results:
                rooms.append({
                    "hotel": hotel,
                    "room_name": room_name,
                    "bed_type": bed_type,
                    "view_type": view_type,
                    "price": price,
                    "max_occupancy": occupancy,
                    "room_type_id": room_id
                })
            
            return json.dumps({
                "status": "found",
                "rooms": rooms,
                "count": len(rooms)
            })
            
    except Exception as e:
        print(f"❌ Room identification error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_room_amenities(hotel_name: str, room_name: str = None) -> str:
    """
    ROOM INTELLIGENCE TOOL 2: Get all amenities, features, bed type, view type
    
    Retrieves comprehensive room information including amenities and features.
    
    Args:
        hotel_name: Hotel name
        room_name: Specific room name (optional, if not provided gets all rooms)
        
    Returns:
        JSON string with detailed room amenities and features
    """
    print(f"📝 ROOM AMENITIES: {room_name or 'all rooms'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, rt.room_name, rt.amenities, rt.room_features, 
                       rt.bed_type, rt.view_type, rt.base_price_per_night, 
                       rt.max_occupancy, rt.breakfast_policy
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            if room_name:
                query += " AND LOWER(rt.room_name) LIKE LOWER(?)"
                params.append(f"%{room_name}%")
            
            query += " ORDER BY rt.base_price_per_night ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No room amenities found for {room_name or 'rooms'} at {hotel_name}"
                })
            
            # Format results
            rooms = []
            for hotel, room, amenities, features, bed, view, price, occupancy, breakfast in results:
                room_info = {
                    "hotel": hotel,
                    "room_name": room,
                    "amenities": json.loads(amenities) if amenities else [],
                    "features": json.loads(features) if features else [],
                    "bed_type": bed,
                    "view_type": view,
                    "price": price,
                    "max_occupancy": occupancy,
                    "breakfast_policy": breakfast or "NO"
                }
                rooms.append(room_info)
            
            return json.dumps({
                "status": "found",
                "rooms": rooms,
                "count": len(rooms)
            })
            
    except Exception as e:
        print(f"❌ Room amenities error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool  
def check_breakfast_policy(hotel_name: str, room_name: str = None) -> str:
    """
    ROOM INTELLIGENCE TOOL 3: Check breakfast inclusion policy
    
    Checks breakfast policy for specific room or all rooms at hotel.
    
    Args:
        hotel_name: Hotel name
        room_name: Specific room name (optional)
        
    Returns:
        JSON string with breakfast policy details
    """
    print(f"🍳 BREAKFAST POLICY: {room_name or 'all rooms'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, rt.room_name, rt.breakfast_policy, rt.base_price_per_night
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            if room_name:
                query += " AND LOWER(rt.room_name) LIKE LOWER(?)"
                params.append(f"%{room_name}%")
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No breakfast policy found for {room_name or 'rooms'} at {hotel_name}"
                })
            
            # Format results
            policies = []
            for hotel, room, policy, price in results:
                policy_info = {
                    "hotel": hotel,
                    "room_name": room,
                    "breakfast_policy": policy or "NO",
                    "price": price,
                    "interpretation": {
                        "YES": "Breakfast is included at no extra charge",
                        "NO": "Breakfast is not available or not included",
                        "RM25perpax": "Breakfast available for RM25 per person per night",
                        "RM30perpax": "Breakfast available for RM30 per person per night",
                        "RM50perpax": "Breakfast available for RM50 per person per night"
                    }.get(policy or "NO", "Breakfast policy not specified")
                }
                policies.append(policy_info)
            
            return json.dumps({
                "status": "found",
                "policies": policies,
                "count": len(policies)
            })
            
    except Exception as e:
        print(f"❌ Breakfast policy error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_room_pricing(hotel_name: str, room_name: str = None) -> str:
    """
    ROOM INTELLIGENCE TOOL 4: Get room price per night
    
    Retrieves pricing information for specific room or all rooms.
    
    Args:
        hotel_name: Hotel name
        room_name: Specific room name (optional)
        
    Returns:
        JSON string with room pricing details
    """
    print(f"💰 ROOM PRICING: {room_name or 'all rooms'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, rt.room_name, rt.base_price_per_night, 
                       rt.bed_type, rt.view_type, rt.max_occupancy, rt.breakfast_policy
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            if room_name:
                query += " AND LOWER(rt.room_name) LIKE LOWER(?)"
                params.append(f"%{room_name}%")
            
            query += " ORDER BY rt.base_price_per_night ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No pricing found for {room_name or 'rooms'} at {hotel_name}"
                })
            
            # Format results
            pricing = []
            for hotel, room, price, bed, view, occupancy, breakfast in results:
                room_pricing = {
                    "hotel": hotel,
                    "room_name": room,
                    "price_per_night": price,
                    "bed_type": bed,
                    "view_type": view,
                    "max_occupancy": occupancy,
                    "breakfast_included": breakfast == "YES",
                    "breakfast_policy": breakfast or "NO"
                }
                pricing.append(room_pricing)
            
            return json.dumps({
                "status": "found",
                "pricing": pricing,
                "count": len(pricing)
            })
            
    except Exception as e:
        print(f"❌ Room pricing error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def compare_room_options(hotel_name: str, room_list: str = None) -> str:
    """
    ROOM INTELLIGENCE TOOL 5: Compare multiple rooms side by side
    
    Provides detailed comparison of room options at a hotel.
    
    Args:
        hotel_name: Hotel name
        room_list: Comma-separated list of room names to compare (optional, compares all if not provided)
        
    Returns:
        Formatted comparison of rooms with recommendations
    """
    print(f"📊 ROOM COMPARISON: {room_list or 'all rooms'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, rt.room_name, rt.base_price_per_night, rt.amenities, 
                       rt.room_features, rt.bed_type, rt.view_type, rt.max_occupancy, 
                       rt.breakfast_policy
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            if room_list:
                room_names = [name.strip() for name in room_list.split(',')]
                room_conditions = " OR ".join(["LOWER(rt.room_name) LIKE LOWER(?)" for _ in room_names])
                query += f" AND ({room_conditions})"
                params.extend([f"%{name}%" for name in room_names])
            
            query += " ORDER BY rt.base_price_per_night ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return "❌ **No Rooms Found**\n\nNo rooms found for comparison at this hotel."
            
            if len(results) == 1:
                return "ℹ️ **Single Room Found**\n\nOnly one room type available. Use 'get room amenities' for detailed information."
            
            # Format comparison
            response = f"📊 **Room Comparison at {hotel_name}**\n\n"
            
            for i, (hotel, room, price, amenities, features, bed, view, occupancy, breakfast) in enumerate(results, 1):
                response += f"**{i}. {room}** - RM{price}/night\n"
                response += f"🛏️ {bed} bed • {view} view • Max {occupancy} guests\n"
                
                # Breakfast policy
                if breakfast == "YES":
                    response += f"🍳 Breakfast included\n"
                elif breakfast and breakfast.startswith("RM"):
                    response += f"🍳 Breakfast available ({breakfast.replace('perpax', ' per person')})\n"
                else:
                    response += f"🍳 No breakfast\n"
                
                # Amenities
                if amenities:
                    amenity_list = json.loads(amenities)
                    response += f"✨ {', '.join(amenity_list[:4])}"
                    if len(amenity_list) > 4:
                        response += f" +{len(amenity_list)-4} more"
                    response += "\n"
                
                # Features
                if features:
                    feature_list = json.loads(features)
                    response += f"🏠 {', '.join(feature_list[:3])}"
                    if len(feature_list) > 3:
                        response += f" +{len(feature_list)-3} more"
                    response += "\n"
                
                response += "\n"
            
            # Add recommendations
            response += "💡 **Recommendations:**\n"
            cheapest = min(results, key=lambda x: x[2])
            most_expensive = max(results, key=lambda x: x[2])
            
            response += f"• **Best Value**: {cheapest[1]} (RM{cheapest[2]}/night)\n"
            if cheapest != most_expensive:
                response += f"• **Premium Option**: {most_expensive[1]} (RM{most_expensive[2]}/night)\n"
            
            # Breakfast recommendations
            breakfast_included = [r for r in results if r[8] == "YES"]
            if breakfast_included:
                response += f"• **Breakfast Included**: {', '.join([r[1] for r in breakfast_included])}\n"
            
            # Next steps (following agent_workflow.md)
            response += "\n💡 **Next Steps:**\n"
            response += "• Ask about hotel facilities: 'What facilities does the hotel have?'\n"  
            response += "• Ready to book: 'Book [room name]'\n"
            response += "• Compare prices: 'Compare [hotel name] prices'\n"
            
            return response
            
    except Exception as e:
        print(f"❌ Room comparison error: {e}")
        return "❌ Unable to compare rooms. Please try again."


class RoomIntelligenceAgent:
    """Room Intelligence Agent - Room Expert following agent_workflow.md"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY, 
            model=MODEL_CONFIG["function_execution"], 
            temperature=0.1
        )
    
    def process(self, user_input: str, conversation_context: str = "") -> str:
        """Process room intelligence request following the 5-step workflow"""
        
        # ROOM INTELLIGENCE AGENT SYSTEM PROMPT (from agent_workflow.md)
        system_prompt = """You are the Room Intelligence Agent. Your job: Answer ALL room questions.

WORKFLOW (Always follow this order):
1. IDENTIFY: Which specific room are they asking about?
2. DETAILS: Get room amenities and features
3. BREAKFAST: Always check breakfast policy  
4. PRICING: Show pricing for the room
5. COMPARE: If multiple rooms, compare options

YOUR TOOLS:
• identify_room_type - Find specific room by name/hotel
• get_room_amenities - All room features and amenities
• check_breakfast_policy - Breakfast inclusion (YES/NO/RMXXperpax)
• get_room_pricing - Price per night 
• compare_room_options - Side-by-side room comparison

BREAKFAST POLICY RESPONSES:
• "YES" → "Breakfast is included at no extra charge"
• "NO" → "This hotel doesn't offer breakfast or breakfast not included"  
• "RM25perpax" → "Breakfast available for RM25 per person per night"
• "RM30perpax" → "Breakfast available for RM30 per person per night"
• "RM50perpax" → "Breakfast available for RM50 per person per night"

ALWAYS:
✅ Include breakfast policy in room descriptions
✅ Mention bed type and view type
✅ Show room price clearly
✅ Ask if they want to book or see other rooms

NEVER:
❌ Answer hotel-wide questions (send to Hotel Agent)
❌ Handle bookings (send to Booking Agent)
❌ Recommend hotels (send to Discovery Agent)"""
        
        try:
            # Execute the Room Intelligence Agent workflow using tools
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Guest request: {user_input}\nContext: {conversation_context}"}
            ]
            
            # Bind tools to the LLM
            tools = [
                identify_room_type,
                get_room_amenities, 
                check_breakfast_policy,
                get_room_pricing,
                compare_room_options
            ]
            
            llm_with_tools = self.llm.bind_tools(tools)
            
            # Initial response - should start workflow
            response = llm_with_tools.invoke(messages)
            
            # Handle tool calls if any
            if response.tool_calls:
                # Process tool calls and continue conversation
                messages.append(response)
                
                for tool_call in response.tool_calls:
                    # Execute the tool call
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    if tool_name == "identify_room_type":
                        tool_result = identify_room_type.invoke(tool_args)
                    elif tool_name == "get_room_amenities":
                        tool_result = get_room_amenities.invoke(tool_args)
                    elif tool_name == "check_breakfast_policy":
                        tool_result = check_breakfast_policy.invoke(tool_args)
                    elif tool_name == "get_room_pricing":
                        tool_result = get_room_pricing.invoke(tool_args)
                    elif tool_name == "compare_room_options":
                        tool_result = compare_room_options.invoke(tool_args)
                    else:
                        tool_result = f"Unknown tool: {tool_name}"
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call["id"]
                    })
                
                # Get final response after tool execution
                final_response = llm_with_tools.invoke(messages)
                return final_response.content
            else:
                return response.content
                
        except Exception as e:
            print(f"❌ Room Intelligence Agent error: {e}")
            
            # Fallback to direct workflow execution
            return self._direct_workflow(user_input, conversation_context)
    
    def _direct_workflow(self, user_input: str, conversation_context: str = "") -> str:
        """Direct workflow execution as fallback"""
        try:
            # Try to extract hotel name from input or context
            hotel_name = self._extract_hotel_name(user_input, conversation_context)
            
            if not hotel_name:
                return "❌ I need to know which hotel you're asking about. Please specify the hotel name."
            
            # Check if this is a breakfast query
            if any(keyword in user_input.lower() for keyword in ['breakfast', 'sarapan', 'makan pagi']):
                result = check_breakfast_policy.invoke({
                    'hotel_name': hotel_name
                })
                data = json.loads(result)
                
                if data['status'] == 'found' and data['policies']:
                    policy = data['policies'][0]
                    return policy['interpretation']
                else:
                    return f"❌ No breakfast information available for {hotel_name}"
            
            # Check if this is a pricing query
            elif any(keyword in user_input.lower() for keyword in ['price', 'cost', 'harga', 'berapa']):
                result = get_room_pricing.invoke({
                    'hotel_name': hotel_name
                })
                data = json.loads(result)
                
                if data['status'] == 'found' and data['pricing']:
                    response = f"💰 **Room Pricing at {hotel_name}**\n\n"
                    for room in data['pricing']:
                        response += f"• **{room['room_name']}**: RM{room['price_per_night']}/night"
                        if room['breakfast_included']:
                            response += " (breakfast included)"
                        response += "\n"
                    return response
                else:
                    return f"❌ No pricing information available for {hotel_name}"
            
            # Default: Get room amenities
            else:
                room_name = self._extract_room_name(user_input)
                result = get_room_amenities.invoke({
                    'hotel_name': hotel_name,
                    'room_name': room_name
                })
                data = json.loads(result)
                
                if data['status'] == 'found' and data['rooms']:
                    room = data['rooms'][0]
                    response = f"🛏️ **{room['room_name']} at {hotel_name}**\n\n"
                    response += f"🛏️ {room['bed_type']} bed • {room['view_type']} view\n"
                    response += f"💰 RM{room['price']}/night • Max {room['max_occupancy']} guests\n"
                    
                    # Breakfast policy
                    if room['breakfast_policy'] == "YES":
                        response += f"🍳 Breakfast included\n"
                    elif room['breakfast_policy'].startswith("RM"):
                        response += f"🍳 Breakfast available ({room['breakfast_policy'].replace('perpax', ' per person')})\n"
                    
                    # Amenities
                    if room['amenities']:
                        response += f"✨ Amenities: {', '.join(room['amenities'])}\n"
                    
                    # Features  
                    if room['features']:
                        response += f"🏠 Features: {', '.join(room['features'])}\n"
                    
                    return response
                else:
                    return f"❌ No room information found for {hotel_name}"
            
        except Exception as e:
            print(f"❌ Direct workflow failed: {e}")
            return "❌ Sorry, I encountered an error getting room information. Please try again."
    
    def _extract_hotel_name(self, user_input: str, context: str = "") -> str:
        """Extract hotel name from input or context"""
        # Check for common hotel names
        hotel_patterns = [
            "grand hyatt", "hyatt", "mandarin oriental", "shangri-la", "hilton", 
            "marriott", "westin", "sheraton", "ritz carlton", "four seasons"
        ]
        
        combined_text = (user_input + " " + context).lower()
        
        for pattern in hotel_patterns:
            if pattern in combined_text:
                if "grand hyatt" in combined_text:
                    return "Grand Hyatt Kuala Lumpur"
                elif "hyatt" in combined_text:
                    return "Grand Hyatt Kuala Lumpur"  # Default to Grand Hyatt
                # Add more mappings as needed
        
        return ""
    
    def _extract_room_name(self, user_input: str) -> str:
        """Extract room name from input"""
        room_keywords = {
            "deluxe king": "deluxe king",
            "king": "king",
            "twin": "twin", 
            "suite": "suite",
            "deluxe": "deluxe",
            "executive": "executive"
        }
        
        user_lower = user_input.lower()
        for keyword, room_type in room_keywords.items():
            if keyword in user_lower:
                return room_type
        
        return ""


# Create the room intelligence agent instance
room_intelligence_agent = RoomIntelligenceAgent()

@tool
def room_intelligence_agent_tool(user_input: str, conversation_context: str = "") -> str:
    """
    🛏️ ROOM INTELLIGENCE AGENT - Room Expert
    
    Following agent_workflow.md architecture for room-specific queries.
    
    AGENT'S JOB: "Tell guests everything about rooms"
    
    WORKFLOW STEPS:
    1. 🎯 Identify which room guest is asking about
    2. 📝 Get room details and amenities
    3. 🍳 Check breakfast and meal policies  
    4. 💰 Show pricing options
    5. 📊 Compare with other rooms if needed
    
    ✅ HANDLES:
    • Room-specific questions and amenities
    • Breakfast policy interpretation 
    • Room pricing and comparisons
    
    ❌ ROUTES TO OTHER AGENTS:
    • Hotel-wide questions → Hotel Intelligence Agent
    • Booking operations → Booking Agent
    • Hotel discovery → Discovery Agent
    
    Args:
        user_input: Guest's room-related question
        conversation_context: Recent conversation for context
        
    Returns:
        Detailed room information with breakfast policy and pricing
    """
    
    try:
        return room_intelligence_agent.process(user_input, conversation_context)
        
    except Exception as e:
        print(f"❌ Room Intelligence Agent tool error: {e}")
        return "❌ Sorry, I encountered an error getting room information. Please specify the hotel and room type."


# Export tools following agent_workflow.md architecture
ROOM_INTELLIGENCE_AGENT_TOOLS = [
    # Main agent tool
    room_intelligence_agent_tool,
    
    # Individual workflow tools (for direct access if needed)
    identify_room_type,
    get_room_amenities,
    check_breakfast_policy, 
    get_room_pricing,
    compare_room_options
]

print("🛏️ Room Intelligence Agent initialized - Following agent_workflow.md architecture") 
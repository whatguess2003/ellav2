#!/usr/bin/env python3
"""
🏨 HOTEL INTELLIGENCE AGENT - Hotel Expert
Following agent_workflow.md architecture: Tell guests everything about the hotel itself

WORKFLOW STEPS:
1. 🏨 Identify the specific hotel
2. 📋 Get hotel details and facilities
3. 📜 Check hotel policies
4. 📞 Provide contact information
5. 🌟 Present complete hotel profile

AGENT BOUNDARIES:
✅ Hotel facilities and amenities (pool, gym, spa, restaurant, wifi)
✅ Hotel policies (check-in/out, pet policy, cancellation)
✅ Hotel contact information and location
✅ Hotel profile and star rating
❌ Room-specific questions → Route to Room Intelligence Agent
❌ Booking operations → Route to Booking Agent
❌ Hotel discovery/search → Route to Discovery Agent
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

# HOTEL INTELLIGENCE AGENT ARCHITECTURE - Following agent_workflow.md

@tool
def identify_hotel(hotel_query: str, city: str = "") -> str:
    """
    HOTEL INTELLIGENCE TOOL 1: Find specific hotel by name or description
    
    Identifies the exact hotel the guest is asking about based on name or description.
    
    Args:
        hotel_query: Hotel name or description to search for
        city: City context for better identification (optional)
        
    Returns:
        JSON string with identified hotel details
    """
    print(f"🏨 HOTEL IDENTIFICATION: '{hotel_query}' in {city or 'any city'}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build search query
            query = """
                        SELECT h.property_id, h.hotel_name, h.city_name, h.state_name,
               h.star_rating, h.latitude, h.longitude, h.description
                FROM hotels h
                WHERE h.is_active = 1
            """
            params = []
            
            # Add hotel name search
            query += " AND LOWER(h.hotel_name) LIKE LOWER(?)"
            params.append(f"%{hotel_query}%")
            
            # Add city filter if provided
            if city:
                            query += " AND LOWER(h.city_name) LIKE LOWER(?)"
            params.append(f"%{city}%")
            
            query += " ORDER BY h.star_rating DESC, h.hotel_name ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No hotel found matching '{hotel_query}'" + (f" in {city}" if city else "")
                })
            
            # Format results
            hotels = []
            for prop_id, name, city_loc, state, rating, lat, lng, description in results:
                hotels.append({
                    "property_id": prop_id,
                    "hotel_name": name,
                    "city": city_loc,
                    "state": state,
                    "rating": rating,
                    "location": {"latitude": lat, "longitude": lng},
                    "description": description
                })
            
            return json.dumps({
                "status": "found",
                "hotels": hotels,
                "count": len(hotels)
            })
            
    except Exception as e:
        print(f"❌ Hotel identification error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_hotel_profile(hotel_name: str) -> str:
    """
    HOTEL INTELLIGENCE TOOL 2: Get basic hotel info (rating, location, description)
    
    Retrieves essential hotel profile information including star rating and location.
    
    Args:
        hotel_name: Hotel name to get profile for
        
    Returns:
        JSON string with hotel profile details
    """
    print(f"📋 HOTEL PROFILE: {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.property_id, h.hotel_name, h.city_name, h.state_name,
                       h.star_rating, h.description, h.address,
                       h.latitude, h.longitude
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
                ORDER BY h.star_rating DESC
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No hotel profile found for '{hotel_name}'"
                })
            
            # Format profile data
            profiles = []
            for prop_id, name, city, state, rating, description, address, lat, lng in results:
                profiles.append({
                    "property_id": prop_id,
                    "hotel_name": name,
                    "location": {
                        "city": city,
                        "state": state,
                        "address": address,
                        "coordinates": {"latitude": lat, "longitude": lng}
                    },
                    "star_rating": rating,
                    "description": description
                })
            
            return json.dumps({
                "status": "found",
                "profiles": profiles,
                "count": len(profiles)
            })
            
    except Exception as e:
        print(f"❌ Hotel profile error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_hotel_facilities(hotel_name: str) -> str:
    """
    HOTEL INTELLIGENCE TOOL 3: Get hotel amenities (pool, gym, spa, restaurant, wifi)
    
    Retrieves comprehensive hotel facility information.
    
    Args:
        hotel_name: Hotel name to get facilities for
        
    Returns:
        JSON string with detailed hotel facilities
    """
    print(f"🏊 HOTEL FACILITIES: {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, h.facilities, h.star_rating
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No facilities information found for '{hotel_name}'"
                })
            
            # Format facilities data
            hotel_facilities = []
            for name, facilities_json, rating in results:
                try:
                    facilities = json.loads(facilities_json) if facilities_json else []
                except:
                    facilities = [facilities_json] if facilities_json else []
                
                hotel_facilities.append({
                    "hotel_name": name,
                    "star_rating": rating,
                    "facilities": facilities,
                    "facility_count": len(facilities)
                })
            
            return json.dumps({
                "status": "found",
                "hotel_facilities": hotel_facilities,
                "count": len(hotel_facilities)
            })
            
    except Exception as e:
        print(f"❌ Hotel facilities error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_hotel_policies(hotel_name: str) -> str:
    """
    HOTEL INTELLIGENCE TOOL 4: Get check-in times, policies, rules
    
    Retrieves hotel policies including check-in/out times, cancellation policies, etc.
    
    Args:
        hotel_name: Hotel name to get policies for
        
    Returns:
        JSON string with hotel policies and rules
    """
    print(f"📜 HOTEL POLICIES: {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get hotel policies from multiple potential sources
            query = """
                SELECT h.hotel_name, h.hotel_policies, h.cancellation_policy,
                       h.check_in_time, h.check_out_time
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No policy information found for '{hotel_name}'"
                })
            
            # Format policy data
            hotel_policies = []
            for name, policies, cancellation, check_in, check_out in results:
                policy_info = {
                    "hotel_name": name,
                    "check_in_time": check_in or "Standard check-in",
                    "check_out_time": check_out or "Standard check-out",
                    "cancellation_policy": cancellation or "Standard cancellation terms",
                    "additional_policies": policies or "Standard hotel policies"
                }
                hotel_policies.append(policy_info)
            
            return json.dumps({
                "status": "found",
                "hotel_policies": hotel_policies,
                "count": len(hotel_policies)
            })
            
    except Exception as e:
        print(f"❌ Hotel policies error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_contact_info(hotel_name: str) -> str:
    """
    HOTEL INTELLIGENCE TOOL 5: Get phone, email, address
    
    Retrieves complete hotel contact information.
    
    Args:
        hotel_name: Hotel name to get contact info for
        
    Returns:
        JSON string with hotel contact details
    """
    print(f"📞 HOTEL CONTACT: {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, h.phone, h.email, h.address,
                       h.city_name, h.state_name, h.website
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No contact information found for '{hotel_name}'"
                })
            
            # Format contact data
            hotel_contacts = []
            for name, phone, email, address, city, state, website in results:
                contact_info = {
                    "hotel_name": name,
                    "phone_number": phone or "Not available",
                    "email": email or "Not available", 
                    "address": address or "Not available",
                    "location": f"{city}, {state}",
                    "website": website or "Not available"
                }
                hotel_contacts.append(contact_info)
            
            return json.dumps({
                "status": "found",
                "hotel_contacts": hotel_contacts,
                "count": len(hotel_contacts)
            })
            
    except Exception as e:
        print(f"❌ Hotel contact error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

class HotelIntelligenceAgent:
    """Hotel Intelligence Agent following agent_workflow.md architecture"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=MODEL_CONFIG.get("function_execution"),
            temperature=0.3,
            openai_api_key=OPENAI_API_KEY,
            max_tokens=500
        )
    
    def process(self, user_input: str, conversation_context: str = "") -> str:
        """
        Process hotel intelligence queries following 5-step workflow
        
        WORKFLOW:
        1. IDENTIFY: Which hotel are they asking about?
        2. PROFILE: Get basic hotel information
        3. FACILITIES: List hotel amenities (pool, gym, spa, etc.)
        4. POLICIES: Check-in/out times, pet policy, etc.
        5. CONTACT: Phone, email, address information
        """
        print(f"🏨 HOTEL INTELLIGENCE PROCESSING: {user_input}")
        
        # Create agent workflow tools
        tools = [
            identify_hotel,
            get_hotel_profile,
            get_hotel_facilities,
            get_hotel_policies,
            get_contact_info
        ]
        
        # Create system prompt for hotel intelligence workflow
        system_prompt = """You are the Hotel Intelligence Agent. Your job: Answer ALL hotel questions.

WORKFLOW (Always follow this order):
1. IDENTIFY: Which hotel are they asking about?
2. PROFILE: Get basic hotel information  
3. FACILITIES: List hotel amenities (pool, gym, spa, restaurant, wifi)
4. POLICIES: Check-in/out times, pet policy, etc.
5. CONTACT: Phone, email, address information

YOUR TOOLS:
• identify_hotel - Find hotel by name or description
• get_hotel_profile - Basic details (rating, location, description)
• get_hotel_facilities - Pool, gym, spa, restaurant, wifi
• get_hotel_policies - Check-in times, policies, rules
• get_contact_info - Phone, email, address

ALWAYS:
✅ Start with hotel name and star rating
✅ List key facilities (pool, gym, restaurant)
✅ Include contact information when relevant
✅ Mention check-in/check-out times if asked

NEVER:
❌ Answer room-specific questions (send to Room Intelligence Agent)
❌ Handle bookings (send to Booking Agent)  
❌ Recommend other hotels (send to Discovery Agent)

ROUTING RESPONSES:
For room questions: "For room details and amenities, ask about specific rooms"
For bookings: "To make a booking, say 'book [hotel name]'"
For hotel search: "To find hotels, tell me your location and dates"

RESPONSE STYLE:
• Natural, conversational tone
• Include specific details (star rating, facilities)
• Provide contact info when helpful
• Keep responses concise but complete"""

        try:
            from langchain.agents import create_openai_functions_agent, AgentExecutor
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
            from langchain.schema import HumanMessage
            
            # Create agent prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # Create and execute agent
            agent = create_openai_functions_agent(self.llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=3,
                return_intermediate_steps=False
            )
            
            # Process the query
            result = agent_executor.invoke({
                "input": f"{user_input}\n\nContext: {conversation_context}"
            })
            
            return result["output"]
            
        except Exception as e:
            print(f"❌ Hotel Intelligence Agent error: {e}")
            return self._fallback_response(user_input)
    
    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when agent workflow fails"""
        return f"I'd be happy to help with hotel information! However, I need you to specify which hotel you're asking about. Please mention the hotel name and I can tell you about its facilities, policies, and contact details."

@tool
def hotel_intelligence_agent_tool(user_input: str, conversation_context: str = "") -> str:
    """
    Hotel Intelligence Agent Tool - Handle all hotel facility and information queries
    
    Use this for:
    • Hotel facilities (pool, gym, spa, restaurant, wifi)
    • Hotel policies (check-in/out times, pet policy, cancellation)
    • Hotel contact information (phone, email, address)
    • Hotel profile and star rating
    
    Do NOT use for:
    • Room-specific questions → Use room_intelligence_agent_tool
    • Hotel search/discovery → Use discovery_agent_tool
    • Booking operations → Use booking tools
    
    Args:
        user_input: Guest's query about hotel facilities/information
        conversation_context: Previous conversation context
        
    Returns:
        Comprehensive hotel information response
    """
    agent = HotelIntelligenceAgent()
    return agent.process(user_input, conversation_context)
#!/usr/bin/env python3
"""
🍽️ SERVICE AGENT - Service Expert
Following agent_workflow.md architecture: Handle all hotel services

WORKFLOW STEPS:
1. 🎯 Identify which service guest is asking about
2. 🏨 Identify the specific hotel context
3. 📋 Get service details and policies
4. 💰 Show pricing and availability
5. 📞 Provide service contact/booking information

AGENT BOUNDARIES:
✅ Breakfast services and policies
✅ Spa services and treatments
✅ Restaurant and dining services
✅ Room service and housekeeping
✅ Laundry and concierge services
✅ Business center and meeting rooms
❌ Room amenities (furniture, view) → Route to Room Intelligence Agent
❌ Hotel facilities (pool, gym) → Route to Hotel Intelligence Agent
❌ Hotel discovery → Route to Discovery Agent
❌ Booking operations → Route to Booking Agent
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

# SERVICE AGENT ARCHITECTURE - Following agent_workflow.md

@tool
def identify_service_type(service_query: str, hotel_name: str = "") -> str:
    """
    SERVICE AGENT TOOL 1: Identify which service the guest is asking about
    
    Categorizes the service request and identifies the hotel context.
    
    Args:
        service_query: Service question (e.g., "breakfast", "spa", "room service", "laundry")
        hotel_name: Hotel name for context (optional)
        
    Returns:
        JSON string with identified service type and category
    """
    print(f"🎯 SERVICE IDENTIFICATION: '{service_query}' at {hotel_name or 'any hotel'}")
    
    # Service categorization
    service_categories = {
        "breakfast": ["breakfast", "morning meal", "buffet", "continental"],
        "dining": ["restaurant", "dining", "dinner", "lunch", "food", "menu"],
        "spa": ["spa", "massage", "treatment", "wellness", "facial", "sauna"],
        "room_service": ["room service", "in-room dining", "24 hour", "delivery"],
        "housekeeping": ["housekeeping", "cleaning", "turndown", "towels", "amenities"],
        "laundry": ["laundry", "dry cleaning", "washing", "pressing", "clothes"],
        "concierge": ["concierge", "assistance", "recommendations", "tickets", "tours"],
        "business": ["business center", "meeting", "conference", "printing", "internet"]
    }
    
    query_lower = service_query.lower()
    identified_services = []
    
    for category, keywords in service_categories.items():
        if any(keyword in query_lower for keyword in keywords):
            identified_services.append(category)
    
    if not identified_services:
        identified_services = ["general_service"]
    
    return json.dumps({
        "status": "identified",
        "services": identified_services,
        "query": service_query,
        "hotel": hotel_name or "any",
        "primary_service": identified_services[0] if identified_services else "general_service"
    })

@tool
def get_breakfast_service(hotel_name: str, room_type: str = "") -> str:
    """
    SERVICE AGENT TOOL 2: Get breakfast service details and policies
    
    Retrieves comprehensive breakfast information including inclusion policy and pricing.
    
    Args:
        hotel_name: Hotel name to check breakfast service
        room_type: Specific room type (optional, checks all rooms if not provided)
        
    Returns:
        JSON string with breakfast service details
    """
    print(f"🍳 BREAKFAST SERVICE: {hotel_name} - {room_type or 'all rooms'}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, rt.room_name, rt.breakfast_policy, rt.base_price_per_night,
                       h.facilities, h.phone, h.email
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE h.is_active = 1 AND rt.is_active = 1
                AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            params = [f"%{hotel_name}%"]
            
            if room_type:
                query += " AND LOWER(rt.room_name) LIKE LOWER(?)"
                params.append(f"%{room_type}%")
            
            query += " ORDER BY rt.base_price_per_night ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No breakfast information found for {hotel_name}"
                })
            
            # Process breakfast policies
            breakfast_info = {}
            hotel_info = None
            
            for hotel, room, policy, price, facilities, phone, email in results:
                if not hotel_info:
                    hotel_info = {
                        "hotel_name": hotel,
                        "phone": phone,
                        "email": email,
                        "facilities": facilities
                    }
                
                if policy not in breakfast_info:
                    breakfast_info[policy] = []
                
                breakfast_info[policy].append({
                    "room_name": room,
                    "room_price": price
                })
            
            # Format breakfast service response
            service_details = {
                "hotel": hotel_info,
                "breakfast_service": {},
                "summary": ""
            }
            
            # Interpret breakfast policies
            for policy, rooms in breakfast_info.items():
                if policy == "YES":
                    service_details["breakfast_service"]["included"] = {
                        "policy": "Complimentary breakfast included",
                        "rooms": rooms,
                        "cost": "No additional charge"
                    }
                elif policy == "NO":
                    service_details["breakfast_service"]["not_available"] = {
                        "policy": "Breakfast not offered by hotel",
                        "rooms": rooms,
                        "alternative": "Check nearby restaurants"
                    }
                elif policy and "RM" in policy and "perpax" in policy:
                    # Extract price from "RM50perpax" format
                    try:
                        price_part = policy.replace("RM", "").replace("perpax", "")
                        price = float(price_part)
                        service_details["breakfast_service"]["additional_charge"] = {
                            "policy": f"Breakfast available for RM{price} per person per night",
                            "rooms": rooms,
                            "cost": f"RM{price} per person per night"
                        }
                    except:
                        service_details["breakfast_service"]["custom_policy"] = {
                            "policy": policy,
                            "rooms": rooms
                        }
            
            # Create summary
            if "included" in service_details["breakfast_service"]:
                service_details["summary"] = f"✅ Complimentary breakfast included with room stays at {hotel}"
            elif "additional_charge" in service_details["breakfast_service"]:
                charge_info = service_details["breakfast_service"]["additional_charge"]
                service_details["summary"] = f"🍽️ Breakfast available at {hotel} for {charge_info['cost']}"
            elif "not_available" in service_details["breakfast_service"]:
                service_details["summary"] = f"❌ {hotel} does not offer breakfast service"
            
            return json.dumps({
                "status": "found",
                "service_details": service_details
            })
            
    except Exception as e:
        print(f"❌ Breakfast service error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_hotel_services(hotel_name: str, service_type: str = "") -> str:
    """
    SERVICE AGENT TOOL 3: Get hotel service offerings and details
    
    Retrieves information about spa, dining, room service, and other hotel services.
    
    Args:
        hotel_name: Hotel name to check services
        service_type: Specific service type to filter (spa, dining, room_service, etc.)
        
    Returns:
        JSON string with hotel service details
    """
    print(f"🏨 HOTEL SERVICES: {service_type or 'all services'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, h.facilities, h.phone, h.email, h.website,
                       h.star_rating, h.description
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            results = cursor.fetchall()
            
            if not results:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No service information found for {hotel_name}"
                })
            
            hotel, facilities, phone, email, website, rating, description = results[0]
            
            # Parse facilities for services
            try:
                facilities_list = json.loads(facilities) if facilities else []
            except:
                facilities_list = [facilities] if facilities else []
            
            # Categorize services
            services = {
                "dining": [],
                "spa_wellness": [],
                "business": [],
                "recreation": [],
                "convenience": []
            }
            
            for facility in facilities_list:
                if not facility:
                    continue
                    
                facility_lower = facility.lower()
                
                # Dining services
                if any(word in facility_lower for word in ["restaurant", "dining", "cafe", "bar", "kitchen", "food"]):
                    services["dining"].append(facility)
                # Spa & Wellness
                elif any(word in facility_lower for word in ["spa", "massage", "wellness", "sauna", "jacuzzi", "fitness", "gym"]):
                    services["spa_wellness"].append(facility)
                # Business services
                elif any(word in facility_lower for word in ["business", "meeting", "conference", "internet", "wifi", "computer"]):
                    services["business"].append(facility)
                # Recreation
                elif any(word in facility_lower for word in ["pool", "tennis", "golf", "game", "entertainment", "tour"]):
                    services["recreation"].append(facility)
                # Convenience services
                elif any(word in facility_lower for word in ["concierge", "laundry", "parking", "transport", "shuttle", "room service"]):
                    services["convenience"].append(facility)
            
            # Filter by service type if specified
            if service_type:
                service_map = {
                    "dining": services["dining"],
                    "spa": services["spa_wellness"],
                    "business": services["business"],
                    "recreation": services["recreation"],
                    "concierge": services["convenience"]
                }
                
                filtered_services = service_map.get(service_type, [])
                if not filtered_services:
                    return json.dumps({
                        "status": "not_available",
                        "message": f"No {service_type} services found at {hotel}"
                    })
                
                return json.dumps({
                    "status": "found",
                    "hotel_name": hotel,
                    "service_type": service_type,
                    "services": filtered_services,
                    "contact": {"phone": phone, "email": email, "website": website}
                })
            
            return json.dumps({
                "status": "found",
                "hotel_name": hotel,
                "star_rating": rating,
                "all_services": services,
                "contact": {"phone": phone, "email": email, "website": website},
                "total_services": sum(len(category) for category in services.values())
            })
            
    except Exception as e:
        print(f"❌ Hotel services error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_service_pricing(hotel_name: str, service_name: str) -> str:
    """
    SERVICE AGENT TOOL 4: Get pricing information for specific services
    
    Retrieves pricing details for hotel services like spa treatments, dining, etc.
    
    Args:
        hotel_name: Hotel name
        service_name: Specific service to get pricing for
        
    Returns:
        JSON string with service pricing information
    """
    print(f"💰 SERVICE PRICING: {service_name} at {hotel_name}")
    
    # For now, return general pricing guidance since detailed service pricing 
    # would need a separate services pricing table
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, h.star_rating, h.phone, h.email
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            result = cursor.fetchone()
            
            if not result:
                return json.dumps({
                    "status": "not_found",
                    "message": f"Hotel {hotel_name} not found"
                })
            
            hotel, rating, phone, email = result
            
            # Provide general pricing guidance based on hotel rating
            pricing_guidance = {
                "hotel_name": hotel,
                "service": service_name,
                "star_rating": rating,
                "pricing_note": f"For current {service_name} pricing, please contact the hotel directly",
                "contact": {
                    "phone": phone,
                    "email": email
                },
                "general_guidance": ""
            }
            
            # Add rating-based guidance
            if rating >= 5:
                pricing_guidance["general_guidance"] = "Premium pricing - expect luxury service rates"
            elif rating >= 4:
                pricing_guidance["general_guidance"] = "Mid to high range pricing"
            else:
                pricing_guidance["general_guidance"] = "Moderate pricing - good value options available"
            
            return json.dumps({
                "status": "contact_required",
                "pricing_info": pricing_guidance
            })
            
    except Exception as e:
        print(f"❌ Service pricing error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@tool
def get_service_contact(hotel_name: str, service_type: str = "") -> str:
    """
    SERVICE AGENT TOOL 5: Get contact information for hotel services
    
    Provides contact details for booking or inquiring about hotel services.
    
    Args:
        hotel_name: Hotel name
        service_type: Specific service department to contact
        
    Returns:
        JSON string with service contact information
    """
    print(f"📞 SERVICE CONTACT: {service_type or 'general'} at {hotel_name}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT h.hotel_name, h.phone, h.email, h.website, h.address,
                       h.city_name, h.state_name
                FROM hotels h
                WHERE h.is_active = 1 AND LOWER(h.hotel_name) LIKE LOWER(?)
            """
            
            cursor.execute(query, [f"%{hotel_name}%"])
            result = cursor.fetchone()
            
            if not result:
                return json.dumps({
                    "status": "not_found",
                    "message": f"Contact information not found for {hotel_name}"
                })
            
            hotel, phone, email, website, address, city, state = result
            
            contact_info = {
                "hotel_name": hotel,
                "location": f"{city}, {state}",
                "main_contact": {
                    "phone": phone or "Not available",
                    "email": email or "Not available",
                    "website": website or "Not available",
                    "address": address or "Not available"
                },
                "service_departments": {
                    "breakfast": "Contact main hotel number for breakfast inquiries",
                    "spa": "Ask for spa department or wellness center",
                    "dining": "Request restaurant reservations or room service",
                    "concierge": "Ask for concierge services",
                    "housekeeping": "Contact housekeeping department",
                    "business": "Request business center or meeting facilities"
                }
            }
            
            if service_type:
                specific_guidance = contact_info["service_departments"].get(
                    service_type, 
                    f"Ask for {service_type} department when calling"
                )
                contact_info["specific_guidance"] = specific_guidance
            
            return json.dumps({
                "status": "found",
                "contact_details": contact_info
            })
            
    except Exception as e:
        print(f"❌ Service contact error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

class ServiceAgent:
    """Service Agent following agent_workflow.md architecture"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=MODEL_CONFIG.get("function_execution"),
            temperature=0.3,
            openai_api_key=OPENAI_API_KEY,
            max_tokens=500
        )
    
    def process(self, user_input: str, conversation_context: str = "") -> str:
        """
        Process service queries following 5-step workflow
        
        WORKFLOW:
        1. IDENTIFY: Which service are they asking about?
        2. HOTEL: Get hotel context 
        3. DETAILS: Get service details and policies
        4. PRICING: Show pricing and availability
        5. CONTACT: Provide service contact/booking information
        """
        print(f"🍽️ SERVICE AGENT PROCESSING: {user_input}")
        
        # Create agent workflow tools
        tools = [
            identify_service_type,
            get_breakfast_service,
            get_hotel_services,
            get_service_pricing,
            get_service_contact
        ]
        
        # Create system prompt for service workflow
        system_prompt = """You are the Service Agent. Your job: Answer ALL hotel service questions.

WORKFLOW (Always follow this order):
1. IDENTIFY: Which service are they asking about?
2. HOTEL: Get hotel context
3. DETAILS: Get service details and policies  
4. PRICING: Show pricing and availability
5. CONTACT: Provide service contact/booking information

YOUR TOOLS:
• identify_service_type - Categorize service requests
• get_breakfast_service - Breakfast policies and inclusion details
• get_hotel_services - Spa, dining, room service, concierge services  
• get_service_pricing - Service pricing information
• get_service_contact - Contact info for service bookings

BREAKFAST POLICY INTERPRETATION:
• "YES" → "Complimentary breakfast included with room stay"
• "NO" → "This hotel does not offer breakfast service"
• "RM50perpax" → "Breakfast available for RM50 per person per night"
• Other pricing → Parse and explain clearly

SERVICE CATEGORIES:
• Breakfast → get_breakfast_service
• Spa/Wellness → get_hotel_services with service_type="spa"
• Dining/Restaurant → get_hotel_services with service_type="dining"
• Room Service → get_hotel_services with service_type="convenience"
• Business Services → get_hotel_services with service_type="business"

ALWAYS:
✅ Start with service identification
✅ Provide clear pricing information
✅ Include contact details for bookings
✅ Explain service policies clearly

NEVER:
❌ Answer room amenities questions (send to Room Intelligence Agent)
❌ Answer hotel facilities questions (send to Hotel Intelligence Agent)
❌ Handle hotel search (send to Discovery Agent)
❌ Handle bookings (send to Booking Agent)

ROUTING RESPONSES:
For room amenities: "For room features and amenities, ask about specific rooms"
For hotel facilities: "For hotel facilities like pool and gym, ask about hotel amenities"
For hotel search: "To find hotels, tell me your location and dates"
For bookings: "To make a booking, say 'book [hotel name]'"

RESPONSE STYLE:
• Natural, helpful tone
• Clear service policies and pricing
• Practical next steps for service booking
• Include contact information when relevant"""

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
            print(f"❌ Service Agent error: {e}")
            return self._fallback_response(user_input)
    
    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when agent workflow fails"""
        return f"I'd be happy to help with hotel service information! Please specify which hotel and which service you're asking about (breakfast, spa, dining, room service, etc.)."

@tool
def service_agent_tool(user_input: str, conversation_context: str = "") -> str:
    """
    Service Agent Tool - Handle all hotel service queries including breakfast
    
    Use this for:
    • Breakfast services and policies ("Does room include breakfast?")
    • Spa services and treatments ("Hotel spa services", "Massage pricing")
    • Restaurant and dining services ("Hotel restaurant hours", "Room service menu")
    • Concierge and housekeeping services ("Laundry service", "Tour bookings")
    • Business center services ("Meeting rooms", "Printing services")
    
    Do NOT use for:
    • Room amenities (furniture, balcony, view) → Use room_intelligence_agent_tool
    • Hotel facilities (pool, gym, lobby) → Use hotel_intelligence_agent_tool
    • Hotel search/discovery → Use discovery_agent_tool
    • Booking operations → Use booking tools
    
    Args:
        user_input: Guest's query about hotel services
        conversation_context: Previous conversation context
        
    Returns:
        Comprehensive service information with policies and contact details
    """
    agent = ServiceAgent()
    return agent.process(user_input, conversation_context)

# Export the service agent tools
SERVICE_AGENT_TOOLS = [service_agent_tool]

print("🍽️ Service Agent initialized - Following agent_workflow.md architecture")
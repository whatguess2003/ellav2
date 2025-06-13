#!/usr/bin/env python3
"""
🔍 DISCOVERY AGENT - Hotel Finder Expert
Following agent_workflow.md architecture: Help guests find the perfect hotel

WORKFLOW STEPS:
1. 📝 Extract search criteria (city, dates, budget, preferences)
2. 🔎 Search for available hotels in location  
3. 🎛️ Filter by guest preferences (price, amenities)
4. ✅ Check availability for their dates
5. 🏆 Show best 3-5 options with reasons

AGENT BOUNDARIES:
✅ Hotel discovery and search workflows
✅ Availability checking and filtering
✅ Price range and preference matching
❌ Room-specific questions → Route to Room Intelligence Agent
❌ Hotel facility questions → Route to Hotel Intelligence Agent  
❌ Booking operations → Route to Booking Agent
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, date, timedelta
import sqlite3

from config.settings import ***REMOVED***, MODEL_CONFIG
from core.guest_id import get_guest_id
from memory.redis_memory import get_search_session, store_search_session, update_search_session
from .search_tools.hotel_search_tool import search_hotels_with_availability

# DISCOVERY AGENT ARCHITECTURE - Following agent_workflow.md

@tool
def extract_search_criteria(user_input: str, conversation_context: str = "") -> str:
    """
    DISCOVERY AGENT TOOL 1: Extract search criteria from natural language
    
    Aggressively extracts: city, dates, adults, budget, preferences from guest input.
    Always provides defaults for missing critical information.
    
    Args:
        user_input: Guest's natural language request
        conversation_context: Previous conversation for context
        
    Returns:
        JSON string with extracted criteria
    """
    criteria_extractor = SearchCriteriaExtractor()
    criteria = criteria_extractor.extract(user_input, conversation_context)
    return json.dumps(criteria)

@tool
def search_hotels_by_city(city: str, min_rating: int = 0) -> str:
    """
    DISCOVERY AGENT TOOL 2: Find all hotels in specified city
    
    Searches hotel database for available properties in the target city.
    
    Args:
        city: Target city name
        min_rating: Minimum star rating filter (0-5)
        
    Returns:
        JSON string with hotel list
    """
    try:
        # Use existing search functionality with basic city filter
        keywords = {'city': city}
        filters = {}
        if min_rating > 0:
            filters['min_rating'] = min_rating
            
        # Default date range for basic search
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        results = search_hotels_with_availability(keywords, filters, today, tomorrow)
        return json.dumps(results)
        
    except Exception as e:
        print(f"❌ City search failed: {e}")
        return json.dumps([])

@tool  
def filter_by_preferences(hotels_data: str, price_range: str = "", amenities: str = "") -> str:
    """
    DISCOVERY AGENT TOOL 3: Filter hotels by guest preferences
    
    Applies guest preferences to hotel list for personalized results.
    
    Args:
        hotels_data: JSON string of hotels from search_hotels_by_city
        price_range: Price preference (under_200, 200_400, above_400)
        amenities: Preferred amenities (pool, gym, spa, etc.)
        
    Returns:
        JSON string with filtered hotels
    """
    try:
        hotels = json.loads(hotels_data) if isinstance(hotels_data, str) else hotels_data
        
        if not hotels:
            return json.dumps([])
        
        filtered_hotels = []
        
        for hotel in hotels:
            # Price range filtering
            if price_range:
                hotel_price = float(hotel.get('cheapest_price', 999))
                
                if price_range == 'under_200' and hotel_price >= 200:
                    continue
                elif price_range == '200_400' and (hotel_price < 200 or hotel_price > 400):
                    continue
                elif price_range == 'above_400' and hotel_price <= 400:
                    continue
            
            # Amenity filtering (if needed)
            # This would require facility data - skip for now or implement if facilities available
            
            filtered_hotels.append(hotel)
        
        return json.dumps(filtered_hotels)
        
    except Exception as e:
        print(f"❌ Preference filtering failed: {e}")
        return hotels_data  # Return original data if filtering fails

@tool
def check_availability(hotel_list: str, check_in: str, check_out: str, adults: int) -> str:
    """
    DISCOVERY AGENT TOOL 4: Verify room availability AND business rules for dates
    
    Enhanced with business rule validation - only shows hotels guests can actually book.
    Pre-validates: room capacity, stay requirements, advance booking, pricing availability.
    
    Args:
        hotel_list: JSON string of hotels to check
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)  
        adults: Number of adult guests
        
    Returns:
        JSON string with available and bookable hotels
    """
    try:
        hotels = json.loads(hotel_list) if isinstance(hotel_list, str) else hotel_list
        
        if not hotels:
            return json.dumps([])
        
        # Parse dates
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        available_hotels = []
        validation_failures = []
        
        for hotel in hotels:
            # Use existing search functionality to verify availability
            keywords = {'hotel_name': hotel['hotel_name']}
            filters = {'max_occupancy': adults}
            
            results = search_hotels_with_availability(keywords, filters, check_in_date, check_out_date)
            
            if results:  # Hotel has inventory availability
                # Now validate business rules for each available room type
                hotel_rooms_valid = []
                
                for room_detail in results[0].get('available_rooms', []):
                    room_type = room_detail.get('room_type', '')
                    
                    # BUSINESS RULE VALIDATION - Pre-validate before offering
                    validation = validate_hotel_business_rules(
                        hotel['hotel_name'], 
                        room_type, 
                        check_in_date, 
                        check_out_date, 
                        adults
                    )
                    
                    if validation['valid']:
                        # Room passes all business rules - safe to offer
                        enhanced_room = room_detail.copy()
                        enhanced_room['business_rules_validated'] = True
                        enhanced_room['validation_details'] = validation['hotel_data']
                        
                        # CRITICAL: Use DATABASE room name, not guest input
                        enhanced_room['room_type'] = validation['hotel_data']['room_name']
                        enhanced_room['database_room_name'] = validation['hotel_data']['room_name']
                        enhanced_room['guest_requested_name'] = room_type
                        
                        hotel_rooms_valid.append(enhanced_room)
                    else:
                        # Log validation failure for debugging
                        validation_failures.append({
                            'hotel': hotel['hotel_name'],
                            'room': room_type,
                            'reason': validation['reason']
                        })
                
                # Only include hotel if it has at least one valid room
                if hotel_rooms_valid:
                    hotel_with_availability = hotel.copy()
                    hotel_with_availability['available_rooms'] = len(hotel_rooms_valid)
                    hotel_with_availability['cheapest_price'] = min(room['price'] for room in hotel_rooms_valid)
                    hotel_with_availability['availability_details'] = hotel_rooms_valid
                    hotel_with_availability['business_rules_passed'] = True
                    available_hotels.append(hotel_with_availability)
        
        # Log validation failures for debugging
        if validation_failures:
            print(f"🚫 DISCOVERY AGENT - Business rule failures:")
            for failure in validation_failures:
                print(f"   • {failure['hotel']} - {failure['room']}: {failure['reason']}")
        
        print(f"✅ DISCOVERY AGENT - {len(available_hotels)} hotels passed all validations")
        
        # 🤝 UPDATE MULTI-AGENT CONTEXT with availability results
        from core.guest_id import get_guest_id
        from memory.multi_agent_context import MultiAgentContext
        
        try:
            guest_id = get_guest_id()
            context = MultiAgentContext(guest_id)
            
            # Update search context with availability results
            context.update_section("search_context", {
                "availability_checked": True,
                "available_hotels_count": len(available_hotels),
                "check_in": check_in,
                "check_out": check_out,
                "adults": adults,
                "availability_date": datetime.now().isoformat()
            })
            
            # Update room context with available room details
            if available_hotels:
                best_hotel = available_hotels[0]  # Best rated/priced hotel
                context.update_section("room_context", {
                    "available_rooms": best_hotel.get('availability_details', []),
                    "cheapest_price": best_hotel.get('cheapest_price'),
                    "selected_hotel": best_hotel.get('hotel_name'),
                    "availability_confirmed": True
                })
                
                print(f"🤝 SHARED CONTEXT UPDATED: {len(available_hotels)} hotels available")
            
        except Exception as e:
            print(f"❌ Failed to update multi-agent context: {e}")
        
        return json.dumps(available_hotels)
        
    except Exception as e:
        print(f"❌ Availability check failed: {e}")
        return hotel_list  # Return original list if check fails

@tool
def rank_and_present(available_hotels: str, criteria: str) -> str:
    """
    DISCOVERY AGENT TOOL 5: Sort and present top 3-5 hotels with reasoning
    
    Ranks available hotels by relevance and presents with explanations.
    
    Args:
        available_hotels: JSON string of available hotels
        criteria: JSON string of original search criteria
        
    Returns:
        Formatted presentation of top hotels with recommendations
    """
    try:
        hotels = json.loads(available_hotels) if isinstance(available_hotels, str) else available_hotels
        search_criteria = json.loads(criteria) if isinstance(criteria, str) else criteria
        
        if not hotels:
            city = search_criteria.get('city', 'the selected location')
            check_in = search_criteria.get('check_in', '')
            check_out = search_criteria.get('check_out', '')
            adults = search_criteria.get('adults', 2)
            
            # Calculate nights for alternative suggestions
            nights = 1
            if check_in and check_out:
                try:
                    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
                    nights = (check_out_date - check_in_date).days
                except:
                    pass
            
            # Provide intelligent alternatives based on common business rule failures
            alternatives = []
            
            # Check if it's a minimum stay issue
            if nights == 1:
                alternatives.append("• **Extend your stay**: Many hotels require 2+ nights minimum")
                alternatives.append(f"• **Try {check_in} to {(datetime.strptime(check_in, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')}** (2 nights)")
            
            # Check if it's a capacity issue
            if adults > 2:
                alternatives.append(f"• **Split into multiple rooms**: Book {adults//2} rooms for {adults} guests")
                alternatives.append("• **Look for family rooms**: Search for 'family' or 'suite' room types")
            
            # Check if it's a timing issue
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                today = datetime.now().date()
                days_ahead = (check_in_date - today).days
                
                if days_ahead < 1:
                    alternatives.append("• **Book for future dates**: Some hotels require advance booking")
                    tomorrow = today + timedelta(days=1)
                    alternatives.append(f"• **Try tomorrow**: {tomorrow.strftime('%Y-%m-%d')} onwards")
            except:
                pass
            
            # General alternatives
            alternatives.extend([
                "• **Different dates**: Try weekdays instead of weekends",
                "• **Nearby areas**: Expand search to surrounding areas",
                "• **Budget adjustment**: Consider different price ranges"
            ])
            
            response = f"""🔍 **No Available Hotels in {city}**

Unfortunately, no hotels meet all your requirements for:
📅 **Dates**: {check_in} to {check_out} ({nights} night{'s' if nights != 1 else ''})
👥 **Guests**: {adults} adult{'s' if adults != 1 else ''}

💡 **Try These Alternatives:**
{chr(10).join(alternatives[:5])}

🤝 **I'm here to help!** Tell me:
• "Show me 2-night options" 
• "Find family rooms for {adults} people"
• "What's available next week?"
• "Show me budget hotels under RM200"
"""
            return response
        
        # Sort hotels by price and rating
        sorted_hotels = sorted(hotels, key=lambda h: (
            -float(h.get('star_rating', 0)),  # Higher rating first
            float(h.get('cheapest_price', 999))  # Lower price second
        ))
        
        # Take top 5 hotels max
        top_hotels = sorted_hotels[:5]
        
        # Format presentation
        city = search_criteria.get('city', 'Your destination')
        check_in = search_criteria.get('check_in', '')
        check_out = search_criteria.get('check_out', '')
        adults = search_criteria.get('adults', 2)
        
        if check_in and check_out:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            nights = (check_out_date - check_in_date).days
            date_str = f"({check_in_date.strftime('%B %d')} - {nights} night{'s' if nights != 1 else ''})"
        else:
            date_str = ""
        
        response = f"🏨 **Top Hotels in {city}** {date_str}\n\n"
        
        for i, hotel in enumerate(top_hotels, 1):
            response += f"**{i}. {hotel['hotel_name']}** ({hotel.get('star_rating', 'N/A')}⭐)\n"
            response += f"📍 {hotel.get('city_name', city)}\n"
            response += f"💰 From RM{hotel.get('cheapest_price', 'N/A')}/night\n"
            
            # Business rules validation status
            if hotel.get('business_rules_passed'):
                response += f"✅ **Pre-validated** - Ready to book immediately\n"
            
            # Availability info with business rule details
            available_rooms = hotel.get('available_rooms', 0)
            if available_rooms:
                response += f"🛏️ {available_rooms} room type{'s' if available_rooms != 1 else ''} available\n"
                
                # Show business rule compliance for transparency
                room_details = hotel.get('availability_details', [])
                if room_details and len(room_details) > 0:
                    sample_room = room_details[0].get('validation_details', {})
                    if sample_room:
                        max_occupancy = sample_room.get('max_occupancy', 0)
                        min_stay = sample_room.get('min_stay_nights', 0)
                        max_stay = sample_room.get('max_stay_nights', 0)
                        
                        response += f"👥 Capacity: Up to {max_occupancy} guests\n"
                        if min_stay > 1 or max_stay < 365:
                            response += f"📅 Stay policy: {min_stay}-{max_stay} nights\n"
            
            # Distance info if available
            if hotel.get('distance_to_airport_km'):
                response += f"✈️ {hotel['distance_to_airport_km']}km from airport\n"
            
            # Enhanced recommendation reasons
            reasons = []
            if hotel.get('star_rating', 0) >= 4:
                reasons.append("High rating")
            if float(hotel.get('cheapest_price', 999)) < 300:
                reasons.append("Great value")
            if hotel.get('distance_to_airport_km', 999) < 20:
                reasons.append("Convenient location")
            if hotel.get('business_rules_passed'):
                reasons.append("Booking guaranteed")
            
            if reasons:
                response += f"✨ Why recommended: {', '.join(reasons)}\n"
            
            response += "\n"
        
        # Next steps (following agent_workflow.md)
        response += "💡 **Next Steps:**\n"
        response += "• Ask about room details: 'Tell me about [hotel name] rooms'\n"
        response += "• Ask about hotel facilities: 'What facilities does [hotel name] have?'\n"  
        response += "• Ready to book: 'Book [hotel name]'\n"
        response += "• Compare prices: 'Compare [hotel name] prices'\n"
        
        return response
        
    except Exception as e:
        print(f"❌ Ranking failed: {e}")
        return "❌ Unable to rank hotels. Please try again."


class SearchCriteriaExtractor:
    """LLM-powered extraction of search criteria from natural language"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=***REMOVED***, 
            model=MODEL_CONFIG["function_execution"], 
            temperature=0.0  # Precise extraction
        )
        
    def extract(self, user_input: str, conversation_context: str = "") -> Dict:
        """Extract structured search criteria from natural language"""
        try:
            prompt = f"""AGGRESSIVE EXTRACTION: Extract hotel criteria from: "{user_input}"

Context: {conversation_context}

EXTRACT ANYTHING POSSIBLE, even partial information!

Current date: {datetime.now().date().strftime('%Y-%m-%d')}

Return ONLY valid JSON:
{{
  "city": "Kuala Lumpur",
  "check_in": "{(datetime.now().date()).strftime('%Y-%m-%d')}", 
  "check_out": "{(datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')}",
  "adults": 2,
  "action": "search",
  "hotel_name": null,
  "preferences": null,
  "price_range": null,
  "special_requirements": null
}}

AGGRESSIVE RULES:
- ALWAYS extract numbers: "2 org"→adults=2, "untuk 3"→adults=3
- ALWAYS extract dates relative to TODAY ({datetime.now().date().strftime('%Y-%m-%d')}):
  * "harini/hari ini" → TODAY ({datetime.now().date().strftime('%Y-%m-%d')})
  * "esok/besok" → TOMORROW ({(datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')})
  * "lusa" → DAY AFTER ({(datetime.now().date() + timedelta(days=2)).strftime('%Y-%m-%d')})
- ALWAYS extract locations: "KL"→"Kuala Lumpur", "KLCC"→"Kuala Lumpur"
- DEFAULT missing data: no city→"Kuala Lumpur", no date→TODAY, no adults→2
- INTERPRET Malaysian: "org"="orang"=people, "harini"="hari ini"=today
- BE AGGRESSIVE: Extract SOMETHING from every input, never return empty

MALAYSIAN TERMS:
- harini/hari ini = today ({datetime.now().date().strftime('%Y-%m-%d')})
- esok/besok = tomorrow ({(datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')})
- lusa = day after tomorrow ({(datetime.now().date() + timedelta(days=2)).strftime('%Y-%m-%d')})
- org/orang = people/adults
- untuk = for
- malam = night
- bilik = room

Return ONLY the JSON object."""
            
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Clean JSON extraction
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            criteria = json.loads(content)
            
            # AGGRESSIVE POST-PROCESSING
            # Auto-generate check_out if missing (default 1 night)
            if criteria.get('check_in') and not criteria.get('check_out'):
                check_in_date = datetime.strptime(criteria['check_in'], '%Y-%m-%d').date()
                criteria['check_out'] = (check_in_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # AGGRESSIVE defaults for missing data
            if not criteria.get('adults') or criteria.get('adults') == 0:
                criteria['adults'] = 2
                
            if not criteria.get('city'):
                criteria['city'] = "Kuala Lumpur"  # Default for Malaysia
                
            if not criteria.get('check_in'):
                # Default to today
                criteria['check_in'] = datetime.now().date().strftime('%Y-%m-%d')
                
            print(f"🧠 AGGRESSIVE LLM extracted: {criteria}")
            return criteria
            
        except Exception as e:
            print(f"❌ LLM extraction failed: {e}")
            return self._fallback_extract(user_input)
    
    def _fallback_extract(self, user_input: str) -> Dict:
        """AGGRESSIVE fallback pattern matching extraction"""
        import re
        
        criteria = {'action': 'search'}
        user_lower = user_input.lower()
        
        # AGGRESSIVE CITY PATTERNS (more variations)
        city_patterns = {
            'Kuala Lumpur': ['kl', 'kuala lumpur', 'klang valley', 'kl sentral', 'klcc', 'bukit bintang'],
            'Kota Kinabalu': ['kk', 'kota kinabalu', 'sabah', 'kinabalu'],
            'Penang': ['penang', 'georgetown', 'pg', 'pulau pinang'],
            'Johor Bahru': ['jb', 'johor bahru', 'johor', 'jb sentral'],
            'Ipoh': ['ipoh', 'perak'],
            'Malacca': ['melaka', 'malacca'],
            'Shah Alam': ['shah alam', 'selangor'],
        }
        
        for city, patterns in city_patterns.items():
            if any(pattern in user_lower for pattern in patterns):
                criteria['city'] = city
                break
        
        # AGGRESSIVE DATE PATTERNS (more Malaysian terms)
        today = datetime.now().date()
        if any(term in user_lower for term in ['esok', 'tomorrow', 'besok']):
            criteria['check_in'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif any(term in user_lower for term in ['lusa', 'day after tomorrow']):
            criteria['check_in'] = (today + timedelta(days=2)).strftime('%Y-%m-%d')
        elif any(term in user_lower for term in ['hari ini', 'today', 'harini', 'sekarang']):
            criteria['check_in'] = today.strftime('%Y-%m-%d')
        elif any(term in user_lower for term in ['weekend', 'hujung minggu']):
            # Next Saturday
            days_ahead = 5 - today.weekday()  # Saturday is 5
            if days_ahead <= 0:
                days_ahead += 7
            criteria['check_in'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        # AGGRESSIVE NUMBER EXTRACTION for adults
        # Try multiple patterns for people count
        adults_patterns = [
            r'(\d+)\s*(?:orang|org|adults?|people|pax|person)',
            r'(?:untuk|for)\s*(\d+)',
            r'(\d+)\s*(?:guest|tamu)',
            r'family.*?(\d+)',
            r'couple.*?(\d+)',
        ]
        
        for pattern in adults_patterns:
            adults_match = re.search(pattern, user_lower)
            if adults_match:
                criteria['adults'] = int(adults_match.group(1))
                break
        
        # SPECIAL CASES for common terms
        if any(term in user_lower for term in ['couple', 'pasangan', 'berdua']):
            criteria['adults'] = 2
        elif any(term in user_lower for term in ['family', 'keluarga']):
            criteria['adults'] = 4
        elif any(term in user_lower for term in ['solo', 'sendiri', 'seorang']):
            criteria['adults'] = 1
        
        # AGGRESSIVE ACTION DETECTION
        if any(term in user_lower for term in ['compare', 'bandingkan', 'banding']):
            criteria['action'] = 'compare'
        elif any(term in user_lower for term in ['check', 'availability', 'available', 'ada', 'kosong']):
            criteria['action'] = 'availability'
        elif any(term in user_lower for term in ['list', 'pilihan', 'options', 'suggest']):
            criteria['action'] = 'shortlist'
        
        # PRICE RANGE EXTRACTION
        if any(term in user_lower for term in ['cheap', 'murah', 'budget']):
            criteria['price_range'] = 'under_200'
        elif any(term in user_lower for term in ['luxury', 'mewah', 'expensive', 'premium']):
            criteria['price_range'] = 'above_400'
        elif any(term in user_lower for term in ['mid', 'sederhana', 'moderate']):
            criteria['price_range'] = '200_400'
            
        print(f"🎯 AGGRESSIVE FALLBACK extracted: {criteria}")
        return criteria


class DiscoveryAgent:
    """Discovery Agent - Hotel Finder Expert following agent_workflow.md"""
    
    def __init__(self):
        self.criteria_extractor = SearchCriteriaExtractor()
        self.llm = ChatOpenAI(
            openai_api_key=***REMOVED***, 
            model=MODEL_CONFIG["function_execution"], 
            temperature=0.1
        )
    
    def process(self, user_input: str, conversation_context: str = "") -> str:
        """Process hotel discovery request following the 5-step workflow"""
        
        # DISCOVERY AGENT SYSTEM PROMPT (from agent_workflow.md)
        system_prompt = """You are the Discovery Agent. Your job: Find perfect hotels for guests.

WORKFLOW (Always follow this order):
1. EXTRACT: Get search criteria from guest
2. SEARCH: Find hotels in their location  
3. FILTER: Apply their preferences
4. CHECK: Verify availability for dates
5. PRESENT: Show 3-5 best options

YOUR TOOLS:
• extract_search_criteria - Get city, dates, adults, budget
• search_hotels_by_city - Find all hotels in location
• filter_by_preferences - Apply price/amenity filters  
• check_availability - Verify rooms available for dates
• rank_and_present - Sort and show best options

ALWAYS:
✅ Extract criteria first (city is mandatory)
✅ Check availability before recommending
✅ Explain WHY you recommend each hotel
✅ Ask if they want to see rooms or book

NEVER:
❌ Recommend hotels without checking availability
❌ Show more than 5 options (overwhelming)
❌ Answer room-specific questions (send to Room Agent)"""
        
        try:
            # Execute the Discovery Agent workflow using tools
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Guest request: {user_input}\nContext: {conversation_context}"}
            ]
            
            # Bind tools to the LLM
            tools = [
                extract_search_criteria,
                search_hotels_by_city, 
                filter_by_preferences,
                check_availability,
                rank_and_present
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
                    
                    if tool_name == "extract_search_criteria":
                        tool_result = extract_search_criteria.invoke(tool_args)
                    elif tool_name == "search_hotels_by_city":
                        tool_result = search_hotels_by_city.invoke(tool_args)
                    elif tool_name == "filter_by_preferences":
                        tool_result = filter_by_preferences.invoke(tool_args)
                    elif tool_name == "check_availability":
                        tool_result = check_availability.invoke(tool_args)
                    elif tool_name == "rank_and_present":
                        tool_result = rank_and_present.invoke(tool_args)
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
            print(f"❌ Discovery Agent error: {e}")
            
            # Fallback to direct workflow execution
            return self._direct_workflow(user_input, conversation_context)
    
    def _direct_workflow(self, user_input: str, conversation_context: str = "") -> str:
        """Direct workflow execution as fallback"""
        try:
            # Step 1: Extract criteria
            criteria = self.criteria_extractor.extract(user_input, conversation_context)
            
            # Store session for availability checking
            self._update_search_session(criteria, get_guest_id())
            
            # Step 2: Search hotels by city
            if not criteria.get('city'):
                return "❌ I need to know which city you're looking for hotels in. Please specify your destination."
            
            hotels_result = search_hotels_by_city.invoke({
                'city': criteria['city'],
                'min_rating': 0
            })
            
            # Step 3: Filter by preferences  
            filtered_result = filter_by_preferences.invoke({
                'hotels_data': hotels_result,
                'price_range': criteria.get('price_range', ''),
                'amenities': criteria.get('preferences', '')
            })
            
            # Step 4: Check availability
            if criteria.get('check_in') and criteria.get('check_out'):
                available_result = check_availability.invoke({
                    'hotel_list': filtered_result,
                    'check_in': criteria['check_in'],
                    'check_out': criteria['check_out'],
                    'adults': criteria.get('adults', 2)
                })
            else:
                available_result = filtered_result
            
            # Step 5: Present results
            final_result = rank_and_present.invoke({
                'available_hotels': available_result,
                'criteria': json.dumps(criteria)
            })
            
            return final_result
            
        except Exception as e:
            print(f"❌ Direct workflow failed: {e}")
            return "❌ Sorry, I encountered an error finding hotels. Please try again with your destination city."
    
    def _update_search_session(self, criteria: Dict, guest_id: str) -> None:
        """Update search session with extracted criteria"""
        try:
            city = criteria.get('city')
            check_in = criteria.get('check_in')
            check_out = criteria.get('check_out')
            adults = criteria.get('adults', 2)
            
            if city and check_in and check_out:
                store_search_session(guest_id, city, check_in, check_out, adults)
                print(f"✅ Search session stored: {city}, {check_in} to {check_out}, {adults} adults")
            else:
                print(f"⚠️ Insufficient data for session storage")
                
        except Exception as e:
            print(f"❌ Session update failed: {e}")

# Create the discovery agent instance
discovery_agent = DiscoveryAgent()

@tool
def discovery_agent_tool(user_input: str, conversation_context: str = "", guest_id: str = "") -> str:
    """
    🔍 DISCOVERY AGENT - Hotel Finder Expert
    
    Following agent_workflow.md architecture for hotel discovery workflows.
    
    AGENT'S JOB: "Help guest find the perfect hotel"
    
    WORKFLOW STEPS:
    1. 📝 Understand what guest wants (city, dates, budget)
    2. 🔎 Search for available hotels  
    3. 🎛️ Filter by preferences (price, amenities)
    4. ✅ Check availability for their dates
    5. 🏆 Show best 3-5 options with reasons
    
    ✅ HANDLES:
    • Hotel search and discovery workflows
    • Availability checking and filtering
    • Price range and preference matching
    
    ❌ ROUTES TO OTHER AGENTS:
    • Room-specific questions → Room Intelligence Agent
    • Hotel facility questions → Hotel Intelligence Agent  
    • Booking operations → Booking Agent
    
    Args:
        user_input: Guest's hotel discovery request
        conversation_context: Recent conversation for context
        guest_id: Guest identifier for shared context
        
    Returns:
        Hotel discovery results with top 3-5 recommendations
    """
    
    try:
        # Import shared context system
        from memory.multi_agent_context import DiscoveryAgentContext
        from core.guest_id import get_guest_id
        
        # Get guest_id if not provided
        if not guest_id:
            guest_id = get_guest_id()
        
        # Initialize shared context manager
        context_mgr = DiscoveryAgentContext(guest_id)
        
        # Extract search criteria and update shared context FIRST
        search_criteria = context_mgr.extract_search_criteria(user_input)
        print(f"🎯 DISCOVERY AGENT: Extracted criteria = {search_criteria}")
        
        # Process with agent (original logic)
        result = discovery_agent.process(user_input, conversation_context)
        
        # Update shared context with search results after processing
        # NOTE: In full implementation, would parse the result to extract actual hotel data
        context_mgr.update_search_results([], search_criteria)
        
        return result
        
    except Exception as e:
        print(f"❌ Discovery Agent tool error: {e}")
        return "❌ Sorry, I encountered an error finding hotels. Please try again with your destination city."


# Export tools following agent_workflow.md architecture
DISCOVERY_AGENT_TOOLS = [
    # Main agent tool
    discovery_agent_tool,
    
    # Individual workflow tools (for direct access if needed)
    extract_search_criteria,
    search_hotels_by_city,
    filter_by_preferences, 
    check_availability,
    rank_and_present
]

print("🔍 Discovery Agent initialized - Following agent_workflow.md architecture")

def validate_hotel_business_rules(hotel_name: str, room_type: str, check_in_date: date, check_out_date: date, adults: int) -> Dict[str, Any]:
    """
    DISCOVERY AGENT BUSINESS RULE VALIDATOR
    
    Pre-validates hotel booking rules before offering to guests.
    Uses INTELLIGENT FUZZY MATCHING like booking_agent to ensure consistency.
    
    Args:
        hotel_name: Hotel name to validate
        room_type: Room type to check
        check_in_date: Check-in date
        check_out_date: Check-out date  
        adults: Number of adult guests
        
    Returns:
        Dict with validation results: {'valid': bool, 'reason': str, 'hotel_data': dict}
    """
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # INTELLIGENT FUZZY MATCHING - Same as booking_agent
            hotel_data = None
            
            # Try exact hotel name match first
            cursor.execute("""
                SELECT h.property_id, rt.room_type_id, h.hotel_name, rt.room_name, rt.max_occupancy,
                       h.min_stay_nights, h.max_stay_nights, h.advance_booking_days
                FROM hotels h 
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE LOWER(h.hotel_name) = LOWER(?) 
                AND h.is_active = 1
            """, (hotel_name,))
            
            hotel_matches = cursor.fetchall()
            
            if not hotel_matches:
                # Try fuzzy hotel name matching
                cursor.execute("""
                    SELECT h.property_id, rt.room_type_id, h.hotel_name, rt.room_name, rt.max_occupancy,
                           h.min_stay_nights, h.max_stay_nights, h.advance_booking_days
                    FROM hotels h 
                    JOIN room_types rt ON h.property_id = rt.property_id
                    WHERE LOWER(h.hotel_name) LIKE LOWER(?) 
                    AND h.is_active = 1
                """, (f"%{hotel_name}%",))
                
                hotel_matches = cursor.fetchall()
            
            if not hotel_matches:
                return {'valid': False, 'reason': 'Hotel not found', 'hotel_data': None}
            
            # Now find matching room type using intelligent fuzzy matching
            for match in hotel_matches:
                property_id, room_type_id, validated_hotel_name, room_name, max_occupancy, min_stay_nights, max_stay_nights, advance_booking_days = match
                
                # INTELLIGENT ROOM MATCHING - Same patterns as booking_agent
                room_match = False
                
                # 1. Exact match
                if room_type.lower() == room_name.lower():
                    room_match = True
                
                # 2. Partial match (context contains part of DB name)
                elif room_type.lower() in room_name.lower():
                    room_match = True
                
                # 3. First word match
                elif room_type.split()[0].lower() == room_name.split()[0].lower():
                    room_match = True
                
                # 4. Remove common suffixes and try again
                elif room_type.lower().replace(' room', '') == room_name.lower().replace(' room', ''):
                    room_match = True
                
                if room_match:
                    hotel_data = match
                    break
            
            if not hotel_data:
                return {'valid': False, 'reason': f'Room type "{room_type}" not found at {hotel_name}', 'hotel_data': None}
            
            property_id, room_type_id, validated_hotel_name, validated_room_name, max_occupancy, min_stay_nights, max_stay_nights, advance_booking_days = hotel_data
            
            # Calculate stay details
            nights = (check_out_date - check_in_date).days
            today = datetime.now().date()
            days_ahead = (check_in_date - today).days
            
            # BUSINESS RULE VALIDATION 1: ROOM CAPACITY
            if adults > max_occupancy:
                return {
                    'valid': False, 
                    'reason': f'Room capacity exceeded: {adults} guests requested, {max_occupancy} maximum',
                    'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                }
            
            # BUSINESS RULE VALIDATION 2: MINIMUM STAY
            if nights < min_stay_nights:
                return {
                    'valid': False,
                    'reason': f'Minimum stay not met: {nights} nights requested, {min_stay_nights} minimum required',
                    'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                }
            
            # BUSINESS RULE VALIDATION 3: MAXIMUM STAY  
            if nights > max_stay_nights:
                return {
                    'valid': False,
                    'reason': f'Maximum stay exceeded: {nights} nights requested, {max_stay_nights} maximum allowed',
                    'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                }
            
            # BUSINESS RULE VALIDATION 4: ADVANCE BOOKING
            if days_ahead < advance_booking_days:
                if advance_booking_days == 0 and days_ahead < 0:
                    return {
                        'valid': False,
                        'reason': f'Past date booking not allowed: Check-in {check_in_date} is in the past',
                        'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                    }
                elif advance_booking_days > 0:
                    return {
                        'valid': False,
                        'reason': f'Advance booking required: {advance_booking_days} days minimum, booking {days_ahead} days ahead',
                        'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                    }
            
            # BUSINESS RULE VALIDATION 5: CURRENT PRICING AVAILABLE
            cursor.execute("""
                SELECT current_price 
                FROM room_inventory 
                WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
            """, (property_id, room_type_id, check_in_date.strftime('%Y-%m-%d')))
            
            price_result = cursor.fetchone()
            if not price_result or price_result[0] <= 0:
                return {
                    'valid': False,
                    'reason': f'Pricing not available: Hotel has not set current rates for {check_in_date}',
                    'hotel_data': {'hotel_name': validated_hotel_name, 'room_name': validated_room_name}
                }
            
            # All validations passed
            return {
                'valid': True,
                'reason': 'All business rules satisfied',
                'hotel_data': {
                    'property_id': property_id,
                    'room_type_id': room_type_id,
                    'hotel_name': validated_hotel_name,
                    'room_name': validated_room_name,
                    'max_occupancy': max_occupancy,
                    'min_stay_nights': min_stay_nights,
                    'max_stay_nights': max_stay_nights,
                    'advance_booking_days': advance_booking_days,
                    'current_price': price_result[0],
                    'nights': nights,
                    'days_ahead': days_ahead
                }
            }
            
    except Exception as e:
        return {'valid': False, 'reason': f'Validation error: {str(e)}', 'hotel_data': None} 
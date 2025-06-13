# 🎯 Ella Agent Workflow Architecture

## Overview: Simple & Clear Hotel Assistant

**Ella's Job**: Help people find hotels, understand rooms, and make bookings.

**How Ella Works**: 
1. 👂 Listen to what guests want (Intent Detection)
2. 🎯 Pick the right expert (Agent Routing) 
3. 🔧 Expert does the work (Workflow Execution)
4. 💬 Give a helpful answer (Response)

---

## 🏗️ System Architecture

```
Guest Question 
     ↓
🧠 Main Ella (Intent Detection)
     ↓
🎯 Route to Specialist Agent
     ↓  
🔧 Agent uses Tools to solve
     ↓
💬 Friendly Response
```

---

## 📋 Level 1: Main System (Intent Detective)

### **Ella's Main Job**: *"What does the guest really want?"*

**Simple Intent Categories:**
- 🔍 **"Find me a hotel"** → Discovery Agent
- 🛏️ **"Tell me about rooms"** → Room Intelligence Agent  
- 🏨 **"Tell me about the hotel"** → Hotel Intelligence Agent
- 📋 **"Help me book/manage"** → Booking Agent

### **System Prompt (Main Ella)**
```
You are Ella, a helpful hotel assistant. Your ONLY job is to understand what guests want and send them to the right expert.

LISTEN FOR THESE INTENTS:

🔍 HOTEL DISCOVERY (Finding Hotels):
- Keywords: "find hotel", "search", "where to stay", "hotel options"
- Examples: "Find me a hotel in KL", "Hotels near KLCC"
- Action: Route to Discovery Agent

🛏️ ROOM INFORMATION (About Rooms):  
- Keywords: "room", "breakfast", "amenities", "what's included"
- Examples: "Does room have breakfast?", "What's in deluxe room?"
- Action: Route to Room Intelligence Agent

🏨 HOTEL INFORMATION (About Hotels):
- Keywords: "hotel facilities", "hotel details", "contact", "address"  
- Examples: "Does hotel have pool?", "Hotel phone number?"
- Action: Route to Hotel Intelligence Agent

📋 BOOKING OPERATIONS (Reservations):
- Keywords: "book", "reserve", "check booking", "cancel"
- Examples: "Book this room", "Check my booking"
- Action: Route to Booking Agent

ROUTING RULES:
✅ Always pick ONE primary intent
✅ Pass full conversation context to chosen agent
✅ If unclear, ask: "Do you want to find hotels, learn about rooms, or make a booking?"
❌ Never try to answer directly - always route to experts
```

---

## 🔍 Level 2A: Discovery Agent (Hotel Finder)

### **Agent's Job**: *"Help guest find the perfect hotel"*

**Workflow Steps:**
1. 📝 Understand what guest wants (city, dates, budget)
2. 🔎 Search for available hotels  
3. 🎛️ Filter by preferences (price, amenities)
4. ✅ Check availability for their dates
5. 🏆 Show best 3-5 options with reasons

### **Agent Prompt**
```
You are the Discovery Agent. Your job: Find perfect hotels for guests.

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
❌ Answer room-specific questions (send to Room Agent)
```

### **Discovery Agent Tools**
```python
@tool
def extract_search_criteria(user_query: str) -> str:
    """Extract: city, dates, adults, budget, preferences"""
    
@tool  
def search_hotels_by_city(city: str, min_rating: int = 0) -> str:
    """Find: all hotels in specified city"""
    
@tool
def filter_by_preferences(hotels_data: str, price_range: str = "", amenities: str = "") -> str:
    """Filter: hotels by guest preferences"""
    
@tool
def check_availability(hotel_list: str, check_in: str, check_out: str, adults: int) -> str:
    """Verify: room availability for dates"""
    
@tool
def rank_and_present(available_hotels: str, criteria: str) -> str:
    """Present: top 3-5 hotels with reasoning"""
```

---

## 🛏️ Level 2B: Room Intelligence Agent (Room Expert)

### **Agent's Job**: *"Tell guests everything about rooms"*

**Workflow Steps:**
1. 🎯 Identify which room guest is asking about
2. 📝 Get room details and amenities
3. 🍳 Check breakfast and meal policies  
4. 💰 Show pricing options
5. 📊 Compare with other rooms if needed

### **Agent Prompt**
```
You are the Room Intelligence Agent. Your job: Answer ALL room questions.

WORKFLOW (Always follow this order):
1. IDENTIFY: Which specific room are they asking about?
2. DETAILS: Get room amenities and features
3. BREAKFAST: Always check breakfast policy  
4. PRICING: Show pricing for the room
5. COMPARE: If multiple rooms, compare options

YOUR TOOLS:
• identify_room_type - Find specific room by name/hotel
• get_room_amenities - All room features and amenities
• check_breakfast_policy - Breakfast inclusion (YES/NO/RM50perpax)
• get_room_pricing - Price per night 
• compare_room_options - Side-by-side room comparison

BREAKFAST POLICY RESPONSES:
• "YES" → "Breakfast is included at no extra charge"
• "NO" → "This hotel doesn't offer breakfast"  
• "RM50perpax" → "Breakfast available for RM50 per person per night"

ALWAYS:
✅ Include breakfast policy in room descriptions
✅ Mention bed type and view type
✅ Show room price clearly
✅ Ask if they want to book or see other rooms

NEVER:
❌ Answer hotel-wide questions (send to Hotel Agent)
❌ Handle bookings (send to Booking Agent)
❌ Recommend hotels (send to Discovery Agent)
```

### **Room Intelligence Tools**
```python
@tool
def identify_room_type(hotel_name: str, room_query: str) -> str:
    """Find: specific room type by hotel and description"""
    
@tool
def get_room_amenities(hotel_name: str, room_name: str) -> str:
    """Get: all amenities, features, bed type, view type"""
    
@tool  
def check_breakfast_policy(hotel_name: str, room_name: str = None) -> str:
    """Check: breakfast inclusion policy (YES/NO/RMXXperpax)"""
    
@tool
def get_room_pricing(hotel_name: str, room_name: str) -> str:
    """Get: room price per night"""
    
@tool
def compare_room_options(hotel_name: str, room_list: str) -> str:
    """Compare: multiple rooms side by side"""
```

---

## 🏨 Level 2C: Hotel Intelligence Agent (Hotel Expert)

### **Agent's Job**: *"Tell guests everything about the hotel itself"*

**Workflow Steps:**
1. 🏨 Identify the specific hotel
2. 📋 Get hotel details and facilities
3. 📜 Check hotel policies
4. 📞 Provide contact information
5. 🌟 Present complete hotel profile

### **Agent Prompt**
```
You are the Hotel Intelligence Agent. Your job: Answer ALL hotel questions.

WORKFLOW (Always follow this order):
1. IDENTIFY: Which hotel are they asking about?
2. PROFILE: Get basic hotel information
3. FACILITIES: List hotel amenities (pool, gym, spa, etc.)
4. POLICIES: Check-in/out times, pet policy, etc.
5. CONTACT: Phone, email, address information

YOUR TOOLS:
• identify_hotel - Find hotel by name or description
• get_hotel_profile - Basic details (rating, location, description)
• get_hotel_facilities - Pool, gym, spa, restaurant, wifi
• get_hotel_policies - Check-in times, pet policy, cancellation
• get_contact_info - Phone, email, address

ALWAYS:
✅ Start with hotel name and star rating
✅ List key facilities (pool, gym, restaurant)
✅ Include contact information
✅ Mention check-in/check-out times if asked

NEVER:
❌ Answer room-specific questions (send to Room Agent)
❌ Handle bookings (send to Booking Agent)  
❌ Recommend other hotels (send to Discovery Agent)
```

### **Hotel Intelligence Tools**
```python
@tool
def identify_hotel(hotel_query: str, city: str = "") -> str:
    """Find: specific hotel by name or description"""
    
@tool
def get_hotel_profile(hotel_name: str) -> str:
    """Get: basic hotel info (rating, location, description)"""
    
@tool
def get_hotel_facilities(hotel_name: str) -> str:
    """Get: hotel amenities (pool, gym, spa, restaurant, wifi)"""
    
@tool
def get_hotel_policies(hotel_name: str) -> str:
    """Get: check-in times, policies, rules"""
    
@tool
def get_contact_info(hotel_name: str) -> str:
    """Get: phone, email, address"""
```

---

## 📋 Level 2D: Booking Agent (Booking Expert)

### **Agent's Job**: *"Handle all booking operations"*

**Workflow Steps:**
1. 🎯 Understand booking operation needed
2. ✅ Validate booking details
3. 💳 Process the booking operation
4. 📧 Provide confirmation details
5. 📋 Offer next steps

### **Agent Prompt**
```
You are the Booking Agent. Your job: Handle ALL booking operations.

WORKFLOW (Always follow this order):
1. OPERATION: What booking action do they need?
2. VALIDATE: Check all required details are present
3. EXECUTE: Perform the booking operation
4. CONFIRM: Provide booking reference and details
5. NEXT: Offer relevant next steps

YOUR TOOLS:
• create_booking - Make new reservation
• check_booking_status - Look up existing booking
• modify_booking - Change booking details
• cancel_booking - Cancel reservation
• get_guest_bookings - List all bookings for guest

BOOKING OPERATIONS:
• NEW BOOKING: Need hotel, room, dates, guest details
• CHECK STATUS: Need booking reference or guest phone
• MODIFY: Need booking reference + what to change
• CANCEL: Need booking reference + confirmation

ALWAYS:
✅ Confirm booking details before processing
✅ Provide booking reference number
✅ Mention cancellation policy
✅ Ask if they need anything else

NEVER:
❌ Book without confirming all details
❌ Cancel without double-checking
❌ Answer room/hotel questions (send to other agents)
```

---

## 🔧 Implementation Plan

### **Phase 1: Room Intelligence Agent** (Start Here)
- ✅ We already have breakfast_policy working
- Consolidate room tools into Room Intelligence Agent
- Create clear workflow for room queries
- Test with room amenity questions

### **Phase 2: Hotel Intelligence Agent**  
- Consolidate hotel-level tools
- Create clear workflow for hotel information
- Test with hotel facility questions

### **Phase 3: Discovery Agent**
- Refactor search tools into discovery workflow
- Implement availability checking
- Test end-to-end hotel search

### **Phase 4: Main Intent Detection**
- Create intent detection system
- Implement agent routing
- Test complete workflow

### **Phase 5: Integration & Testing**
- Full system testing
- Performance optimization
- Agent communication refinement

---

## 🎯 Success Metrics

**Each Agent Should:**
- ✅ Handle 100% of queries in their domain
- ✅ Never cross into other agent territories  
- ✅ Use tools in logical workflow order
- ✅ Provide complete, helpful responses
- ✅ Route complex queries appropriately

**Guest Experience:**
- ✅ Always get relevant, accurate answers
- ✅ Never feel confused about who's helping
- ✅ Clear next steps provided
- ✅ Fast response times maintained 
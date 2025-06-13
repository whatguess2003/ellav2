#!/usr/bin/env python3
"""
🎯 LEAN SHARED CONTEXT EXAMPLE
Demonstrates how agents coordinate through focused, non-bloated shared context

EXAMPLE SCENARIO: "Book deluxe room at Grand Hyatt KL with breakfast for 2 nights"
"""

import json
from memory.multi_agent_context import MultiAgentContext

def demonstrate_lean_context():
    """Show how lean context enables perfect agent coordination"""
    
    guest_id = "guest_123"
    context = MultiAgentContext(guest_id)
    
    print("🎯 LEAN SHARED CONTEXT DEMONSTRATION")
    print("=" * 50)
    
    # ============================================================================
    # STEP 1: DISCOVERY AGENT contributes essential search coordination data
    # ============================================================================
    print("\n1. 🔍 DISCOVERY AGENT updates search_context:")
    
    discovery_updates = {
        "search_context": {
            "destination": "Kuala Lumpur",       # ✅ Needed by all agents
            "check_in": "2024-06-15",           # ✅ Critical for pricing/booking
            "check_out": "2024-06-17",          # ✅ Critical for pricing/booking
            "adults": 2,                        # ✅ Affects services & booking
            "rooms": 1,                         # ✅ Critical for calculations
            "hotels_found": 8,                  # ✅ Status for other agents
            "selected_hotel": "Grand Hyatt Kuala Lumpur",  # ✅ Needed by all
            "selected_property_id": "GHKL001",  # ✅ Critical for booking
            "search_status": "completed"        # ✅ Workflow coordination
            
            # ❌ NOT STORED: Full hotel list (bloat), detailed search criteria, 
            #    search history, filters applied, etc.
        }
    }
    
    context.update_context(discovery_updates)
    print(f"   ✅ Stored: {list(discovery_updates['search_context'].keys())}")
    print(f"   🚫 Avoided bloat: Full hotel details, search history, filters")
    
    # ============================================================================
    # STEP 2: ROOM INTELLIGENCE AGENT contributes essential room coordination data  
    # ============================================================================
    print("\n2. 🛏️ ROOM INTELLIGENCE AGENT updates room_context:")
    
    room_updates = {
        "room_context": {
            "room_type": "Deluxe King",         # ✅ Needed for booking
            "room_type_id": "GHKL_DLX_KING",   # ✅ Critical for booking
            "bed_configuration": "King Bed",    # ✅ Affects service planning
            "max_occupancy": 2,                 # ✅ Important for services
            "base_price_per_night": 400,       # ✅ CRITICAL for booking agent
            "currency": "RM"                   # ✅ For pricing coordination
            
            # ❌ NOT STORED: Room amenities list (bloat), room photos, 
            #    detailed features, view descriptions, etc.
        }
    }
    
    context.update_context(room_updates)
    print(f"   ✅ Stored: {list(room_updates['room_context'].keys())}")
    print(f"   🚫 Avoided bloat: Full amenities, photos, detailed features")
    
    # ============================================================================
    # STEP 3: SERVICE AGENT contributes essential service coordination data
    # ============================================================================
    print("\n3. 🍽️ SERVICE AGENT updates service_context:")
    
    service_updates = {
        "service_context": {
            "breakfast": {
                "available": True,              # ✅ Boolean for booking options
                "included": False,              # ✅ Critical for pricing
                "cost_per_person": 50,          # ✅ CRITICAL for booking
                "policy": "RM50 per person"     # ✅ Brief policy for booking
            },
            "services_requested": ["breakfast"], # ✅ List for booking
            "total_service_cost": 100           # ✅ CRITICAL (50 x 2 people)
            
            # ❌ NOT STORED: Full breakfast menu (bloat), spa catalogs,
            #    detailed service descriptions, operating hours, etc.
        }
    }
    
    context.update_context(service_updates)
    print(f"   ✅ Stored: Essential service coordination data")
    print(f"   🚫 Avoided bloat: Full menus, service catalogs, detailed descriptions")
    
    # ============================================================================
    # STEP 4: BOOKING AGENT reads all contexts and calculates total
    # ============================================================================
    print("\n4. 📋 BOOKING AGENT reads shared context and calculates:")
    
    # Read coordination data from all agents
    current_context = context.get_context()
    search_ctx = current_context["search_context"]
    room_ctx = current_context["room_context"] 
    service_ctx = current_context["service_context"]
    
    # Calculate using coordination data
    nights = 2  # From check_in/check_out dates
    room_cost = room_ctx["base_price_per_night"] * nights * search_ctx["rooms"]  # 400 * 2 * 1 = 800
    service_cost = service_ctx["total_service_cost"] * nights  # 100 * 2 = 200
    subtotal = room_cost + service_cost  # 800 + 200 = 1000
    tax = subtotal * 0.06  # 6% tax = 60
    total = subtotal + tax  # 1060
    
    booking_updates = {
        "booking_context": {
            "booking_intent": True,
            "booking_stage": "pricing",
            "room_cost": room_cost,           # ✅ Calculated from room context
            "service_cost": service_cost,     # ✅ Calculated from service context  
            "tax_amount": tax,                # ✅ Calculated
            "total_cost": total               # ✅ Final coordination result
            
            # ❌ NOT STORED: Detailed billing breakdown, payment methods,
            #    promotional codes, booking history, etc.
        }
    }
    
    context.update_context(booking_updates)
    
    print(f"   💰 Room Cost: RM{room_cost} (from room_context)")
    print(f"   🍽️ Service Cost: RM{service_cost} (from service_context)")
    print(f"   💸 Tax: RM{tax}")
    print(f"   🎯 TOTAL: RM{total}")
    print(f"   ✅ Perfect coordination through lean context!")
    
    # ============================================================================
    # STEP 5: Show final lean context size
    # ============================================================================
    print("\n5. 📊 FINAL CONTEXT SIZE & EFFICIENCY:")
    
    final_context = context.get_context()
    context_json = json.dumps(final_context, indent=2)
    
    print(f"   📏 Total context size: {len(context_json)} characters")
    print(f"   🎯 Essential coordination data only")
    print(f"   🚫 Zero bloat - no unnecessary details")
    print(f"   ⚡ Fast agent coordination")
    print(f"   🤝 Perfect inter-agent data sharing")
    
    # Show what each agent contributed
    print(f"\n   🔍 Discovery: destination, dates, hotel selection")
    print(f"   🛏️ Room: room type, pricing")  
    print(f"   🍽️ Service: breakfast cost")
    print(f"   📋 Booking: total calculation")
    
    return final_context

if __name__ == "__main__":
    demonstrate_lean_context() 
#!/usr/bin/env python3
"""
📋 BOOKING AGENT - Simple Booking Confirmation Handler
Triggered only when booking context is complete. Summarizes and asks for confirmation.

SIMPLE WORKFLOW:
1. 🔍 Check if booking context slots are filled (hotel, room, dates, pricing)
2. 📋 Summarize booking details for guest confirmation  
3. ❓ Ask: "Ready to book?" (Yes/No)
4. ✅ YES → Proceed to booking_management
5. ❌ NO → Clarify details or fallback to discovery_agent
"""

from langchain_core.tools import tool
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, date, timedelta

from core.guest_id import get_guest_id
import sqlite3







@tool
def extract_guest_details(user_input: str, guest_id: str = "") -> str:
    """
    Extract guest details (name, email, phone) from user input and store in context.
    
    Args:
        user_input: User message containing guest details
        guest_id: Guest identifier
        
    Returns:
        Status message about extracted details
    """
    print(f"👤 EXTRACTING GUEST DETAILS")
    
    try:
        import re
        
        # Get guest_id if not provided
        if not guest_id:
            guest_id = get_guest_id()
        
        # Extract details using regex patterns
        name_patterns = [
            r'(?:my name is|i am|i\'m|name:?)\s+([a-zA-Z\s]+?)(?:\s*,|\s*$|\s+email|\s+phone|\s+\+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # FirstName LastName pattern
        ]
        
        email_patterns = [
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'(?:email:?)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        phone_patterns = [
            r'(\+?6?0?1[0-9\-\s]{8,11})',  # Malaysian phone numbers
            r'(?:phone:?|tel:?|call:?)\s*(\+?[\d\-\s\(\)]{8,15})',
            r'(\+[\d\-\s\(\)]{8,15})'
        ]
        
        # Extract name
        guest_name = ""
        for pattern in name_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                guest_name = match.group(1).strip()
                # Clean up common issues
                guest_name = re.sub(r'\s+', ' ', guest_name)  # Multiple spaces
                guest_name = guest_name.replace(',', '').strip()
                break
        
        # Extract email
        guest_email = ""
        for pattern in email_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                guest_email = match.group(1).strip()
                break
        
        # Extract phone
        guest_phone = ""
        for pattern in phone_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                guest_phone = match.group(1).strip()
                # Clean up phone number
                guest_phone = re.sub(r'[\s\-\(\)]', '', guest_phone)
                break
        
        # Store in context
        from memory.multi_agent_context import MultiAgentContext
        context = MultiAgentContext(guest_id)
        
        booking_updates = {}
        if guest_name:
            booking_updates["guest_name"] = guest_name
        if guest_email:
            booking_updates["guest_email"] = guest_email
        if guest_phone:
            booking_updates["guest_phone"] = guest_phone
        
        if booking_updates:
            context.update_section("booking_context", booking_updates)
            print(f"📝 Stored guest details: {booking_updates}")
        
        # Return status
        extracted_items = []
        if guest_name:
            extracted_items.append(f"Name: {guest_name}")
        if guest_email:
            extracted_items.append(f"Email: {guest_email}")
        if guest_phone:
            extracted_items.append(f"Phone: {guest_phone}")
        
        if extracted_items:
            return f"✅ Extracted guest details: {', '.join(extracted_items)}"
        else:
            return """
❌ Could not extract guest details. Please provide them in this format:
"My name is John Smith, email john@email.com, phone +60123456789"
"""
        
    except Exception as e:
        print(f"❌ Guest details extraction error: {e}")
        return f"Error extracting guest details: {str(e)}"

@tool
def check_booking_context_ready(guest_id: str = "") -> str:
    """
    Check if all required booking slots are filled in context.
    
    Args:
        guest_id: Guest identifier for context access
        
    Returns:
        JSON string indicating if booking context is ready
    """
    print(f"🔍 CHECKING BOOKING CONTEXT READINESS")
    
    try:
        # Import shared context system
        from memory.multi_agent_context import MultiAgentContext
        
        # Get guest_id if not provided
        if not guest_id:
            guest_id = get_guest_id()
        
        # Read from shared context
        context = MultiAgentContext(guest_id)
        search_context = context.get_section("search_context")
        room_context = context.get_section("room_context")
        service_context = context.get_section("service_context")
        
        # VALIDATE SPECIFIC ROOM AVAILABILITY
        available_rooms = room_context.get("available_rooms", [])
        requested_room_type = room_context.get("room_type", "")
        
        # Check if the specific requested room is available
        room_available = False
        room_has_pricing = False
        if available_rooms and requested_room_type:
            for room in available_rooms:
                if room.get("room_type", "").lower() == requested_room_type.lower():
                    room_available = True
                    room_has_pricing = room.get("price", 0) > 0
                    break
        
        # Get booking context for guest details validation
        booking_context = context.get_section("booking_context")
        
        # Check required slots with SPECIFIC room validation
        required_slots = {
            "hotel": search_context.get("selected_hotel", ""),
            "room_type": room_context.get("room_type", ""),
            "check_in": search_context.get("check_in", ""),
            "check_out": search_context.get("check_out", ""),
            "adults": search_context.get("adults", 0),
            "room_available": room_available,  # SPECIFIC room must be available
            "room_pricing": room_has_pricing,  # SPECIFIC room must have pricing
            "service_pricing": bool(service_context.get("services_requested", []) or service_context.get("breakfast", {}).get("available", False)),
            "guest_name": booking_context.get("guest_name", ""),
            "guest_email": booking_context.get("guest_email", "")
        }
        
        # Check if all required slots are filled
        missing_slots = []
        for slot, value in required_slots.items():
            if not value:
                missing_slots.append(slot)
        
        is_ready = len(missing_slots) == 0
        
        return json.dumps({
            "context_ready": is_ready,
            "missing_slots": missing_slots,
            "available_slots": {k: v for k, v in required_slots.items() if v},
            "message": "Ready for booking" if is_ready else f"Missing: {', '.join(missing_slots)}"
        })
        
    except Exception as e:
        print(f"❌ Context check error: {e}")
        return json.dumps({
            "context_ready": False,
            "error": str(e)
        })

@tool
def create_booking_summary(guest_id: str = "") -> str:
    """
    Create a comprehensive booking summary with REAL-TIME DATABASE VALIDATION.
    
    CRITICAL VALIDATIONS PERFORMED:
    1. Real-time inventory check against room_inventory table
    2. Hotel and room type validation in database
    3. Current pricing from database (not stale context)
    4. Complete availability verification for entire stay period
    
    Args:
        guest_id: Guest identifier for context access
        
    Returns:
        Formatted booking summary string or error message with real-time validation
    """
    print(f"📋 CREATING BOOKING SUMMARY")
    
    try:
        # Import shared context system
        from memory.multi_agent_context import MultiAgentContext
        
        # Get guest_id if not provided
        if not guest_id:
            guest_id = get_guest_id()
        
        # Read from shared context
        context = MultiAgentContext(guest_id)
        search_context = context.get_section("search_context")
        room_context = context.get_section("room_context")
        service_context = context.get_section("service_context")
        
        # Extract booking details
        hotel_name = search_context.get("selected_hotel", "")
        room_type = room_context.get("room_type", "")
        check_in = search_context.get("check_in", "")
        check_out = search_context.get("check_out", "")
        adults = search_context.get("adults", 1)
        
        # CRITICAL: REAL-TIME DATABASE INVENTORY VALIDATION
        # Step 1: Get hotel and room type IDs from database with INTELLIGENT MATCHING
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                
                # FIRST: Try exact match
                cursor.execute("""
                    SELECT h.property_id, rt.room_type_id, rt.base_price_per_night, h.hotel_name, rt.room_name, rt.max_occupancy
                    FROM hotels h 
                    JOIN room_types rt ON h.property_id = rt.property_id
                    WHERE h.hotel_name = ? AND rt.room_name = ?
                """, (hotel_name, room_type))
                
                hotel_room_data = cursor.fetchone()
                
                # SECOND: If no exact match, try FUZZY MATCHING (database as source of truth)
                if not hotel_room_data:
                    print(f"🔍 Exact match failed. Trying fuzzy matching for: {hotel_name} - {room_type}")
                    
                    # Try fuzzy hotel name matching
                    cursor.execute("""
                        SELECT h.property_id, rt.room_type_id, rt.base_price_per_night, h.hotel_name, rt.room_name, rt.max_occupancy
                        FROM hotels h 
                        JOIN room_types rt ON h.property_id = rt.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?) 
                        AND (
                            LOWER(rt.room_name) LIKE LOWER(?) OR
                            LOWER(rt.room_name) LIKE LOWER(?) OR
                            LOWER(rt.room_name) LIKE LOWER(?) OR
                            LOWER(rt.room_name) LIKE LOWER(?)
                        )
                        LIMIT 1
                    """, (
                        f"%{hotel_name}%",
                        f"%{room_type}%",
                        f"{room_type}%",
                        f"%{room_type.split()[0]}%",  # First word match
                        f"%{room_type.replace(' Room', '')}%"  # Remove "Room" suffix
                    ))
                    
                    hotel_room_data = cursor.fetchone()
                    
                    if hotel_room_data:
                        actual_hotel_name = hotel_room_data[3]
                        actual_room_name = hotel_room_data[4]
                        print(f"✅ Fuzzy match found: {actual_hotel_name} - {actual_room_name}")
                        
                        # UPDATE CONTEXT WITH DATABASE TRUTH
                        hotel_name = actual_hotel_name
                        room_type = actual_room_name
                
                # FINAL CHECK: Still no match means invalid request
                if not hotel_room_data:
                    # Get available options from database to suggest alternatives
                    cursor.execute("""
                        SELECT h.hotel_name, rt.room_name
                        FROM hotels h 
                        JOIN room_types rt ON h.property_id = rt.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?)
                        LIMIT 3
                    """, (f"%{hotel_name.split()[0]}%",))
                    
                    alternatives = cursor.fetchall()
                    alt_text = ""
                    if alternatives:
                        alt_text = "\n\n🏨 Available options:\n" + "\n".join([f"• {alt[0]} - {alt[1]}" for alt in alternatives])
                    
                    return f"""
❌ ROOM TYPE NOT FOUND

The room type "{room_type}" is not available at {hotel_name}.
{alt_text}

Please try:
• Different room type from available options above
• Different hotel
• Let me search for similar rooms

Would you like me to search for available rooms at this hotel?
"""
                
                property_id, room_type_id, base_price, validated_hotel_name, validated_room_name, max_occupancy = hotel_room_data
                
                # ENFORCE DATABASE AS SOURCE OF TRUTH
                hotel_name = validated_hotel_name
                room_type = validated_room_name
                
                print(f"✅ Database validation passed: {hotel_name} - {room_type}")
                
                # BUSINESS RULE VALIDATION 1: ROOM CAPACITY vs GUEST COUNT
                if adults > max_occupancy:
                    return f"""
❌ ROOM CAPACITY EXCEEDED

The {room_type} at {hotel_name} has a maximum occupancy of {max_occupancy} guest{'s' if max_occupancy != 1 else ''}.

You requested accommodation for {adults} adult{'s' if adults != 1 else ''}.

Please:
• Reduce the number of guests to {max_occupancy} or fewer
• Select a different room type with higher capacity
• Book multiple rooms for your group

Would you like me to search for rooms with higher capacity?
"""
        
        except Exception as e:
            return f"""
❌ DATABASE VALIDATION ERROR

Unable to validate booking details against our system.

Please try again or contact support.
Error: {str(e)}
"""
        
        # Step 2: REAL-TIME INVENTORY CHECK for the entire stay period
        try:
            from datetime import datetime, timedelta
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            # Calculate nights and booking lead time
            nights = (check_out_date - check_in_date).days
            today = datetime.now().date()
            days_ahead = (check_in_date - today).days
            
            # BUSINESS RULE VALIDATION 2: STAY REQUIREMENTS
            # Get hotel stay policies
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT min_stay_nights, max_stay_nights, advance_booking_days
                    FROM hotels 
                    WHERE property_id = ?
                """, (property_id,))
                
                stay_policy = cursor.fetchone()
                if stay_policy:
                    min_stay_nights, max_stay_nights, advance_booking_days = stay_policy
                    
                    # Validate minimum stay
                    if nights < min_stay_nights:
                        return f"""
❌ MINIMUM STAY REQUIREMENT NOT MET

{hotel_name} requires a minimum stay of {min_stay_nights} night{'s' if min_stay_nights != 1 else ''}.

Your booking is for {nights} night{'s' if nights != 1 else ''} ({check_in} to {check_out}).

Please:
• Extend your stay to at least {min_stay_nights} night{'s' if min_stay_nights != 1 else ''}
• Choose different dates that meet the minimum stay
• Select a different hotel with more flexible policies

Would you like me to help you find alternative dates or hotels?
"""
                    
                    # Validate maximum stay
                    if nights > max_stay_nights:
                        return f"""
❌ MAXIMUM STAY LIMIT EXCEEDED

{hotel_name} allows a maximum stay of {max_stay_nights} night{'s' if max_stay_nights != 1 else ''}.

Your booking is for {nights} night{'s' if nights != 1 else ''} ({check_in} to {check_out}).

Please:
• Reduce your stay to {max_stay_nights} night{'s' if max_stay_nights != 1 else ''} or fewer
• Split your stay across multiple bookings
• Select a different hotel for extended stays

Would you like me to help you adjust your booking dates?
"""
                    
                    # BUSINESS RULE VALIDATION 3: ADVANCE BOOKING REQUIREMENTS
                    if days_ahead < advance_booking_days:
                        if advance_booking_days == 0:
                            # Same-day booking allowed, but check if it's past check-in time
                            if days_ahead < 0:
                                return f"""
❌ PAST DATE BOOKING NOT ALLOWED

You cannot book for past dates.

Check-in date: {check_in}
Today's date: {today}

Please select a future date for your stay.
"""
                        else:
                            return f"""
❌ ADVANCE BOOKING REQUIREMENT NOT MET

{hotel_name} requires bookings to be made at least {advance_booking_days} day{'s' if advance_booking_days != 1 else ''} in advance.

Your check-in date: {check_in} (in {days_ahead} day{'s' if days_ahead != 1 else ''})
Required advance booking: {advance_booking_days} day{'s' if advance_booking_days != 1 else ''}

Please:
• Select a check-in date at least {advance_booking_days} day{'s' if advance_booking_days != 1 else ''} from today
• Choose a different hotel with more flexible booking policies
• Contact the hotel directly for same-day bookings

Would you like me to help you find alternative dates or hotels?
"""
            
            # Import booking management for availability check
            from .booking_tools.booking_management import BookingConfirmationManager
            booking_manager = BookingConfirmationManager()
            
            # Perform real-time availability check
            availability_result = booking_manager.check_availability(
                property_id, room_type_id, check_in_date, check_out_date, 1
            )
            
            if not availability_result.get('available', False):
                return f"""
❌ ROOM NO LONGER AVAILABLE

Real-time check shows "{room_type}" is no longer available at {hotel_name} for {check_in} to {check_out}.

Reason: {availability_result.get('message', 'Insufficient inventory')}

Please try:
• Different dates
• Different room type  
• Different hotel

Would you like me to search for alternatives?
"""
                
        except Exception as e:
            return f"""
❌ AVAILABILITY CHECK FAILED

Unable to verify real-time room availability.

Error: {str(e)}

Please try again or contact support.
"""
        
        # Step 3: Get current pricing from database (CURRENT_PRICE ONLY - NO FALLBACKS)
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                
                # Get current pricing for the check-in date - ONLY SOURCE OF TRUTH
                cursor.execute("""
                    SELECT current_price 
                    FROM room_inventory 
                    WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                """, (property_id, room_type_id, check_in))
                
                price_result = cursor.fetchone()
                if price_result and price_result[0] > 0:
                    room_price = price_result[0]
                    print(f"💰 Using current pricing: RM{room_price} from inventory")
                else:
                    # NO FALLBACKS - Hotel must update their pricing
                    return f"""
❌ PRICING NOT AVAILABLE

The hotel "{hotel_name}" has not updated their current pricing for {room_type} on {check_in}.

This means:
• Hotel needs to update their room rates
• Pricing system not configured for this date
• Room may not be available for booking

Please:
• Try a different date
• Contact the hotel directly
• Check back later after hotel updates pricing

Hotel management must configure current pricing in the system.
"""
                    
        except Exception as e:
            return f"""
❌ PRICING SYSTEM ERROR

Unable to retrieve current pricing from the hotel's system.

Error: {str(e)}

Please try again or contact support.
"""
        
        # Nights already calculated in validation section above
        
        # FETCH HOTEL POLICIES FROM DATABASE
        hotel_policies = {}
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT check_in_time, check_out_time, requires_prepayment, payment_policy,
                           cancellation_policy_json, cancellation_window_nights, cancellation_type
                    FROM hotels 
                    WHERE LOWER(hotel_name) LIKE LOWER(?) AND is_active = 1
                    LIMIT 1
                """, [f"%{hotel_name}%"])
                
                result = cursor.fetchone()
                if result:
                    check_in_time, check_out_time, requires_prepayment, payment_policy_json, cancellation_policy_json, cancellation_window_nights, cancellation_type = result
                    
                    # Parse payment policy JSON
                    payment_policy = {}
                    if payment_policy_json:
                        try:
                            payment_policy = json.loads(payment_policy_json)
                        except:
                            payment_policy = {}
                    
                    # Parse cancellation policy JSON or create default
                    cancellation_policy = ""
                    if cancellation_policy_json:
                        try:
                            cancellation_data = json.loads(cancellation_policy_json)
                            # Extract a readable policy from the JSON
                            if isinstance(cancellation_data, dict):
                                policy_parts = []
                                if cancellation_window_nights:
                                    policy_parts.append(f"Free cancellation up to {cancellation_window_nights} night{'s' if cancellation_window_nights != 1 else ''} before check-in")
                                if cancellation_data.get('fee_percentage'):
                                    policy_parts.append(f"Cancellation fee: {cancellation_data.get('fee_percentage')}%")
                                cancellation_policy = ". ".join(policy_parts) if policy_parts else "Standard cancellation policy applies"
                            else:
                                cancellation_policy = str(cancellation_data)
                        except:
                            if cancellation_window_nights:
                                cancellation_policy = f"Free cancellation up to {cancellation_window_nights} night{'s' if cancellation_window_nights != 1 else ''} before check-in"
                            else:
                                cancellation_policy = "Standard cancellation policy applies"
                    else:
                        if cancellation_window_nights:
                            cancellation_policy = f"Free cancellation up to {cancellation_window_nights} night{'s' if cancellation_window_nights != 1 else ''} before check-in"
                        else:
                            cancellation_policy = "Standard cancellation policy applies"
                    
                    hotel_policies = {
                        "check_in_time": check_in_time or "3:00 PM",
                        "check_out_time": check_out_time or "12:00 PM",
                        "tax_rate": 0.06,  # Standard Malaysian tax
                        "service_charge": 0.10,  # Standard service charge
                        "requires_prepayment": bool(requires_prepayment),
                        "payment_policy": payment_policy,
                        "cancellation_policy": cancellation_policy
                    }
                else:
                    # Fallback for unknown hotels
                    hotel_policies = {
                        "check_in_time": "3:00 PM",
                        "check_out_time": "12:00 PM",
                        "tax_rate": 0.06,
                        "service_charge": 0.10,
                        "requires_prepayment": False,
                        "payment_policy": {},
                        "cancellation_policy": "Free cancellation up to 1 night before check-in"
                    }
        except Exception as e:
            print(f"❌ Error fetching hotel policies: {e}")
            # Fallback defaults
            hotel_policies = {
                "check_in_time": "3:00 PM",
                "check_out_time": "12:00 PM",
                "tax_rate": 0.06,
                "service_charge": 0.10,
                "requires_prepayment": False,
                "payment_policy": {},
                "cancellation_policy": "Free cancellation up to 1 night before check-in"
            }
        
        # Get services if any
        services_requested = service_context.get("services_requested", [])
        breakfast_info = service_context.get("breakfast", {})
        breakfast_included = breakfast_info.get("available", False) or "breakfast" in str(services_requested).lower()
        breakfast_cost = breakfast_info.get("cost_per_person", 50)  # Get actual cost or default
        
        # DETAILED PRICING CALCULATION
        room_total = room_price * nights
        service_total = breakfast_cost * adults * nights if breakfast_included else 0
        subtotal = room_total + service_total
        
        # TAX SETTINGS - Get actual tax rate
        tax_rate = hotel_policies.get("tax_rate", 0.06)  # Default 6% or actual rate
        service_charge_rate = hotel_policies.get("service_charge", 0.10)  # 10% service charge
        
        # Calculate taxes and charges
        service_charge = subtotal * service_charge_rate
        government_tax = (subtotal + service_charge) * tax_rate
        total_tax = service_charge + government_tax
        total = subtotal + total_tax
        
        # VALIDATE COMPLETE PRICING
        if total <= 0:
            return f"""
❌ PRICING CALCULATION ERROR

There was an error calculating the total price for your booking. 

Please try:
• Refreshing room availability
• Selecting a different room type
• Contacting our support team

Would you like me to help you find alternative options?
"""
        
        # PAYMENT STATUS AND POLICY CHECK
        requires_prepayment = hotel_policies.get("requires_prepayment", False)
        payment_policy = hotel_policies.get("payment_policy", {})
        
        # Determine payment status and create payment section
        # Payment status is always UNPAID until actual payment is verified
        payment_status = "UNPAID"
        
        if requires_prepayment:
            payment_timing = "Prior to confirmation"
            payment_window_nights = payment_policy.get("payment_window_nights", 1)
            payment_methods = ", ".join(payment_policy.get("payment_methods", ["Credit Card"]))
            payment_notes = payment_policy.get("payment_notes", "Payment required before confirmation")
            
            payment_section = f"""
💳 PAYMENT REQUIRED BEFORE CONFIRMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  For this booking you have to make the payment first prior to confirmation
⏰ Payment Due: {payment_timing}
⏰ Payment Window: {payment_window_nights} night{'s' if payment_window_nights != 1 else ''} from booking
💰 Payment Methods: {payment_methods}
📝 Note: {payment_notes}
💸 Refund Policy: {payment_policy.get('refund_policy', 'Standard refund policy applies')}
"""
        else:
            payment_timing = "Prior to check-in"
            payment_notes = payment_policy.get("payment_notes", "Payment upon check-in at hotel")
            
            payment_section = f"""
💳 PAYMENT POLICY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Payment Due: {payment_timing}
💰 Payment Location: At hotel during check-in
💸 Refund Policy: {payment_policy.get('refund_policy', 'Standard refund policy applies')}
📝 Note: {payment_notes}
"""

        # CREATE COMPREHENSIVE BOOKING SUMMARY
        summary = f"""
📋 COMPREHENSIVE BOOKING SUMMARY

🏨 Hotel: {hotel_name}
🛏️ Room: {room_type}
📅 Dates: {check_in} to {check_out} ({nights} nights)
👥 Guests: {adults} adults

⏰ CHECK-IN/OUT TIMES:
• Check-in: {hotel_policies.get('check_in_time')}
• Check-out: {hotel_policies.get('check_out_time')}

💰 DETAILED PRICING:
Room Rate: RM{room_total:.2f} ({nights} nights × RM{room_price:.2f})"""
        
        if breakfast_included:
            summary += f"\nBreakfast: RM{service_total:.2f} ({adults} guests × {nights} nights × RM{breakfast_cost:.2f})"
        
        summary += f"""
Subtotal: RM{subtotal:.2f}
Service Charge ({service_charge_rate*100:.0f}%): RM{service_charge:.2f}
Government Tax ({tax_rate*100:.0f}%): RM{government_tax:.2f}
Total Taxes & Charges: RM{total_tax:.2f}
FINAL TOTAL: RM{total:.2f}
{payment_section}
📜 CANCELLATION POLICY:
{hotel_policies.get('cancellation_policy', 'Standard cancellation policy applies. Free cancellation up to 1 night before check-in.')}

🛡️ BOOKING TERMS:
• Payment Status: {payment_status}
• Valid ID required at check-in
• Rates include all applicable taxes and charges
• Subject to hotel terms and conditions

{"⚠️  IMPORTANT: For this booking you have to make the payment first prior to confirmation" if requires_prepayment else "✅ This booking can be confirmed immediately - payment upon check-in"}

Ready to {"initiate payment process" if requires_prepayment else "confirm this booking"}? Please say YES to proceed.
"""
        
        return summary.strip()
        
    except Exception as e:
        print(f"❌ Summary creation error: {e}")
        return f"Error creating booking summary: {str(e)}"

@tool
def process_booking_confirmation(user_response: str, guest_id: str = "") -> str:
    """
    Process guest's yes/no response to booking confirmation.
    
    Args:
        user_response: Guest's response (yes/no/clarify)
        guest_id: Guest identifier for context access
        
    Returns:
        Next action (book/clarify/search)
    """
    print(f"✅ PROCESSING BOOKING CONFIRMATION: {user_response}")
    
    try:
        response_lower = user_response.lower()
        
        # Check for YES responses
        if any(word in response_lower for word in ['yes', 'book', 'confirm', 'proceed', 'ok', 'yeah', 'sure']):
            print("👍 Guest confirmed booking - checking payment requirements")
            
            # Extract booking details from context
            from memory.multi_agent_context import MultiAgentContext
            context = MultiAgentContext(guest_id)
            search_context = context.get_section("search_context")
            room_context = context.get_section("room_context")
            booking_context = context.get_section("booking_context")
            
            # Get guest details
            guest_name = booking_context.get("guest_name", "")
            guest_email = booking_context.get("guest_email", "")
            guest_phone = booking_context.get("guest_phone", "")
            
            # If guest details missing, request them
            if not guest_name or not guest_email:
                return """
📝 GUEST DETAILS REQUIRED

To complete your booking, I need:
• Full name
• Email address  
• Phone number

Please provide these details like: "My name is John Smith, email john@email.com, phone +60123456789"
"""
            
            # Get booking details from context
            hotel_name = search_context.get("selected_hotel", "")
            room_type = room_context.get("room_type", "")
            check_in = search_context.get("check_in", "")
            check_out = search_context.get("check_out", "")
            
            # Convert dates to date objects
            from datetime import datetime
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            # Get hotel property_id and room_type_id first
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT h.property_id, rt.room_type_id, h.requires_prepayment, h.payment_window_nights
                    FROM hotels h 
                    JOIN room_types rt ON h.property_id = rt.property_id
                    WHERE h.hotel_name = ? AND rt.room_name = ?
                """, (hotel_name, room_type))
                
                hotel_data = cursor.fetchone()
                if not hotel_data:
                    return f"❌ Hotel or room type not found: {hotel_name}, {room_type}"
                
                property_id, room_type_id, requires_prepayment, payment_window_nights = hotel_data
            
            # Calculate total price from context
            total_price = room_context.get("price", 0) * (check_out_date - check_in_date).days
            
            # Use PRE_CONFIRMED system for prepayment hotels, or direct CONFIRMED for pay-at-checkin
            if requires_prepayment:
                print(f"🔄 Creating PRE_CONFIRMED booking (requires prepayment)")
                
                # Import PRE_CONFIRMED booking system
                from .booking_tools.preconfirmed_booking_system import PreConfirmedBookingManager
                
                preconfirmed_manager = PreConfirmedBookingManager()
                result = preconfirmed_manager.create_pre_confirmed_booking(
                    property_id=property_id,
                    room_type_id=room_type_id,
                    guest_name=guest_name,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    guest_email=guest_email,
                    guest_phone=guest_phone,
                    rooms_booked=1,
                    total_price=total_price
                )
                
                if result['success']:
                    payment_deadline = result['payment_window_expires']
                    days_to_payment = result['days_to_payment_deadline']
                    deposit_required = result['deposit_required']
                    
                    return f"""🎉 BOOKING PRE-CONFIRMED SUCCESSFULLY!

🎫 Booking Reference: {result['booking_reference']}
📋 Status: {result['booking_status']} (Payment Required)
🏨 Hotel: {hotel_name}
🛏️ Room: {room_type}
👤 Guest: {guest_name}
📧 Email: {guest_email}

⚠️ PAYMENT REQUIRED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Deposit Amount: RM{deposit_required:.2f}
📅 Payment Deadline: {payment_deadline} ({days_to_payment} days remaining)
🏦 Your room is RESERVED until payment deadline

💡 NEXT STEPS:
1. Make payment of RM{deposit_required:.2f} before {payment_deadline}
2. Submit payment proof using: submit_payment_proof("{result['booking_reference']}", file_path, amount)
3. Room will be CONFIRMED once payment is verified

⚠️ Important: If payment is not received by {payment_deadline}, booking status will change to PENDING and room may become available to other guests."""
                else:
                    return f"❌ BOOKING FAILED: {result['message']}"
            
            else:
                print(f"🔄 Creating CONFIRMED booking (pay at check-in)")
                
                # Import and call booking management for direct confirmation
                from chat_assistant.chat_tools.booking_tools.booking_management import confirm_booking
                
                result = confirm_booking.func(
                    hotel_name=hotel_name,
                    room_type=room_type,
                    guest_name=guest_name,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    guest_email=guest_email,
                    guest_phone=guest_phone,
                    rooms_booked=1
                )
            
            if result.startswith("✅"):
                # Success - extract booking reference
                booking_reference = ""
                lines = result.split('\n')
                for line in lines:
                    if "Reference:" in line:
                        booking_reference = line.split("Reference:")[-1].strip()
                        break
                
                # Generate booking confirmation PDF automatically
                pdf_result = ""
                if booking_reference:
                    try:
                        from .booking_tools.pdf_generator import generate_booking_confirmation_pdf
                        pdf_result = generate_booking_confirmation_pdf(booking_reference, guest_id)
                        print(f"📄 PDF generated for booking {booking_reference}")
                    except Exception as e:
                        print(f"⚠️ PDF generation failed: {e}")
                        pdf_result = "📄 Booking confirmation PDF will be available shortly."
                
                return f"""🎉 BOOKING CONFIRMED SUCCESSFULLY!

{result}

📧 Confirmation details will be sent to {guest_email or guest_name}
🎫 Your booking reference: {booking_reference}

{pdf_result}

💡 Next steps:
• Check payment requirements in your confirmation details
• Booking is confirmed and secured
• Check-in starts at 3:00 PM on your arrival date

Thank you for choosing {hotel_name}! 🏨"""
            else:
                print(f"❌ Booking creation failed: {result}")
                return f"""
❌ BOOKING FAILED

{result}

Would you like me to:
• Try a different hotel
• Check different dates
• Contact our support team
"""
        
        # Check for NO responses
        elif any(word in response_lower for word in ['no', 'cancel', 'stop', 'wait', 'not yet']):
            print("👎 Guest declined booking - offering clarification")
            return """
No problem! What would you like to clarify or change?

I can help you:
• Find different hotels
• Check other room types  
• Look at different dates
• Adjust services (breakfast, etc.)

What would you like to do?
"""
        
        # Check for clarification requests
        elif any(word in response_lower for word in ['change', 'different', 'other', 'modify', 'clarify']):
            print("🔄 Guest wants clarification - routing back to discovery")
            return """
I'd be happy to help you find other options!

Please let me know what you'd like to change:
• Hotel name or location
• Room type or view preference
• Check-in/check-out dates  
• Number of guests
• Services (breakfast, spa, etc.)

What would you like to look for instead?
"""
        
        else:
            # Unclear response - ask for clarification
            return """
I want to make sure I understand correctly. 

Are you ready to book this hotel room, or would you like to look at other options first?

Please say "Yes, book it" to confirm the booking, or "No, show me other options" to continue searching.
"""
            
    except Exception as e:
        print(f"❌ Booking confirmation error: {e}")
        return f"Sorry, there was an error processing your booking. Please try again or contact support."

@tool
def submit_payment_proof(booking_reference: str, file_path: str, amount_claimed: float = 0.0, payment_method: str = "", notes: str = "") -> str:
    """
    Submit payment proof (receipt, bank statement, etc.) for verification.
    Built-in payment proof handling - no external dependencies.
    
    Args:
        booking_reference: The booking reference number
        file_path: Path to the payment proof file (image, PDF, etc.)
        amount_claimed: Amount claimed in the payment proof
        payment_method: Payment method used (e.g., "Bank Transfer", "Cash", "Credit Card")
        notes: Additional notes about the payment
        
    Returns:
        Confirmation of payment proof submission and next steps
    """
    
    try:
        import os
        import shutil
        from pathlib import Path
        import mimetypes
        
        # Validate booking exists
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT booking_reference, guest_name FROM bookings WHERE booking_reference = ?", (booking_reference,))
            booking = cursor.fetchone()
            
            if not booking:
                return f"❌ PAYMENT PROOF SUBMISSION FAILED: Invalid booking reference '{booking_reference}'"
        
        # Validate file
        file_path = Path(file_path)
        if not file_path.exists():
            return "❌ PAYMENT PROOF SUBMISSION FAILED: File not found"
        
        file_size = file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB max
            return "❌ PAYMENT PROOF SUBMISSION FAILED: File too large (max 10MB)"
        
        # Check file type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf']
        
        if mime_type not in allowed_types:
            return "❌ PAYMENT PROOF SUBMISSION FAILED: Invalid file type. Allowed: Images, PDF"
        
        # Create payment_proofs directory
        proof_dir = Path("payment_proofs")
        proof_dir.mkdir(exist_ok=True)
        
        # Generate stored filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = file_path.suffix
        stored_filename = f"{booking_reference}_PaymentProof_{timestamp}{file_ext}"
        stored_path = proof_dir / stored_filename
        
        # Copy file
        shutil.copy2(file_path, stored_path)
        
        # Store in database
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_proofs (
                    proof_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_reference TEXT NOT NULL,
                    guest_name TEXT,
                    original_filename TEXT,
                    stored_filename TEXT,
                    file_size INTEGER,
                    file_type TEXT,
                    amount_claimed DECIMAL(10,2),
                    payment_method TEXT,
                    notes TEXT,
                    submission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    verification_status TEXT DEFAULT 'PENDING'
                )
            """)
            
            cursor.execute("""
                INSERT INTO payment_proofs 
                (booking_reference, guest_name, original_filename, stored_filename, 
                 file_size, file_type, amount_claimed, payment_method, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (booking_reference, booking[1], file_path.name, stored_filename,
                  file_size, mime_type, amount_claimed, payment_method, notes))
            
            proof_id = cursor.lastrowid
            conn.commit()
        
        file_size_mb = file_size / (1024 * 1024)
        
        return f"""✅ PAYMENT PROOF SUBMITTED SUCCESSFULLY

🎫 Booking Reference: {booking_reference}
📁 Original File: {file_path.name}
🏷️  Stored As: {stored_filename}
📊 File Size: {file_size_mb:.1f}MB
📋 File Type: {mime_type}

💰 PAYMENT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Amount Claimed: RM{amount_claimed:.2f}
💳 Payment Method: {payment_method or 'Not specified'}
📝 Notes: {notes or 'None'}

📋 PROOF ID: {proof_id}

🔄 NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Your payment proof has been stored and forwarded to our finance team
📧 You will receive verification confirmation within 1-2 business days
💡 Use get_payment_proof_status() to check verification status
⚠️  Please keep your original receipt until verification is complete

✅ Thank you for submitting your payment proof!"""
        
    except Exception as e:
        return f"❌ Error submitting payment proof: {str(e)}"

@tool
def get_payment_proof_status(booking_reference: str) -> str:
    """
    Check the status of submitted payment proofs for a booking.
    Built-in payment proof status checking - no external dependencies.
    
    Args:
        booking_reference: The booking reference number
        
    Returns:
        Status of all submitted payment proofs including verification status
    """
    
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get all payment proofs for booking
            cursor.execute("""
                SELECT proof_id, original_filename, stored_filename, file_size, 
                       file_type, submission_date, verification_status, 
                       amount_claimed, payment_method, notes
                FROM payment_proofs 
                WHERE booking_reference = ?
                ORDER BY submission_date DESC
            """, (booking_reference,))
            
            proofs = cursor.fetchall()
        
        if not proofs:
            return f"""📋 PAYMENT PROOF STATUS

🎫 Booking Reference: {booking_reference}
📁 Submitted Proofs: None

💡 To submit payment proof, use submit_payment_proof() with your receipt/bank statement."""

        summary = f"""📋 PAYMENT PROOF STATUS

🎫 Booking Reference: {booking_reference}
📁 Total Submissions: {len(proofs)}

📋 PROOF HISTORY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        for i, proof in enumerate(proofs, 1):
            (proof_id, original_filename, stored_filename, file_size, file_type,
             submission_date, verification_status, amount_claimed, payment_method, notes) = proof
            
            status_emoji = {
                'PENDING': '⏳',
                'VERIFIED': '✅',
                'REJECTED': '❌',
                'PROCESSING': '🔄'
            }.get(verification_status, '❓')
            
            file_size_mb = file_size / (1024 * 1024)
            submission_dt = datetime.strptime(submission_date, '%Y-%m-%d %H:%M:%S')
            formatted_date = submission_dt.strftime('%d %b %Y, %H:%M')
            
            summary += f"""

{i}. {status_emoji} {verification_status} - {original_filename}
   📅 Submitted: {formatted_date}
   💰 Amount Claimed: RM{amount_claimed:.2f}
   💳 Payment Method: {payment_method or 'Not specified'}
   📊 File Size: {file_size_mb:.1f}MB
   📝 Notes: {notes or 'None'}"""

        # Count by status
        pending_count = sum(1 for p in proofs if p[6] == 'PENDING')
        verified_count = sum(1 for p in proofs if p[6] == 'VERIFIED')
        rejected_count = sum(1 for p in proofs if p[6] == 'REJECTED')

        summary += f"""

📊 SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Pending Verification: {pending_count}
✅ Verified: {verified_count}
❌ Rejected: {rejected_count}

💡 NEXT STEPS:
{f"⏳ Your payment proof is being reviewed by our finance team." if pending_count > 0 else ""}
{f"✅ Payment verification complete!" if verified_count > 0 and pending_count == 0 else ""}
{f"⚠️  Some submissions were rejected. Please resubmit valid proof." if rejected_count > 0 else ""}"""

        return summary
        
    except Exception as e:
        return f"❌ Error getting payment proof status: {str(e)}"

@tool
def check_partial_payment_status(booking_reference: str) -> str:
    """
    Check partial payment status for hotels that require deposits or staged payments.
    Built-in partial payment tracking - no external dependencies.
    
    Args:
        booking_reference: The booking reference number
        
    Returns:
        Payment breakdown showing deposits, partial payments, and balance due
    """
    
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get booking details
            cursor.execute("""
                SELECT b.booking_reference, b.guest_name, b.total_price, 
                       h.hotel_name, h.requires_prepayment
                FROM bookings b
                JOIN hotels h ON b.property_id = h.property_id
                WHERE b.booking_reference = ?
            """, (booking_reference,))
            
            booking = cursor.fetchone()
            if not booking:
                return f"❌ Booking not found: {booking_reference}"
            
            booking_ref, guest_name, total_price, hotel_name, requires_prepayment = booking
            
            # Calculate deposit requirement (30% for prepayment hotels, 0 for others)
            deposit_required = total_price * 0.3 if requires_prepayment else 0
            
            # Get payment proof submissions
            cursor.execute("""
                SELECT amount_claimed, verification_status, submission_date, payment_method
                FROM payment_proofs 
                WHERE booking_reference = ? AND verification_status = 'VERIFIED'
                ORDER BY submission_date
            """, (booking_reference,))
            
            verified_payments = cursor.fetchall()
            total_paid = sum(payment[0] for payment in verified_payments)
            balance_due = total_price - total_paid
            
            # Determine payment status
            if total_paid >= total_price:
                payment_status = "FULLY_PAID"
                status_emoji = "✅"
            elif total_paid >= deposit_required and deposit_required > 0:
                payment_status = "DEPOSIT_PAID"
                status_emoji = "🟡"
            elif total_paid > 0:
                payment_status = "PARTIALLY_PAID"
                status_emoji = "⚠️"
            else:
                payment_status = "UNPAID"
                status_emoji = "❌"
            
            summary = f"""💳 PARTIAL PAYMENT STATUS

🏨 Hotel: {hotel_name}
🎫 Booking: {booking_reference}
👤 Guest: {guest_name}
{status_emoji} Status: {payment_status}

💰 FINANCIAL BREAKDOWN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Total Booking Value: RM{total_price:.2f}
💸 Total Verified Payments: RM{total_paid:.2f}
⚠️  Balance Due: RM{balance_due:.2f}"""

            if requires_prepayment:
                deposit_outstanding = max(0, deposit_required - total_paid)
                summary += f"""

🏦 DEPOSIT POLICY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Deposit Required: RM{deposit_required:.2f} (30% of total)
⚠️  Deposit Outstanding: RM{deposit_outstanding:.2f}"""

            if verified_payments:
                summary += f"""

📋 VERIFIED PAYMENT HISTORY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                
                for amount, status, date_str, method in verified_payments:
                    payment_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    formatted_date = payment_date.strftime('%d %b %Y')
                    summary += f"""
• RM{amount:.2f} - {method or 'Payment'} - {formatted_date}"""

            # Next steps
            if balance_due > 0:
                if requires_prepayment and total_paid < deposit_required:
                    summary += f"""

🚨 NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Deposit payment of RM{deposit_required - total_paid:.2f} required to confirm booking
💳 Submit payment proof after making your deposit payment
📱 Use submit_payment_proof() to upload receipt/bank statement"""
                else:
                    summary += f"""

🚨 NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 Balance payment of RM{balance_due:.2f} due at check-in
✅ Deposit requirement satisfied"""
            else:
                summary += f"""

✅ PAYMENT COMPLETE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 All payments received - booking fully confirmed!"""

            return summary
        
    except Exception as e:
        return f"❌ Error checking payment status: {str(e)}"

@tool
def booking_agent_tool(user_input: str, conversation_context: str = "") -> str:
    """
    Enhanced Booking Agent - Handles guest details, validation, and booking creation.
    
    Use this tool when:
    • Guest has selected hotel, room, dates 
    • Pricing has been discussed
    • Ready for booking confirmation
    • Guest provides personal details
    
    Do NOT use for:
    • Hotel search → Use discovery_agent_tool
    • Room information → Use room_intelligence_agent_tool  
    • Service pricing → Use service_agent_tool
    
    Args:
        user_input: Guest's booking request or confirmation response
        conversation_context: Previous conversation context
        
    Returns:
        Booking summary + confirmation request OR booking result
    """
    print(f"📋 BOOKING AGENT: {user_input}")
    
    try:
        guest_id = get_guest_id()
        user_lower = user_input.lower()
        
        # Step 1: Handle guest details extraction
        if any(keyword in user_lower for keyword in ['name is', 'email', 'phone', '@', 'my name', 'i am']):
            extraction_result = extract_guest_details(user_input, guest_id)
            print(f"👤 Guest details extraction: {extraction_result}")
            
            # If extraction was successful, proceed to booking
            if "✅" in extraction_result:
                return f"""
✅ Thank you for providing your details!

Perfect! I have your information. Now let me create your booking summary for confirmation.
"""
            else:
                return extraction_result  # Return extraction error/instruction
        
        # Step 2: Check if booking context is ready
        context_check = check_booking_context_ready(guest_id)
        context_data = json.loads(context_check)
        
        if not context_data.get("context_ready", False):
            # Context not ready - redirect to discovery agent
            missing = context_data.get("missing_slots", [])
            return f"""
I need a bit more information before we can book:

Missing details: {', '.join(missing)}

Let me help you find the right hotel and room first. What are you looking for?
"""
        
        # Step 3: Check if this is a confirmation response
        confirmation_words = ['yes', 'no', 'book', 'confirm', 'cancel', 'proceed', 'change']
        if any(word in user_input.lower() for word in confirmation_words):
            return process_booking_confirmation(user_input, guest_id)
        
        # Step 4: Present booking summary and ask for confirmation
        summary = create_booking_summary(guest_id)
        return summary
        
    except Exception as e:
        print(f"❌ Booking Agent error: {e}")
        return "I'd be happy to help you with your booking! Let me first make sure we have all the details - what hotel and dates are you interested in?"

@tool
def check_payment_window_expiry() -> str:
    """
    Check for PRE_CONFIRMED bookings with expired payment windows and update them to PENDING status.
    This tool should be run daily/regularly to maintain booking status accuracy.
    
    Returns:
        Summary of bookings whose status was updated due to payment window expiry
    """
    
    try:
        from .booking_tools.preconfirmed_booking_system import PreConfirmedBookingManager
        
        manager = PreConfirmedBookingManager()
        updated_bookings = manager.check_payment_window_expiry()
        
        if not updated_bookings:
            return "✅ No payment windows have expired. All PRE_CONFIRMED bookings are still within payment deadline."
        
        summary = f"⚠️ PAYMENT WINDOW EXPIRY PROCESSING\n\n"
        summary += f"Updated {len(updated_bookings)} booking(s):\n\n"
        
        for booking in updated_bookings:
            summary += f"🎫 {booking['booking_reference']}\n"
            summary += f"   Status: {booking['old_status']} → {booking['new_status']}\n"
            summary += f"   Inventory: {booking['inventory_action']}\n"
            summary += f"   Success: {'✅' if booking['inventory_success'] else '❌'}\n\n"
        
        summary += "💡 These bookings are now PENDING. Guests can still pay to reconfirm if rooms are available."
        
        return summary
        
    except Exception as e:
        return f"❌ Error checking payment window expiry: {str(e)}"

@tool
def process_late_payment(booking_reference: str, amount: float, payment_method: str = "Credit Card") -> str:
    """
    Process payment for a PENDING booking that missed its payment window.
    Handles room availability check and buffer booking creation if needed.
    
    Args:
        booking_reference: The booking reference number
        amount: Payment amount
        payment_method: Method of payment (e.g., "Bank Transfer", "Credit Card")
        
    Returns:
        Payment processing result and booking status update
    """
    
    try:
        from .booking_tools.preconfirmed_booking_system import PreConfirmedBookingManager
        
        manager = PreConfirmedBookingManager()
        result = manager.process_late_payment(booking_reference, amount, payment_method)
        
        if result['success']:
            if result.get('requires_manual_intervention'):
                return f"""💳 LATE PAYMENT PROCESSED - MANUAL INTERVENTION REQUIRED

🎫 Booking Reference: {booking_reference}
💰 Payment Amount: RM{amount:.2f}
📊 Payment Status: {result['payment_status']}
📋 Booking Status: {result['booking_status']}

⚠️ ROOM NO LONGER AVAILABLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 Your selected room has been sold to another guest
💳 Your payment has been received and recorded
📋 Booking added to buffer list for manual resolution

🏨 NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Hotel staff will contact you within 24 hours
• We will offer similar room or upgrade if available
• Full refund option available if no suitable alternative
• Priority rebooking for future dates

📞 For immediate assistance, please contact hotel directly.
Thank you for your patience."""
            
            else:
                return f"""✅ LATE PAYMENT PROCESSED SUCCESSFULLY

🎫 Booking Reference: {booking_reference}
💰 Payment Amount: RM{amount:.2f}
📊 Payment Status: {result['payment_status']}
📋 Booking Status: {result['booking_status']}

🎉 BOOKING CONFIRMED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Room is available and has been secured for you
💳 Payment verified and applied to your booking
🏨 Your booking is now fully confirmed

Thank you for your payment! Your room is secured."""
        
        else:
            return f"❌ LATE PAYMENT PROCESSING FAILED: {result['message']}"
        
    except Exception as e:
        return f"❌ Error processing late payment: {str(e)}"

@tool
def get_buffer_bookings() -> str:
    """
    Get all buffer bookings that require manual intervention.
    These are bookings where guests paid late but rooms are no longer available.
    
    Returns:
        List of buffer bookings awaiting resolution
    """
    
    try:
        from .booking_tools.preconfirmed_booking_system import PreConfirmedBookingManager
        
        manager = PreConfirmedBookingManager()
        buffer_bookings = manager.get_buffer_bookings()
        
        if not buffer_bookings:
            return "✅ No buffer bookings requiring manual intervention."
        
        summary = f"🚨 BUFFER BOOKINGS REQUIRING MANUAL INTERVENTION\n\n"
        summary += f"Total: {len(buffer_bookings)} booking(s)\n\n"
        
        for booking in buffer_bookings:
            summary += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            summary += f"🎫 Booking: {booking['booking_reference']}\n"
            summary += f"🏨 Hotel: {booking['hotel_name']}\n"
            summary += f"👤 Guest: {booking['guest_name']}\n"
            summary += f"📧 Email: {booking['guest_email']}\n"
            summary += f"📞 Phone: {booking['guest_phone']}\n"
            summary += f"🛏️ Room: {booking['original_room_type']}\n"
            summary += f"📅 Dates: {booking['check_in_date']} to {booking['check_out_date']}\n"
            summary += f"🏠 Rooms: {booking['rooms_booked']}\n"
            summary += f"💰 Total: RM{booking['total_price']:.2f}\n"
            summary += f"💳 Payment: {booking['payment_status']}\n"
            summary += f"⚠️ Reason: {booking['reason']}\n"
            summary += f"📝 Notes: {booking['notes']}\n"
            summary += f"🕒 Created: {booking['created_at']}\n\n"
        
        summary += "💡 These guests need to be contacted for alternative arrangements."
        
        return summary
        
    except Exception as e:
        return f"❌ Error getting buffer bookings: {str(e)}"

# Export the complete booking agent with PRE_CONFIRMED payment features
BOOKING_AGENT_TOOLS = [
    booking_agent_tool,
    submit_payment_proof,
    get_payment_proof_status,
    check_partial_payment_status,
    check_payment_window_expiry,
    process_late_payment,
    get_buffer_bookings
]

print("📋 Enhanced Booking Agent initialized - PRE_CONFIRMED system with payment window monitoring")
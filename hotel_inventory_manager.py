#!/usr/bin/env python3
"""
Hotel Inventory Manager - FOR HOTEL STAFF ONLY
Allows manual adjustment of room availability and inventory.
"""

import sqlite3
import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

class HotelInventoryManager:
    """Manages hotel room inventory - FOR HOTEL STAFF ONLY"""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_current_inventory_status(self, property_id: str, room_type_id: str, target_date: str = None) -> Dict:
        """Get current inventory status for a room type"""
        
        if not target_date:
            target_date = date.today().strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get base room information
                cursor.execute("""
                    SELECT h.hotel_name, rt.room_name, rt.total_rooms, rt.base_price_per_night
                    FROM hotels h
                    JOIN room_types rt ON h.property_id = rt.property_id
                    WHERE h.property_id = ? AND rt.room_type_id = ?
                """, (property_id, room_type_id))
                
                base_info = cursor.fetchone()
                if not base_info:
                    return {"success": False, "message": "Hotel or room type not found"}
                
                hotel_name, room_name, total_rooms, base_price = base_info
                
                # Get daily inventory for the target date
                cursor.execute("""
                    SELECT available_rooms, current_price, updated_at
                    FROM room_inventory
                    WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                """, (property_id, room_type_id, target_date))
                
                daily_info = cursor.fetchone()
                if daily_info:
                    available_rooms, current_price, updated_at = daily_info
                else:
                    available_rooms, current_price, updated_at = 0, base_price, "No record"
                
                # Get confirmed bookings for this date
                cursor.execute("""
                    SELECT COALESCE(SUM(rooms_booked), 0) as booked_rooms
                    FROM bookings 
                    WHERE property_id = ? AND room_type_id = ? 
                    AND booking_status = 'CONFIRMED'
                    AND check_in_date <= ? AND check_out_date > ?
                """, (property_id, room_type_id, target_date, target_date))
                
                booked_rooms = cursor.fetchone()[0]
                
                return {
                    "success": True,
                    "hotel_name": hotel_name,
                    "room_name": room_name,
                    "target_date": target_date,
                    "base_inventory": {
                        "total_rooms": total_rooms,
                        "base_price": base_price
                    },
                    "daily_inventory": {
                        "available_rooms": available_rooms,
                        "current_price": current_price,
                        "updated_at": updated_at
                    },
                    "bookings": {
                        "confirmed_bookings": booked_rooms,
                        "sellable_rooms": available_rooms - booked_rooms
                    }
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def increase_base_inventory(self, property_id: str, room_type_id: str, additional_rooms: int, reason: str = "") -> Dict:
        """
        PERMANENTLY increase the base room inventory (adding physical rooms to hotel)
        This affects the total_rooms in room_types table
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current total rooms
                cursor.execute("""
                    SELECT total_rooms, room_name FROM room_types
                    WHERE property_id = ? AND room_type_id = ?
                """, (property_id, room_type_id))
                
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "message": "Room type not found"}
                
                current_total, room_name = result
                new_total = current_total + additional_rooms
                
                # Update base inventory
                cursor.execute("""
                    UPDATE room_types 
                    SET total_rooms = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE property_id = ? AND room_type_id = ?
                """, (new_total, property_id, room_type_id))
                
                # Also update all future room_inventory records to reflect new base inventory
                cursor.execute("""
                    UPDATE room_inventory 
                    SET available_rooms = available_rooms + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE property_id = ? AND room_type_id = ? AND stay_date >= DATE('now')
                """, (additional_rooms, property_id, room_type_id))
                
                rows_updated = cursor.rowcount
                
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "BASE_INVENTORY_INCREASE",
                    "room_name": room_name,
                    "previous_total": current_total,
                    "new_total": new_total,
                    "rooms_added": additional_rooms,
                    "future_dates_updated": rows_updated,
                    "reason": reason,
                    "message": f"✅ Added {additional_rooms} {room_name} rooms permanently. Total now: {new_total}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error increasing base inventory: {str(e)}"}
    
    def increase_daily_availability(self, property_id: str, room_type_id: str, 
                                  start_date: str, end_date: str, additional_rooms: int, 
                                  reason: str = "") -> Dict:
        """
        TEMPORARILY increase room availability for specific dates
        This updates available_rooms in room_inventory table
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get room info
                cursor.execute("""
                    SELECT room_name FROM room_types
                    WHERE property_id = ? AND room_type_id = ?
                """, (property_id, room_type_id))
                
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "message": "Room type not found"}
                
                room_name = result[0]
                
                # Convert dates
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                updated_dates = []
                current_date = start
                
                while current_date <= end:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Check if inventory record exists
                    cursor.execute("""
                        SELECT available_rooms FROM room_inventory
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, date_str))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        old_available = existing[0]
                        new_available = old_available + additional_rooms
                        
                        cursor.execute("""
                            UPDATE room_inventory 
                            SET available_rooms = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                        """, (new_available, property_id, room_type_id, date_str))
                        
                        updated_dates.append({
                            "date": date_str,
                            "old_available": old_available,
                            "new_available": new_available,
                            "added": additional_rooms
                        })
                    else:
                        return {"success": False, "message": f"No inventory record for {date_str}"}
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "DAILY_AVAILABILITY_INCREASE",
                    "room_name": room_name,
                    "date_range": f"{start_date} to {end_date}",
                    "rooms_added_per_day": additional_rooms,
                    "dates_updated": len(updated_dates),
                    "updated_dates": updated_dates,
                    "reason": reason,
                    "message": f"✅ Added {additional_rooms} {room_name} rooms per day from {start_date} to {end_date}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error increasing daily availability: {str(e)}"}
    
    def bulk_inventory_adjustment(self, property_id: str, room_type_id: str, 
                                date_adjustments: List[Dict], reason: str = "") -> Dict:
        """
        Bulk adjust inventory for multiple dates with different amounts
        date_adjustments format: [{"date": "2025-06-07", "add_rooms": 5}, ...]
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get room info
                cursor.execute("""
                    SELECT room_name FROM room_types
                    WHERE property_id = ? AND room_type_id = ?
                """, (property_id, room_type_id))
                
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "message": "Room type not found"}
                
                room_name = result[0]
                updated_dates = []
                
                for adjustment in date_adjustments:
                    target_date = adjustment["date"]
                    add_rooms = adjustment["add_rooms"]
                    
                    # Get current availability
                    cursor.execute("""
                        SELECT available_rooms FROM room_inventory
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, target_date))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        old_available = existing[0]
                        new_available = old_available + add_rooms
                        
                        cursor.execute("""
                            UPDATE room_inventory 
                            SET available_rooms = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                        """, (new_available, property_id, room_type_id, target_date))
                        
                        updated_dates.append({
                            "date": target_date,
                            "old_available": old_available,
                            "new_available": new_available,
                            "added": add_rooms
                        })
                
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "BULK_INVENTORY_ADJUSTMENT",
                    "room_name": room_name,
                    "dates_updated": len(updated_dates),
                    "updated_dates": updated_dates,
                    "reason": reason,
                    "message": f"✅ Bulk updated {len(updated_dates)} dates for {room_name}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error in bulk adjustment: {str(e)}"}

def demo_inventory_management():
    """Demo the inventory management system"""
    
    print("🏨 HOTEL INVENTORY MANAGEMENT DEMO")
    print("=" * 60)
    
    manager = HotelInventoryManager()
    
    # Test data
    property_id = "grand_hyatt_kuala_lumpur"
    room_type_id = "grand_hyatt_kl_deluxe_king"
    today = date.today().strftime('%Y-%m-%d')
    
    print(f"📋 Testing with:")
    print(f"   🏨 Hotel: {property_id}")
    print(f"   🛏️ Room: {room_type_id}")
    print(f"   📅 Date: {today}")
    
    # Step 1: Check current status
    print(f"\n🔍 STEP 1: Current inventory status")
    status = manager.get_current_inventory_status(property_id, room_type_id, today)
    
    if status["success"]:
        print(f"✅ Status for {status['hotel_name']} - {status['room_name']}:")
        print(f"   📊 Base inventory: {status['base_inventory']['total_rooms']} total rooms")
        print(f"   📅 Daily availability: {status['daily_inventory']['available_rooms']} available")
        print(f"   📝 Confirmed bookings: {status['bookings']['confirmed_bookings']} rooms booked")
        print(f"   💡 Sellable rooms: {status['bookings']['sellable_rooms']} rooms")
    else:
        print(f"❌ Error: {status['message']}")
        return
    
    # Step 2: Demo temporary increase (most common scenario)
    print(f"\n📈 STEP 2: Adding 5 more rooms for today (temporary)")
    temp_increase = manager.increase_daily_availability(
        property_id=property_id,
        room_type_id=room_type_id,
        start_date=today,
        end_date=today,
        additional_rooms=5,
        reason="Extra rooms made available for high demand day"
    )
    
    if temp_increase["success"]:
        print(f"✅ {temp_increase['message']}")
        for update in temp_increase['updated_dates']:
            print(f"   📅 {update['date']}: {update['old_available']} → {update['new_available']} rooms (+{update['added']})")
    else:
        print(f"❌ Error: {temp_increase['message']}")
    
    # Step 3: Check status after increase
    print(f"\n🔍 STEP 3: Status after temporary increase")
    new_status = manager.get_current_inventory_status(property_id, room_type_id, today)
    
    if new_status["success"]:
        print(f"✅ Updated status:")
        print(f"   📅 Daily availability: {new_status['daily_inventory']['available_rooms']} available")
        print(f"   💡 Sellable rooms: {new_status['bookings']['sellable_rooms']} rooms")
        print(f"   📈 Change: +5 rooms added temporarily")
    
    # Step 4: Demo permanent increase (adding physical rooms)
    print(f"\n🏗️ STEP 4: Adding 2 rooms permanently (new construction)")
    
    # First, let's not actually do this in demo, just show what would happen
    print(f"   ⚠️ DEMO MODE: Would permanently add 2 rooms to base inventory")
    print(f"   ⚠️ This would update room_types.total_rooms from {status['base_inventory']['total_rooms']} to {status['base_inventory']['total_rooms'] + 2}")
    print(f"   ⚠️ All future dates would get +2 rooms automatically")
    
    # Step 5: Demo bulk adjustment
    print(f"\n📊 STEP 5: Bulk inventory adjustment demo")
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    day_after = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
    
    bulk_adjustments = [
        {"date": tomorrow, "add_rooms": 3},
        {"date": day_after, "add_rooms": 7}
    ]
    
    print(f"   📋 Would add:")
    for adj in bulk_adjustments:
        print(f"      📅 {adj['date']}: +{adj['add_rooms']} rooms")

def interactive_inventory_manager():
    """Interactive inventory management tool"""
    
    print("🏨 INTERACTIVE HOTEL INVENTORY MANAGER")
    print("=" * 50)
    
    manager = HotelInventoryManager()
    
    # Get hotel and room selection
    property_id = input("Enter property_id (e.g., grand_hyatt_kuala_lumpur): ").strip()
    room_type_id = input("Enter room_type_id (e.g., grand_hyatt_kl_deluxe_king): ").strip()
    target_date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
    
    if not target_date:
        target_date = date.today().strftime('%Y-%m-%d')
    
    # Show current status
    print(f"\n🔍 Current Status:")
    status = manager.get_current_inventory_status(property_id, room_type_id, target_date)
    
    if not status["success"]:
        print(f"❌ Error: {status['message']}")
        return
    
    print(f"🏨 {status['hotel_name']} - {status['room_name']}")
    print(f"📅 Date: {status['target_date']}")
    print(f"📊 Base inventory: {status['base_inventory']['total_rooms']} total rooms")
    print(f"📋 Available today: {status['daily_inventory']['available_rooms']} rooms")
    print(f"📝 Confirmed bookings: {status['bookings']['confirmed_bookings']} rooms")
    print(f"💡 Currently sellable: {status['bookings']['sellable_rooms']} rooms")
    
    # Ask what to do
    print(f"\nWhat would you like to do?")
    print(f"1. Add rooms for specific dates (temporary)")
    print(f"2. Add rooms permanently (base inventory)")
    print(f"3. Just view status")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        additional_rooms = int(input("How many rooms to add? "))
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        end_date = input("End date (YYYY-MM-DD): ").strip()
        reason = input("Reason for increase: ").strip()
        
        result = manager.increase_daily_availability(
            property_id, room_type_id, start_date, end_date, additional_rooms, reason
        )
        
        if result["success"]:
            print(f"✅ {result['message']}")
            for update in result['updated_dates']:
                print(f"   📅 {update['date']}: {update['old_available']} → {update['new_available']} rooms")
        else:
            print(f"❌ Error: {result['message']}")
    
    elif choice == "2":
        additional_rooms = int(input("How many rooms to add permanently? "))
        reason = input("Reason for increase (e.g., 'New wing constructed'): ").strip()
        
        result = manager.increase_base_inventory(property_id, room_type_id, additional_rooms, reason)
        
        if result["success"]:
            print(f"✅ {result['message']}")
            print(f"📊 Previous total: {result['previous_total']} rooms")
            print(f"📊 New total: {result['new_total']} rooms")
            print(f"📅 Future dates updated: {result['future_dates_updated']}")
        else:
            print(f"❌ Error: {result['message']}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_inventory_manager()
    else:
        demo_inventory_management() 
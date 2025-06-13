#!/usr/bin/env python3
"""
Hotel Availability Management System - FOR HOTEL MANAGERS ONLY
Manages inventory, pricing, room blocks, and availability across properties
NOT used by Ella - Ella only reads from database via hotel_search_tool.py
"""

import sqlite3
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

class HotelAvailabilityManager:
    """Manages hotel inventory, pricing, and room blocks - FOR HOTEL MANAGERS ONLY."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
        self._init_room_blocks_table()
    
    def _init_room_blocks_table(self):
        """Initialize room blocks table if it doesn't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS room_blocks (
                        block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        block_reference TEXT UNIQUE,
                        property_id TEXT NOT NULL,
                        room_type_id TEXT NOT NULL,
                        block_date TEXT NOT NULL,
                        rooms_blocked INTEGER NOT NULL,
                        block_type TEXT NOT NULL,
                        block_reason TEXT,
                        blocked_by TEXT,
                        block_status TEXT DEFAULT 'ACTIVE',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (property_id) REFERENCES hotels(property_id),
                        FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id)
                    )
                """)
                
                # Create indexes for efficient querying
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_blocks_date ON room_blocks(block_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_blocks_property ON room_blocks(property_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_room_blocks_status ON room_blocks(block_status)")
                
                conn.commit()
                
        except Exception as e:
            print(f"Warning: Could not initialize room_blocks table: {e}")
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def generate_block_reference(self) -> str:
        """Generate unique block reference."""
        return f"BLK{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
    
    def add_inventory_date_range(self, property_id: str, room_type_id: str,
                                start_date: date, end_date: date, 
                                available_rooms: int, price_per_night: float) -> Dict:
        """Add room inventory for a date range."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = start_date
                added_count = 0
                
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Insert or update inventory
                    cursor.execute("""
                        INSERT OR REPLACE INTO room_inventory (
                            property_id, room_type_id, stay_date, available_rooms,
                            base_price, current_price, price_last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (property_id, room_type_id, date_str, available_rooms,
                          price_per_night, price_per_night))
                    
                    added_count += 1
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Added inventory for {added_count} dates",
                    'property_id': property_id,
                    'room_type_id': room_type_id,
                    'date_range': f"{start_date} to {end_date}",
                    'available_rooms': available_rooms,
                    'price_per_night': price_per_night
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error adding inventory: {str(e)}"
            }
    
    def update_pricing(self, property_id: str, room_type_id: str,
                      start_date: date, end_date: date, new_price: float) -> Dict:
        """Update pricing for a date range."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE room_inventory 
                    SET current_price = ?, price_last_updated = CURRENT_TIMESTAMP
                    WHERE property_id = ? AND room_type_id = ? 
                    AND stay_date BETWEEN ? AND ?
                """, (new_price, property_id, room_type_id, 
                      start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                
                updated_count = cursor.rowcount
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Updated pricing for {updated_count} dates",
                    'new_price': new_price,
                    'updated_count': updated_count
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error updating pricing: {str(e)}"
            }
    
    def adjust_inventory(self, property_id: str, room_type_id: str,
                        stay_date: date, adjustment: int) -> Dict:
        """Adjust available room count for a specific date."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                date_str = stay_date.strftime('%Y-%m-%d')
                
                cursor.execute("""
                    UPDATE room_inventory 
                    SET available_rooms = available_rooms + ?
                    WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                """, (adjustment, property_id, room_type_id, date_str))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return {
                        'success': True,
                        'message': f"Adjusted inventory by {adjustment} rooms for {stay_date}",
                        'adjustment': adjustment
                    }
                else:
                    return {
                        'success': False,
                        'message': f"No inventory found for {stay_date}"
                    }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error adjusting inventory: {str(e)}"
            }
    
    def get_inventory_report(self, property_id: str, start_date: date, end_date: date) -> List[Dict]:
        """Get inventory report for a property and date range."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT ri.room_type_id, rt.room_name, ri.stay_date, 
                           ri.available_rooms, ri.current_price, ri.demand_level
                    FROM room_inventory ri
                    JOIN room_types rt ON ri.room_type_id = rt.room_type_id
                    WHERE ri.property_id = ? 
                    AND ri.stay_date BETWEEN ? AND ?
                    ORDER BY ri.stay_date, rt.room_name
                """, (property_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                
                results = cursor.fetchall()
                
                report = []
                for row in results:
                    room_type_id, room_name, stay_date, available_rooms, current_price, demand_level = row
                    report.append({
                        'room_type_id': room_type_id,
                        'room_name': room_name,
                        'stay_date': stay_date,
                        'available_rooms': available_rooms,
                        'current_price': current_price,
                        'demand_level': demand_level
                    })
                
                return report
                
        except Exception as e:
            print(f"Error getting inventory report: {e}")
            return []
    
    def process_booking_confirmation(self, property_id: str, room_type_id: str,
                                   check_in: date, check_out: date, rooms_booked: int) -> Dict:
        """Process confirmed booking by reducing available inventory."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = check_in
                updated_dates = []
                
                while current_date < check_out:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Reduce available rooms
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET available_rooms = available_rooms - ?
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                        AND available_rooms >= ?
                    """, (rooms_booked, property_id, room_type_id, date_str, rooms_booked))
                    
                    if cursor.rowcount > 0:
                        updated_dates.append(date_str)
                    else:
                        conn.rollback()
                        return {
                            'success': False,
                            'message': f"Insufficient inventory for {date_str}"
                        }
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Booking confirmed - inventory updated for {len(updated_dates)} dates",
                    'updated_dates': updated_dates,
                    'rooms_booked': rooms_booked
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error processing booking: {str(e)}"
            }
    
    def cancel_booking_restore_inventory(self, property_id: str, room_type_id: str,
                                       check_in: date, check_out: date, rooms_to_restore: int) -> Dict:
        """Restore inventory when booking is cancelled."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = check_in
                restored_dates = []
                
                while current_date < check_out:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Restore available rooms
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET available_rooms = available_rooms + ?
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (rooms_to_restore, property_id, room_type_id, date_str))
                    
                    if cursor.rowcount > 0:
                        restored_dates.append(date_str)
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Booking cancelled - inventory restored for {len(restored_dates)} dates",
                    'restored_dates': restored_dates,
                    'rooms_restored': rooms_to_restore
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error restoring inventory: {str(e)}"
            }

    # ROOM BLOCK MANAGEMENT - FOR HOTEL STAFF ONLY
    def get_real_time_availability(self, property_id: str, room_type_id: str, stay_date: str) -> Dict:
        """Get real-time availability considering bookings and blocks."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get base room count from room_types table
                cursor.execute("""
                    SELECT total_rooms FROM room_types
                    WHERE property_id = ? AND room_type_id = ? AND is_active = 1
                """, (property_id, room_type_id))
                
                room_type_row = cursor.fetchone()
                if not room_type_row:
                    return {
                        'available_rooms': 0,
                        'booked_rooms': 0,
                        'blocked_rooms': 0,
                        'total_rooms': 0,
                        'message': "Room type not found"
                    }
                
                base_rooms = room_type_row[0]
                
                # Calculate confirmed bookings for this date
                cursor.execute("""
                    SELECT COALESCE(SUM(rooms_booked), 0) as booked_rooms
                    FROM bookings 
                    WHERE property_id = ? AND room_type_id = ? 
                    AND booking_status = 'CONFIRMED'
                    AND check_in_date <= ? AND check_out_date > ?
                """, (property_id, room_type_id, stay_date, stay_date))
                
                booked_rooms = cursor.fetchone()[0]
                
                # Calculate active room blocks for this date
                cursor.execute("""
                    SELECT COALESCE(SUM(rooms_blocked), 0) as blocked_rooms
                    FROM room_blocks 
                    WHERE property_id = ? AND room_type_id = ? 
                    AND block_status = 'ACTIVE'
                    AND block_date = ?
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (property_id, room_type_id, stay_date))
                
                blocked_rooms = cursor.fetchone()[0]
                
                # Calculate actual available rooms: total - bookings - blocks
                available_rooms = base_rooms - booked_rooms - blocked_rooms
                
                return {
                    'available_rooms': max(0, available_rooms),
                    'booked_rooms': booked_rooms,
                    'blocked_rooms': blocked_rooms,
                    'total_rooms': base_rooms,
                    'message': f"Real-time availability calculated for {stay_date}"
                }
                
        except Exception as e:
            return {
                'available_rooms': 0,
                'booked_rooms': 0,
                'blocked_rooms': 0,
                'total_rooms': 0,
                'message': f"Error getting availability: {str(e)}"
            }
    
    def create_room_block(self, property_id: str, room_type_id: str, block_date: date,
                         rooms_blocked: int, block_type: str, block_reason: str = "",
                         blocked_by: str = "hotel_staff", expires_at: Optional[datetime] = None,
                         notes: str = "") -> Dict:
        """Create a room block that reduces availability - FOR HOTEL STAFF ONLY."""
        
        try:
            block_reference = self.generate_block_reference()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify room type exists
                cursor.execute("""
                    SELECT total_rooms FROM room_types
                    WHERE property_id = ? AND room_type_id = ? AND is_active = 1
                """, (property_id, room_type_id))
                
                room_type_row = cursor.fetchone()
                if not room_type_row:
                    return {
                        'success': False,
                        'message': "Room type not found or inactive"
                    }
                
                total_rooms = room_type_row[0]
                
                # Check if blocking is feasible
                availability = self.get_real_time_availability(
                    property_id, room_type_id, block_date.strftime('%Y-%m-%d')
                )
                
                if availability['available_rooms'] < rooms_blocked:
                    return {
                        'success': False,
                        'message': f"Cannot block {rooms_blocked} rooms. Only {availability['available_rooms']} available (Booked: {availability['booked_rooms']}, Already blocked: {availability['blocked_rooms']})"
                    }
                
                # Create room block
                cursor.execute("""
                    INSERT INTO room_blocks (
                        block_reference, property_id, room_type_id, block_date,
                        rooms_blocked, block_type, block_reason, blocked_by,
                        expires_at, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    block_reference, property_id, room_type_id, block_date.strftime('%Y-%m-%d'),
                    rooms_blocked, block_type, block_reason, blocked_by,
                    expires_at, notes
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'block_reference': block_reference,
                    'property_id': property_id,
                    'room_type_id': room_type_id,
                    'block_date': block_date.strftime('%Y-%m-%d'),
                    'rooms_blocked': rooms_blocked,
                    'block_type': block_type,
                    'block_reason': block_reason,
                    'message': f"Room block created successfully. Reference: {block_reference}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Block creation failed: {str(e)}"
            }
    
    def release_room_block(self, block_reference: str, release_reason: str = "") -> Dict:
        """Release/cancel a room block to restore availability - FOR HOTEL STAFF ONLY."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get block details
                cursor.execute("""
                    SELECT block_status, rooms_blocked, block_type
                    FROM room_blocks
                    WHERE block_reference = ?
                """, (block_reference,))
                
                block = cursor.fetchone()
                if not block:
                    return {
                        'success': False,
                        'message': f"Block reference {block_reference} not found"
                    }
                
                current_status, rooms_blocked, block_type = block
                
                if current_status != 'ACTIVE':
                    return {
                        'success': False,
                        'message': f"Block {block_reference} is already {current_status}"
                    }
                
                # Release the block
                cursor.execute("""
                    UPDATE room_blocks 
                    SET block_status = 'RELEASED',
                        notes = COALESCE(notes, '') || 
                               CASE WHEN notes IS NOT NULL THEN ' | ' ELSE '' END ||
                               'RELEASED: ' || ?
                    WHERE block_reference = ?
                """, (release_reason or "Released by hotel staff", block_reference))
                
                conn.commit()
                
                return {
                    'success': True,
                    'block_reference': block_reference,
                    'rooms_released': rooms_blocked,
                    'block_type': block_type,
                    'message': f"Block {block_reference} released successfully"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Block release failed: {str(e)}"
            }
    
    def get_room_blocks(self, property_id: str, room_type_id: str = None, 
                       block_date: str = None, status: str = 'ACTIVE') -> List[Dict]:
        """Get room blocks for a property, room type, or date - FOR HOTEL STAFF ONLY."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT rb.block_reference, rb.property_id, rb.room_type_id, rb.block_date,
                           rb.rooms_blocked, rb.block_type, rb.block_reason, rb.blocked_by,
                           rb.block_status, rb.created_at, rb.expires_at, rb.notes,
                           h.hotel_name, rt.room_name
                    FROM room_blocks rb
                    JOIN hotels h ON rb.property_id = h.property_id
                    JOIN room_types rt ON rb.room_type_id = rt.room_type_id
                    WHERE rb.property_id = ?
                """
                params = [property_id]
                
                if room_type_id:
                    query += " AND rb.room_type_id = ?"
                    params.append(room_type_id)
                
                if block_date:
                    query += " AND rb.block_date = ?"
                    params.append(block_date)
                
                if status:
                    query += " AND rb.block_status = ?"
                    params.append(status)
                
                query += " ORDER BY rb.block_date, rb.created_at"
                
                cursor.execute(query, params)
                blocks = cursor.fetchall()
                
                result = []
                for block in blocks:
                    result.append({
                        'block_reference': block[0],
                        'property_id': block[1],
                        'room_type_id': block[2],
                        'block_date': block[3],
                        'rooms_blocked': block[4],
                        'block_type': block[5],
                        'block_reason': block[6],
                        'blocked_by': block[7],
                        'block_status': block[8],
                        'created_at': block[9],
                        'expires_at': block[10],
                        'notes': block[11],
                        'hotel_name': block[12],
                        'room_name': block[13]
                    })
                
                return result
                
        except Exception as e:
            print(f"Error getting room blocks: {e}")
            return []

# Interactive functions for hotel managers
def interactive_hotel_manager():
    """Interactive CLI for hotel managers to manage availability."""
    
    print("🏨 HOTEL AVAILABILITY MANAGEMENT SYSTEM")
    print("=" * 50)
    print("FOR HOTEL MANAGERS ONLY")
    print("Manage inventory, pricing, and room availability")
    
    manager = HotelAvailabilityManager()
    
    while True:
        print("\n📋 HOTEL MANAGER OPTIONS:")
        print("1. Add inventory for date range")
        print("2. Update pricing")
        print("3. Adjust inventory for specific date")
        print("4. View inventory report")
        print("5. Process booking confirmation")
        print("6. Cancel booking (restore inventory)")
        print("7. Exit")
        
        choice = input("\nChoose option (1-7): ").strip()
        
        if choice == '1':
            add_inventory_interactive(manager)
        elif choice == '2':
            update_pricing_interactive(manager)
        elif choice == '3':
            adjust_inventory_interactive(manager)
        elif choice == '4':
            view_inventory_report(manager)
        elif choice == '5':
            process_booking_interactive(manager)
        elif choice == '6':
            cancel_booking_interactive(manager)
        elif choice == '7':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

def add_inventory_interactive(manager: HotelAvailabilityManager):
    """Interactive inventory addition."""
    
    print("\n📦 ADD INVENTORY")
    print("-" * 20)
    
    property_id = input("Property ID: ")
    room_type_id = input("Room Type ID: ")
    start_date_str = input("Start date (YYYY-MM-DD): ")
    end_date_str = input("End date (YYYY-MM-DD): ")
    available_rooms = int(input("Available rooms per day: "))
    price_per_night = float(input("Price per night (RM): "))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        result = manager.add_inventory_date_range(
            property_id, room_type_id, start_date, end_date, available_rooms, price_per_night
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

def update_pricing_interactive(manager: HotelAvailabilityManager):
    """Interactive pricing update."""
    
    print("\n💰 UPDATE PRICING")
    print("-" * 20)
    
    property_id = input("Property ID: ")
    room_type_id = input("Room Type ID: ")
    start_date_str = input("Start date (YYYY-MM-DD): ")
    end_date_str = input("End date (YYYY-MM-DD): ")
    new_price = float(input("New price per night (RM): "))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        result = manager.update_pricing(property_id, room_type_id, start_date, end_date, new_price)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

def adjust_inventory_interactive(manager: HotelAvailabilityManager):
    """Interactive inventory adjustment."""
    
    print("\n🔧 ADJUST INVENTORY")
    print("-" * 20)
    
    property_id = input("Property ID: ")
    room_type_id = input("Room Type ID: ")
    stay_date_str = input("Stay date (YYYY-MM-DD): ")
    adjustment = int(input("Adjustment (+/- rooms): "))
    
    try:
        stay_date = datetime.strptime(stay_date_str, '%Y-%m-%d').date()
        
        result = manager.adjust_inventory(property_id, room_type_id, stay_date, adjustment)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

def view_inventory_report(manager: HotelAvailabilityManager):
    """View inventory report."""
    
    print("\n📊 INVENTORY REPORT")
    print("-" * 25)
    
    property_id = input("Property ID: ")
    start_date_str = input("Start date (YYYY-MM-DD): ")
    end_date_str = input("End date (YYYY-MM-DD): ")
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        report = manager.get_inventory_report(property_id, start_date, end_date)
        
        if report:
            print(f"\n📋 INVENTORY REPORT ({start_date} to {end_date}):")
            print("-" * 70)
            print(f"{'Date':<12} {'Room Type':<25} {'Available':<10} {'Price':<10}")
            print("-" * 70)
            
            for item in report:
                print(f"{item['stay_date']:<12} {item['room_name'][:24]:<25} "
                      f"{item['available_rooms']:<10} RM{item['current_price']:<9.2f}")
        else:
            print("❌ No inventory found for specified criteria")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

def process_booking_interactive(manager: HotelAvailabilityManager):
    """Process booking confirmation."""
    
    print("\n✅ PROCESS BOOKING CONFIRMATION")
    print("-" * 35)
    
    property_id = input("Property ID: ")
    room_type_id = input("Room Type ID: ")
    check_in_str = input("Check-in date (YYYY-MM-DD): ")
    check_out_str = input("Check-out date (YYYY-MM-DD): ")
    rooms_booked = int(input("Rooms booked: "))
    
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        result = manager.process_booking_confirmation(
            property_id, room_type_id, check_in, check_out, rooms_booked
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

def cancel_booking_interactive(manager: HotelAvailabilityManager):
    """Cancel booking and restore inventory."""
    
    print("\n❌ CANCEL BOOKING")
    print("-" * 20)
    
    property_id = input("Property ID: ")
    room_type_id = input("Room Type ID: ")
    check_in_str = input("Check-in date (YYYY-MM-DD): ")
    check_out_str = input("Check-out date (YYYY-MM-DD): ")
    rooms_to_restore = int(input("Rooms to restore: "))
    
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        result = manager.cancel_booking_restore_inventory(
            property_id, room_type_id, check_in, check_out, rooms_to_restore
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")

if __name__ == "__main__":
    interactive_hotel_manager() 
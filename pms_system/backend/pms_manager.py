#!/usr/bin/env python3
"""
PMS Manager - Consolidated Property Management System
Unified hotel operations management for LEON dashboard
"""

import sqlite3
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class PMSManager:
    """Consolidated Property Management System for hotel operations"""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    # ========================
    # HOTEL MANAGEMENT
    # ========================
    
    def get_all_hotels(self) -> List[Dict]:
        """Get all hotels in the system"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT property_id, hotel_name, city_name, state_name, country_name,
                           star_rating, address, phone, email, is_active, created_at
                    FROM hotels
                    ORDER BY hotel_name
                """)
                
                hotels = []
                for row in cursor.fetchall():
                    hotels.append({
                        'property_id': row[0],
                        'hotel_name': row[1],
                        'city_name': row[2],
                        'state_name': row[3],
                        'country_name': row[4],
                        'star_rating': row[5],
                        'address': row[6],
                        'phone': row[7],
                        'email': row[8],
                        'is_active': bool(row[9]),
                        'created_at': row[10]
                    })
                
                return hotels
        except Exception as e:
            print(f"Error getting hotels: {e}")
            return []
    
    def get_hotel_details(self, property_id: str) -> Dict:
        """Get detailed information about a specific hotel"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get hotel basic info
                cursor.execute("""
                    SELECT h.*, 
                           COUNT(DISTINCT rt.room_type_id) as room_types_count,
                           COUNT(DISTINCT CASE WHEN b.booking_status = 'CONFIRMED' THEN b.booking_id END) as active_bookings
                    FROM hotels h
                    LEFT JOIN room_types rt ON h.property_id = rt.property_id
                    LEFT JOIN bookings b ON h.property_id = b.property_id AND b.booking_status = 'CONFIRMED'
                    WHERE h.property_id = ?
                    GROUP BY h.property_id
                """, (property_id,))
                
                hotel_data = cursor.fetchone()
                if not hotel_data:
                    return {"success": False, "message": "Hotel not found"}
                
                return {
                    "success": True,
                    "hotel": {
                        'property_id': hotel_data[0],
                        'hotel_name': hotel_data[1],
                        'city_name': hotel_data[2],
                        'state_name': hotel_data[3],
                        'country_name': hotel_data[4],
                        'star_rating': hotel_data[5],
                        'address': hotel_data[6],
                        'phone': hotel_data[7],
                        'email': hotel_data[8],
                        'is_active': bool(hotel_data[9]),
                        'room_types_count': hotel_data[-2],
                        'active_bookings': hotel_data[-1]
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    # ========================
    # ROOM TYPE MANAGEMENT
    # ========================
    
    def get_room_types(self, property_id: str) -> List[Dict]:
        """Get all room types for a hotel"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT room_type_id, room_name, bed_type, view_type, max_occupancy,
                           room_size_sqm, total_rooms, base_price_per_night, amenities,
                           room_features, is_active
                    FROM room_types
                    WHERE property_id = ?
                    ORDER BY room_name
                """, (property_id,))
                
                room_types = []
                for row in cursor.fetchall():
                    room_types.append({
                        'room_type_id': row[0],
                        'room_name': row[1],
                        'bed_type': row[2],
                        'view_type': row[3],
                        'max_occupancy': row[4],
                        'room_size_sqm': row[5],
                        'total_rooms': row[6],
                        'base_price_per_night': row[7],
                        'amenities': row[8],
                        'room_features': row[9],
                        'is_active': bool(row[10])
                    })
                
                return room_types
        except Exception as e:
            print(f"Error getting room types: {e}")
            return []
    
    def create_room_type(self, property_id: str, room_data: dict) -> Dict:
        """Create a new room type for a hotel"""
        try:
            # Generate room_type_id from hotel and room name
            room_name = room_data.get("name", "").strip()
            if not room_name:
                return {"success": False, "message": "Room name is required"}
            
            # Create room_type_id (hotel_id_room_name in lowercase with underscores)
            room_type_id = f"{property_id}_{room_name.lower().replace(' ', '_').replace('-', '_')}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if room type already exists
                cursor.execute("SELECT room_type_id FROM room_types WHERE room_type_id = ?", (room_type_id,))
                if cursor.fetchone():
                    return {"success": False, "message": "Room type with this name already exists"}
                
                # Insert new room type
                cursor.execute("""
                    INSERT INTO room_types (
                        room_type_id, property_id, room_name, bed_type, 
                        max_occupancy, base_price_per_night, total_rooms, 
                        room_size_sqm, view_type, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """, (
                    room_type_id, property_id, room_name,
                    room_data.get("bed_type", "King"),
                    room_data.get("max_occupancy", 2),
                    room_data.get("base_price", 100.0),
                    room_data.get("total_rooms", 10),
                    room_data.get("room_size_sqm"),
                    room_data.get("view_type", "City")
                ))
                
                conn.commit()
                
                return {
                    "success": True, 
                    "room_type_id": room_type_id,
                    "message": f"Room type '{room_name}' created successfully"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error creating room type: {str(e)}"}

    def update_room_type(self, property_id: str, room_type_id: str, room_data: dict) -> Dict:
        """Update an existing room type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if room type exists
                cursor.execute("SELECT room_type_id FROM room_types WHERE room_type_id = ? AND property_id = ?", 
                             (room_type_id, property_id))
                if not cursor.fetchone():
                    return {"success": False, "message": "Room type not found"}
                
                # Update room type
                cursor.execute("""
                    UPDATE room_types 
                    SET room_name = ?, bed_type = ?, max_occupancy = ?, 
                        base_price_per_night = ?, total_rooms = ?, 
                        room_size_sqm = ?, view_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE room_type_id = ? AND property_id = ?
                """, (
                    room_data.get("room_name"),
                    room_data.get("bed_type"),
                    room_data.get("max_occupancy"),
                    room_data.get("base_price_per_night"),
                    room_data.get("total_rooms"),
                    room_data.get("room_size_sqm"),
                    room_data.get("view_type"),
                    room_type_id, property_id
                ))
                
                conn.commit()
                
                return {
                    "success": True,
                    "message": f"Room type updated successfully"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error updating room type: {str(e)}"}

    def delete_room_type(self, property_id: str, room_type_id: str) -> Dict:
        """Delete a room type (soft delete by setting is_active = 0)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if room type exists
                cursor.execute("SELECT room_type_id FROM room_types WHERE room_type_id = ? AND property_id = ?", 
                             (room_type_id, property_id))
                if not cursor.fetchone():
                    return {"success": False, "message": "Room type not found"}
                
                # Check if there are active bookings for this room type
                cursor.execute("""
                    SELECT COUNT(*) FROM bookings 
                    WHERE room_type_id = ? AND booking_status IN ('CONFIRMED', 'CHECKED_IN')
                """, (room_type_id,))
                active_bookings = cursor.fetchone()[0]
                
                if active_bookings > 0:
                    return {"success": False, "message": f"Cannot delete room type with {active_bookings} active bookings"}
                
                # Soft delete room type
                cursor.execute("""
                    UPDATE room_types 
                    SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE room_type_id = ? AND property_id = ?
                """, (room_type_id, property_id))
                
                conn.commit()
                
                return {
                    "success": True,
                    "message": "Room type deleted successfully"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error deleting room type: {str(e)}"}

    # ========================
    # INVENTORY MANAGEMENT
    # ========================
    
    def get_inventory_status(self, property_id: str, room_type_id: str = None, 
                           start_date: str = None, end_date: str = None) -> Dict:
        """Get inventory status for hotel/room type"""
        try:
            if not start_date:
                start_date = date.today().strftime('%Y-%m-%d')
            if not end_date:
                end_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if room_type_id:
                    # Specific room type
                    cursor.execute("""
                        SELECT ri.stay_date, ri.available_rooms, ri.current_price,
                               rt.room_name, rt.total_rooms,
                               COALESCE(SUM(b.rooms_booked), 0) as booked_rooms
                        FROM room_inventory ri
                        JOIN room_types rt ON ri.property_id = rt.property_id 
                                           AND ri.room_type_id = rt.room_type_id
                        LEFT JOIN bookings b ON ri.property_id = b.property_id 
                                             AND ri.room_type_id = b.room_type_id
                                             AND b.booking_status = 'CONFIRMED'
                                             AND b.check_in_date <= ri.stay_date 
                                             AND b.check_out_date > ri.stay_date
                        WHERE ri.property_id = ? AND ri.room_type_id = ?
                              AND ri.stay_date BETWEEN ? AND ?
                        GROUP BY ri.stay_date, ri.available_rooms, ri.current_price, rt.room_name, rt.total_rooms
                        ORDER BY ri.stay_date
                    """, (property_id, room_type_id, start_date, end_date))
                else:
                    # All room types
                    cursor.execute("""
                        SELECT ri.stay_date, ri.room_type_id, ri.available_rooms, ri.current_price,
                               rt.room_name, rt.total_rooms,
                               COALESCE(SUM(b.rooms_booked), 0) as booked_rooms
                        FROM room_inventory ri
                        JOIN room_types rt ON ri.property_id = rt.property_id 
                                           AND ri.room_type_id = rt.room_type_id
                        LEFT JOIN bookings b ON ri.property_id = b.property_id 
                                             AND ri.room_type_id = b.room_type_id
                                             AND b.booking_status = 'CONFIRMED'
                                             AND b.check_in_date <= ri.stay_date 
                                             AND b.check_out_date > ri.stay_date
                        WHERE ri.property_id = ? AND ri.stay_date BETWEEN ? AND ?
                        GROUP BY ri.stay_date, ri.room_type_id, ri.available_rooms, ri.current_price, rt.room_name, rt.total_rooms
                        ORDER BY ri.stay_date, rt.room_name
                    """, (property_id, start_date, end_date))
                
                inventory_data = []
                for row in cursor.fetchall():
                    if room_type_id:
                        inventory_data.append({
                            'date': row[0],
                            'available_rooms': row[1],
                            'current_price': row[2],
                            'room_name': row[3],
                            'total_rooms': row[4],
                            'booked_rooms': row[5],
                            'sellable_rooms': row[1] - row[5]
                        })
                    else:
                        inventory_data.append({
                            'date': row[0],
                            'room_type_id': row[1],
                            'available_rooms': row[2],
                            'current_price': row[3],
                            'room_name': row[4],
                            'total_rooms': row[5],
                            'booked_rooms': row[6],
                            'sellable_rooms': row[2] - row[6]
                        })
                
                return {"success": True, "inventory": inventory_data}
                
        except Exception as e:
            return {"success": False, "message": f"Error getting inventory: {str(e)}"}
    
    def update_inventory(self, property_id: str, room_type_id: str, 
                        start_date: str, end_date: str, available_rooms: int = None,
                        current_price: float = None, add_rooms: int = None) -> Dict:
        """Update room inventory"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                updated_dates = []
                current_date = start
                
                while current_date <= end:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    if add_rooms is not None:
                        # Add rooms to existing inventory
                        cursor.execute("""
                            UPDATE room_inventory 
                            SET available_rooms = available_rooms + ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                        """, (add_rooms, property_id, room_type_id, date_str))
                    else:
                        # Set specific values
                        update_fields = []
                        values = []
                        
                        if available_rooms is not None:
                            update_fields.append("available_rooms = ?")
                            values.append(available_rooms)
                        
                        if current_price is not None:
                            update_fields.append("current_price = ?")
                            values.append(current_price)
                        
                        if update_fields:
                            update_fields.append("updated_at = CURRENT_TIMESTAMP")
                            values.extend([property_id, room_type_id, date_str])
                            
                            cursor.execute(f"""
                                UPDATE room_inventory 
                                SET {', '.join(update_fields)}
                                WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                            """, values)
                    
                    if cursor.rowcount > 0:
                        updated_dates.append(date_str)
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                return {
                    "success": True,
                    "dates_updated": len(updated_dates),
                    "updated_dates": updated_dates,
                    "message": f"Inventory updated for {len(updated_dates)} dates"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error updating inventory: {str(e)}"}
    
    # ========================
    # BOOKING MANAGEMENT
    # ========================
    
    def get_bookings(self, property_id: str = None, booking_status: str = None,
                    start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get bookings with filters"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT b.booking_id, b.booking_reference, h.hotel_name, rt.room_name,
                           b.guest_name, b.guest_email, b.guest_phone,
                           b.check_in_date, b.check_out_date, b.nights, b.rooms_booked,
                           b.total_price, b.currency, b.booking_status, b.payment_status,
                           b.special_requests, b.booked_at, b.updated_at
                    FROM bookings b
                    JOIN hotels h ON b.property_id = h.property_id
                    JOIN room_types rt ON b.room_type_id = rt.room_type_id
                    WHERE 1=1
                """
                params = []
                
                if property_id:
                    query += " AND b.property_id = ?"
                    params.append(property_id)
                
                if booking_status:
                    query += " AND b.booking_status = ?"
                    params.append(booking_status)
                
                if start_date:
                    query += " AND b.check_in_date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND b.check_out_date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY b.booked_at DESC"
                
                cursor.execute(query, params)
                
                bookings = []
                for row in cursor.fetchall():
                    bookings.append({
                        'booking_id': row[0],
                        'booking_reference': row[1],
                        'hotel_name': row[2],
                        'room_name': row[3],
                        'guest_name': row[4],
                        'guest_email': row[5],
                        'guest_phone': row[6],
                        'check_in_date': row[7],
                        'check_out_date': row[8],
                        'nights': row[9],
                        'rooms_booked': row[10],
                        'total_price': row[11],
                        'currency': row[12],
                        'booking_status': row[13],
                        'payment_status': row[14],
                        'special_requests': row[15],
                        'booked_at': row[16],
                        'updated_at': row[17]
                    })
                
                return bookings
        except Exception as e:
            print(f"Error getting bookings: {e}")
            return []
    
    def cancel_booking(self, booking_reference: str, cancellation_reason: str = "") -> Dict:
        """Cancel a booking and restore inventory"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get booking details
                cursor.execute("""
                    SELECT booking_status, property_id, room_type_id, check_in_date, 
                           check_out_date, rooms_booked, guest_name
                    FROM bookings
                    WHERE booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                if not booking:
                    return {"success": False, "message": "Booking not found"}
                
                current_status, property_id, room_type_id, check_in_str, check_out_str, rooms_booked, guest_name = booking
                
                if current_status == 'CANCELLED':
                    return {"success": False, "message": "Booking already cancelled"}
                
                # Restore inventory
                check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
                
                current_date = check_in_date
                restored_dates = []
                
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET available_rooms = available_rooms + ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (rooms_booked, property_id, room_type_id, date_str))
                    
                    if cursor.rowcount > 0:
                        restored_dates.append(date_str)
                    
                    current_date += timedelta(days=1)
                
                # Update booking status
                cursor.execute("""
                    UPDATE bookings 
                    SET booking_status = 'CANCELLED',
                        special_requests = COALESCE(special_requests, '') || 
                                         CASE WHEN special_requests IS NOT NULL THEN ' | ' ELSE '' END ||
                                         'CANCELLED: ' || ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE booking_reference = ?
                """, (cancellation_reason or "Cancelled by hotel", booking_reference))
                
                conn.commit()
                
                return {
                    "success": True,
                    "booking_reference": booking_reference,
                    "guest_name": guest_name,
                    "inventory_restored": len(restored_dates),
                    "message": f"Booking cancelled and {rooms_booked} rooms restored for {len(restored_dates)} dates"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error cancelling booking: {str(e)}"}
    
    def update_booking_status(self, booking_id: int, booking_status: str = None, 
                            payment_status: str = None, notes: str = "") -> Dict:
        """Update booking status and/or payment status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if booking exists
                cursor.execute("SELECT booking_id, booking_reference, guest_name FROM bookings WHERE booking_id = ?", 
                             (booking_id,))
                booking = cursor.fetchone()
                if not booking:
                    return {"success": False, "message": "Booking not found"}
                
                _, booking_reference, guest_name = booking
                
                # Build update query dynamically
                update_fields = []
                update_values = []
                
                if booking_status:
                    update_fields.append("booking_status = ?")
                    update_values.append(booking_status)
                
                if payment_status:
                    update_fields.append("payment_status = ?")
                    update_values.append(payment_status)
                
                # Add notes to special_requests if provided
                if notes:
                    update_fields.append("""special_requests = COALESCE(special_requests, '') || 
                                        CASE WHEN special_requests IS NOT NULL AND special_requests != '' THEN ' | ' ELSE '' END ||
                                        'STATUS UPDATE: ' || ?""")
                    update_values.append(notes)
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                if not update_fields or len(update_fields) == 1:  # Only timestamp update
                    return {"success": False, "message": "No valid updates provided"}
                
                # Execute update
                update_values.append(booking_id)
                cursor.execute(f"""
                    UPDATE bookings 
                    SET {', '.join(update_fields)}
                    WHERE booking_id = ?
                """, update_values)
                
                conn.commit()
                
                return {
                    "success": True,
                    "booking_id": booking_id,
                    "booking_reference": booking_reference,
                    "guest_name": guest_name,
                    "message": "Booking status updated successfully"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error updating booking status: {str(e)}"}
    
    # ========================
    # ANALYTICS & REPORTING
    # ========================
    
    def get_hotel_analytics(self, property_id: str, days: int = 30) -> Dict:
        """Get hotel analytics and statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
                end_date = date.today().strftime('%Y-%m-%d')
                
                # Booking statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_bookings,
                        COUNT(CASE WHEN booking_status = 'CONFIRMED' THEN 1 END) as confirmed_bookings,
                        COUNT(CASE WHEN booking_status = 'CANCELLED' THEN 1 END) as cancelled_bookings,
                        SUM(CASE WHEN booking_status = 'CONFIRMED' THEN total_price ELSE 0 END) as total_revenue,
                        SUM(CASE WHEN booking_status = 'CONFIRMED' THEN rooms_booked ELSE 0 END) as total_room_nights
                    FROM bookings
                    WHERE property_id = ? AND booked_at >= ?
                """, (property_id, start_date))
                
                booking_stats = cursor.fetchone()
                
                # Occupancy rate
                cursor.execute("""
                    SELECT 
                        SUM(rt.total_rooms) as total_room_capacity,
                        SUM(ri.available_rooms) as total_available,
                        COUNT(DISTINCT ri.stay_date) as days_counted
                    FROM room_inventory ri
                    JOIN room_types rt ON ri.property_id = rt.property_id 
                                       AND ri.room_type_id = rt.room_type_id
                    WHERE ri.property_id = ? AND ri.stay_date BETWEEN ? AND ?
                """, (property_id, start_date, end_date))
                
                capacity_stats = cursor.fetchone()
                
                # Room type performance
                cursor.execute("""
                    SELECT rt.room_name, 
                           COUNT(b.booking_id) as bookings,
                           SUM(b.total_price) as revenue
                    FROM room_types rt
                    LEFT JOIN bookings b ON rt.property_id = b.property_id 
                                         AND rt.room_type_id = b.room_type_id
                                         AND b.booking_status = 'CONFIRMED'
                                         AND b.booked_at >= ?
                    WHERE rt.property_id = ?
                    GROUP BY rt.room_type_id, rt.room_name
                    ORDER BY revenue DESC
                """, (start_date, property_id))
                
                room_performance = []
                for row in cursor.fetchall():
                    room_performance.append({
                        'room_name': row[0],
                        'bookings': row[1] or 0,
                        'revenue': row[2] or 0
                    })
                
                # Calculate occupancy rate
                total_capacity = capacity_stats[0] or 1
                total_available = capacity_stats[1] or 0
                days_counted = capacity_stats[2] or 1
                
                occupancy_rate = ((total_capacity - total_available) / total_capacity) * 100 if total_capacity > 0 else 0
                
                return {
                    "success": True,
                    "analytics": {
                        "period_days": days,
                        "bookings": {
                            "total": booking_stats[0] or 0,
                            "confirmed": booking_stats[1] or 0,
                            "cancelled": booking_stats[2] or 0,
                            "conversion_rate": (booking_stats[1] / booking_stats[0] * 100) if booking_stats[0] > 0 else 0
                        },
                        "revenue": {
                            "total": booking_stats[3] or 0,
                            "average_per_booking": (booking_stats[3] / booking_stats[1]) if booking_stats[1] > 0 else 0
                        },
                        "occupancy": {
                            "rate": round(occupancy_rate, 2),
                            "room_nights_sold": booking_stats[4] or 0,
                            "total_capacity": total_capacity * days_counted
                        },
                        "room_performance": room_performance
                    }
                }
                
        except Exception as e:
            return {"success": False, "message": f"Error getting analytics: {str(e)}"}

# Global PMS manager instance
pms_manager = PMSManager() 
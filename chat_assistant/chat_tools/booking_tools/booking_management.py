#!/usr/bin/env python3
"""
Customer Booking Management System - Relational Database Approach
ELLA's booking interface - CUSTOMER FUNCTIONS ONLY
Uses proper database relationships to maintain inventory synchronization automatically.
Available rooms = total_rooms - SUM(confirmed_bookings) - SUM(active_blocks)
"""

import sqlite3
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool
import json
import time

class BookingConfirmationManager:
    """Manages customer bookings using proper database relationships."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def generate_booking_reference(self, property_id: str, room_type_id: str, 
                                  check_in_date: date, check_out_date: date, 
                                  guest_phone: str, guest_name: str) -> str:
        """
        Generate simple, clean booking reference in format:
        hotelname_checkindate_booking1
        
        Example: Grand Hyatt Kuala Lumpur_20250607_booking1
        
        Uses full hotel name from database (self-explanatory, no abbreviations)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get full hotel name from database
                cursor.execute("""
                    SELECT h.hotel_name
                    FROM hotels h
                    WHERE h.property_id = ?
                """, (property_id,))
                
                result = cursor.fetchone()
                if not result:
                    # Fallback if lookup fails
                    hotel_name = property_id
                else:
                    hotel_name = result[0]
                
                # Format check-in date as YYYYMMDD
                checkin_str = check_in_date.strftime('%Y%m%d')
                
                # Find sequence number for today (how many bookings created today)
                today = datetime.now().date()
                cursor.execute("""
                    SELECT COUNT(*) + 1 as sequence
                    FROM bookings 
                    WHERE DATE(booked_at) = ? AND booking_status != 'CANCELLED'
                """, (today.strftime('%Y-%m-%d'),))
                
                sequence = cursor.fetchone()[0]
                
                # Build the simple booking reference
                # Format: hotelname_checkindate_bookingN
                reference = f"{hotel_name}_{checkin_str}_booking{sequence}"
                
                print(f"📋 Generated simple booking reference: {reference}")
                return reference
                
        except Exception as e:
            print(f"❌ Error generating booking reference: {e}")
            # Fallback to simple format with timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M')
            return f"booking_{timestamp}_fallback"
    
    def check_availability(self, property_id: str, room_type_id: str, 
                          check_in_date: date, check_out_date: date, 
                          rooms_needed: int = 1) -> Dict:
        """
        Check availability using database relationships for CUSTOMERS.
        Available rooms = total_rooms - SUM(confirmed_bookings) - SUM(active_blocks)
        """
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
                        'available': False,
                        'message': f"Room type not found",
                        'min_available': 0
                    }
                
                base_rooms = room_type_row[0]
                
                current_date = check_in_date
                availability_details = []
                min_available = float('inf')
                total_price = 0
                nights = 0
                
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Get pricing for this date
                    cursor.execute("""
                        SELECT current_price 
                        FROM room_inventory 
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, date_str))
                    
                    price_row = cursor.fetchone()
                    if not price_row:
                        return {
                            'available': False,
                            'message': f"No inventory record for {date_str}",
                            'min_available': 0
                        }
                    
                    price = price_row[0]
                    
                    # Calculate confirmed bookings for this date
                    cursor.execute("""
                        SELECT COALESCE(SUM(rooms_booked), 0) as booked_rooms
                        FROM bookings 
                        WHERE property_id = ? AND room_type_id = ? 
                        AND booking_status = 'CONFIRMED'
                        AND check_in_date <= ? AND check_out_date > ?
                    """, (property_id, room_type_id, date_str, date_str))
                    
                    booked_rooms = cursor.fetchone()[0]
                    
                    # Calculate active room blocks for this date (managed by hotel staff)
                    cursor.execute("""
                        SELECT COALESCE(SUM(rooms_blocked), 0) as blocked_rooms
                        FROM room_blocks 
                        WHERE property_id = ? AND room_type_id = ? 
                        AND block_status = 'ACTIVE'
                        AND block_date = ?
                        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    """, (property_id, room_type_id, date_str))
                    
                    blocked_rooms = cursor.fetchone()[0]
                    
                    # Calculate actual available rooms: total - bookings - blocks
                    actual_available = base_rooms - booked_rooms - blocked_rooms
                    
                    availability_details.append({
                        'date': date_str,
                        'base_rooms': base_rooms,
                        'booked_rooms': booked_rooms,
                        'blocked_rooms': blocked_rooms,
                        'available_rooms': actual_available,
                        'price': price
                    })
                    
                    if actual_available < rooms_needed:
                        return {
                            'available': False,
                            'message': f"Insufficient rooms on {date_str}. Available: {actual_available}, Needed: {rooms_needed}",
                            'min_available': actual_available,
                            'availability_details': availability_details
                        }
                    
                    min_available = min(min_available, actual_available)
                    total_price += price * rooms_needed
                    nights += 1
                    current_date += timedelta(days=1)
                
                return {
                    'available': True,
                    'min_available': min_available,
                    'total_price': total_price,
                    'nights': nights,
                    'avg_nightly_price': total_price / nights if nights > 0 else 0,
                    'availability_details': availability_details
                }
                
        except Exception as e:
            return {
                'available': False,
                'message': f"Error checking availability: {str(e)}"
            }
    
    def update_room_inventory(self, property_id: str, room_type_id: str, 
                             check_in_date: date, check_out_date: date, 
                             rooms_change: int, operation: str = "booking") -> Dict:
        """
        Update room inventory for booking/cancellation.
        rooms_change: positive for reducing inventory (booking), negative for increasing (cancellation)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = check_in_date
                updated_dates = []
                
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Check if inventory record exists for this date
                    cursor.execute("""
                        SELECT available_rooms FROM room_inventory 
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, date_str))
                    
                    inventory_row = cursor.fetchone()
                    
                    if inventory_row:
                        current_available = inventory_row[0]
                        new_available = current_available - rooms_change
                        
                        # Prevent negative inventory
                        if new_available < 0:
                            return {
                                'success': False,
                                'message': f"Cannot reduce inventory below 0 for date {date_str}. Current: {current_available}, Requested reduction: {rooms_change}",
                                'updated_dates': updated_dates
                            }
                        
                        # Update inventory
                        cursor.execute("""
                            UPDATE room_inventory 
                            SET available_rooms = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                        """, (new_available, property_id, room_type_id, date_str))
                        
                        updated_dates.append({
                            'date': date_str,
                            'old_available': current_available,
                            'new_available': new_available,
                            'change': -rooms_change
                        })
                    else:
                        return {
                            'success': False,
                            'message': f"No inventory record found for {date_str}",
                            'updated_dates': updated_dates
                        }
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                print(f"✅ INVENTORY UPDATED: {operation} - {rooms_change} rooms for {len(updated_dates)} dates")
                for update in updated_dates:
                    print(f"   📅 {update['date']}: {update['old_available']} → {update['new_available']} rooms")
                
                return {
                    'success': True,
                    'message': f"Inventory updated for {len(updated_dates)} dates",
                    'updated_dates': updated_dates
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error updating inventory: {str(e)}",
                'updated_dates': []
            }
            
    def reserve_room_inventory(self, property_id: str, room_type_id: str, 
                              check_in_date: date, check_out_date: date, 
                              rooms_reserved: int, operation: str = "reservation") -> Dict:
        """
        Reserve inventory for PRE_CONFIRMED bookings without deducting from available_rooms.
        Reservations prevent new bookings but don't permanently reduce inventory.
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate date range for reservation
                current_date = check_in_date
                updated_dates = []
                
                while current_date < check_out_date:
                    # Check if enough rooms available (available - already_reserved >= new_reservation)
                    cursor.execute("""
                        SELECT stay_date, available_rooms, COALESCE(reserved_rooms, 0) as reserved_rooms
                        FROM room_inventory 
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, current_date.strftime('%Y-%m-%d')))
                    
                    inventory_row = cursor.fetchone()
                    if not inventory_row:
                        return {
                            'success': False,
                            'message': f"No inventory record for {current_date}"
                        }
                    
                    stay_date, available_rooms, current_reserved = inventory_row
                    truly_available = available_rooms - current_reserved
                    
                    if truly_available < rooms_reserved:
                        return {
                            'success': False,
                            'message': f"Insufficient inventory on {current_date}: need {rooms_reserved}, available {truly_available} (total: {available_rooms}, reserved: {current_reserved})"
                        }
                    
                    # Reserve the rooms
                    new_reserved = current_reserved + rooms_reserved
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET reserved_rooms = ?, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (new_reserved, property_id, room_type_id, current_date.strftime('%Y-%m-%d')))
                    
                    updated_dates.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'reserved_change': f"{current_reserved} → {new_reserved}",
                        'available_remaining': available_rooms - new_reserved
                    })
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                
                print(f"🔒 INVENTORY RESERVED: {operation} - {rooms_reserved} rooms for {len(updated_dates)} dates")
                for update in updated_dates:
                    print(f"   📅 {update['date']}: reserved {update['reserved_change']}, available: {update['available_remaining']}")
                
                return {
                    'success': True,
                    'operation': operation,
                    'rooms_reserved': rooms_reserved,
                    'dates_affected': len(updated_dates),
                    'reserved_dates': updated_dates,
                    'message': f"Successfully reserved {rooms_reserved} rooms for {len(updated_dates)} dates"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Inventory reservation failed: {str(e)}"
            }
    
    def create_confirmed_booking(self, property_id: str, room_type_id: str, 
                               guest_name: str, check_in_date: date, check_out_date: date,
                               guest_email: Optional[str] = None,
                               guest_phone: Optional[str] = None,
                               rooms_booked: int = 1, total_price: float = 0.0,
                               special_requests: Optional[str] = None,
                               guest_id: Optional[str] = None) -> Dict:
        """Create a confirmed booking using database relationships."""
        
        try:
            # Generate guest_id if not provided
            if not guest_id:
                guest_id = str(uuid.uuid4())[:8].upper()
            
            booking_reference = self.generate_booking_reference(
                property_id=property_id,
                room_type_id=room_type_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_phone=guest_phone or "",
                guest_name=guest_name
            )
            nights = (check_out_date - check_in_date).days
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify hotel and room type exist
                cursor.execute("""
                    SELECT h.hotel_name, rt.room_name, rt.base_price_per_night, h.city_name, h.state_name, h.address, h.phone
                    FROM hotels h
                    JOIN room_types rt ON h.property_id = rt.property_id
                    WHERE h.property_id = ? AND rt.room_type_id = ? AND h.is_active = 1 AND rt.is_active = 1
                """, (property_id, room_type_id))
                
                hotel_data = cursor.fetchone()
                if not hotel_data:
                    return {
                        'success': False,
                        'message': "Hotel or room type not found or inactive"
                    }
                
                hotel_name, room_name, base_price, city_name, state_name, address, hotel_phone = hotel_data
                
                # Check availability using database relationships
                availability = self.check_availability(
                    property_id=property_id,
                    room_type_id=room_type_id,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    rooms_needed=rooms_booked
                )
                
                if not availability['available']:
                    return {
                        'success': False,
                        'message': availability['message']
                    }
                
                # Calculate total price if not provided
                if total_price == 0.0:
                    total_price = availability['total_price']
                
                # 🚀 REAL-TIME INVENTORY UPDATE: Reduce available rooms
                inventory_update = self.update_room_inventory(
                    property_id=property_id,
                    room_type_id=room_type_id,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    rooms_change=rooms_booked,  # Positive to reduce inventory
                    operation="booking_confirmation"
                )
                
                if not inventory_update['success']:
                    return {
                        'success': False,
                        'message': f"Inventory update failed: {inventory_update['message']}"
                    }
                
                # Create confirmed booking record with inventory deduction
                cursor.execute("""
                    INSERT INTO bookings (
                        booking_reference, property_id, room_type_id, guest_name, 
                        guest_email, guest_phone, check_in_date, check_out_date,
                        nights, rooms_booked, total_price, booking_status, payment_status,
                        special_requests, booked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', 'UNPAID', ?, CURRENT_TIMESTAMP)
                """, (
                    booking_reference, property_id, room_type_id, guest_name,
                    guest_email, guest_phone, check_in_date.strftime('%Y-%m-%d'),
                    check_out_date.strftime('%Y-%m-%d'), nights, rooms_booked,
                    total_price, special_requests
                ))
                
                conn.commit()
                
                print(f"✅ BOOKING CONFIRMED: {booking_reference}")
                print(f"   📋 Reference: {booking_reference}")
                print(f"   🏨 Hotel: {hotel_name}")
                print(f"   👤 Guest: {guest_name}")
                print(f"   📅 Dates: {check_in_date} → {check_out_date}")
                print(f"   🛏️ Rooms: {rooms_booked}")
                print(f"   💰 Total: RM{total_price}")
                
                # Don't generate PDF immediately - will be generated on-demand
                pdf_available = True
                try:
                    # Test that PDF generation will work by checking if we have required data
                    from .pdf_generator import generate_temp_booking_pdf
                    pdf_available = True
                    print("PDF generation available for on-demand creation")
                except ImportError as pdf_error:
                    print(f"PDF generation not available: {pdf_error}")
                    pdf_available = False
                
                return {
                    'success': True,
                    'booking_reference': booking_reference,
                    'hotel_name': hotel_name,
                    'room_name': room_name,
                    'guest_name': guest_name,
                    'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                    'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                    'nights': nights,
                    'rooms_booked': rooms_booked,
                    'total_price': total_price,
                    'availability_details': availability['availability_details'],
                    'pdf_available': pdf_available,
                    'pdf_url': f"/booking-confirmation/{booking_reference}" if pdf_available else None,
                    'message': f"Booking confirmed! Reference: {booking_reference}" + 
                              (f" | PDF available: /booking-confirmation/{booking_reference}" if pdf_available else "")
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Booking creation failed: {str(e)}"
            }
            

            

    
    def get_booking_status(self, booking_reference: str) -> Dict:
        """Get booking status and details."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT b.booking_id, b.booking_reference, h.hotel_name, rt.room_name,
                           b.guest_name, b.guest_email, b.guest_phone,
                           b.check_in_date, b.check_out_date, b.nights, b.rooms_booked,
                           b.total_price, b.currency, b.booking_status, b.payment_status,
                           b.special_requests, b.booked_at, b.updated_at,
                           h.city_name, h.state_name, h.address, h.phone as hotel_phone
                    FROM bookings b
                    JOIN hotels h ON b.property_id = h.property_id
                    JOIN room_types rt ON b.room_type_id = rt.room_type_id
                    WHERE b.booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                if not booking:
                    return {
                        'success': False,
                        'message': f"Booking reference {booking_reference} not found"
                    }
                
                (booking_id, booking_ref, hotel_name, room_name, guest_name, guest_email, guest_phone,
                 check_in, check_out, nights, rooms_booked, total_price, currency, booking_status,
                 payment_status, special_requests, booked_at, updated_at, city_name, state_name,
                 address, hotel_phone) = booking
                
                return {
                    'success': True,
                    'booking_reference': booking_ref,
                    'booking_status': booking_status,
                    'payment_status': payment_status,
                    'hotel_name': hotel_name,
                    'room_name': room_name,
                    'guest_name': guest_name,
                    'guest_email': guest_email,
                    'guest_phone': guest_phone,
                    'check_in_date': check_in,
                    'check_out_date': check_out,
                    'nights': nights,
                    'rooms_booked': rooms_booked,
                    'total_price': total_price,
                    'currency': currency,
                    'special_requests': special_requests,
                    'hotel_location': f"{city_name}, {state_name}",
                    'hotel_address': address,
                    'hotel_phone': hotel_phone,
                    'booked_at': booked_at,
                    'updated_at': updated_at
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error retrieving booking: {str(e)}"
            }
    
    def cancel_booking(self, booking_reference: str, cancellation_reason: str = "") -> Dict:
        """Cancel a booking and restore inventory."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get booking details first
                cursor.execute("""
                    SELECT booking_status, property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                    FROM bookings
                    WHERE booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                if not booking:
                    return {
                        'success': False,
                        'message': f"Booking {booking_reference} not found"
                    }
                
                current_status, property_id, room_type_id, check_in_str, check_out_str, rooms_booked = booking
                
                if current_status == 'CANCELLED':
                    return {
                        'success': False,
                        'message': f"Booking {booking_reference} is already cancelled"
                    }
                
                # Convert date strings to date objects
                check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
                
                # 🚀 REAL-TIME INVENTORY UPDATE: Restore available rooms
                inventory_update = self.update_room_inventory(
                    property_id=property_id,
                    room_type_id=room_type_id,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    rooms_change=-rooms_booked,  # Negative to increase inventory
                    operation="booking_cancellation"
                )
                
                if not inventory_update['success']:
                    return {
                        'success': False,
                        'message': f"Inventory restoration failed: {inventory_update['message']}"
                    }
                
                # Update booking status
                cursor.execute("""
                    UPDATE bookings 
                    SET booking_status = 'CANCELLED', 
                        special_requests = COALESCE(special_requests, '') || 
                                         CASE WHEN special_requests IS NOT NULL THEN ' | ' ELSE '' END ||
                                         'CANCELLED: ' || ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE booking_reference = ?
                """, (cancellation_reason or "Cancelled by customer", booking_reference))
                
                conn.commit()
                
                print(f"❌ BOOKING CANCELLED: {booking_reference}")
                print(f"   🔄 Inventory restored: {rooms_booked} rooms")
                print(f"   📅 Dates affected: {check_in_date} → {check_out_date}")
                
                return {
                    'success': True,
                    'booking_reference': booking_reference,
                    'inventory_restored': inventory_update['updated_dates'],
                    'message': f"Booking {booking_reference} cancelled and inventory restored"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Cancellation failed: {str(e)}"
            }
    
    def get_guest_bookings(self, guest_name: str, guest_email: Optional[str] = None) -> List[Dict]:
        """Get all bookings for a guest."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if guest_email:
                    cursor.execute("""
                        SELECT b.booking_reference, b.booking_status, h.hotel_name, rt.room_name,
                               b.check_in_date, b.check_out_date, b.nights, b.rooms_booked,
                               b.total_price, b.currency, b.booked_at
                        FROM bookings b
                        JOIN hotels h ON b.property_id = h.property_id
                        JOIN room_types rt ON b.room_type_id = rt.room_type_id
                        WHERE (b.guest_name = ? OR b.guest_email = ?)
                        ORDER BY b.booked_at DESC
                    """, (guest_name, guest_email))
                else:
                    cursor.execute("""
                        SELECT b.booking_reference, b.booking_status, h.hotel_name, rt.room_name,
                               b.check_in_date, b.check_out_date, b.nights, b.rooms_booked,
                               b.total_price, b.currency, b.booked_at
                        FROM bookings b
                        JOIN hotels h ON b.property_id = h.property_id
                        JOIN room_types rt ON b.room_type_id = rt.room_type_id
                        WHERE b.guest_name = ?
                        ORDER BY b.booked_at DESC
                    """, (guest_name,))
                
                bookings = cursor.fetchall()
                
                result = []
                for booking in bookings:
                    result.append({
                        'booking_reference': booking[0],
                        'booking_status': booking[1],
                        'hotel_name': booking[2],
                        'room_name': booking[3],
                        'check_in_date': booking[4],
                        'check_out_date': booking[5],
                        'nights': booking[6],
                        'rooms_booked': booking[7],
                        'total_price': booking[8],
                        'currency': booking[9],
                        'booked_at': booking[10]
                    })
                
                return result
                
        except Exception as e:
            print(f"Error getting guest bookings: {e}")
            return []
    
    def check_availability_excluding_booking(self, property_id: str, room_type_id: str, 
                                           check_in_date: date, check_out_date: date, 
                                           rooms_needed: int, exclude_booking_id: int) -> Dict:
        """
        Check availability excluding a specific booking (for modifications).
        Available rooms = total_rooms - (confirmed_bookings - excluded_booking) - active_blocks
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get base room count
                cursor.execute("""
                    SELECT total_rooms FROM room_types
                    WHERE property_id = ? AND room_type_id = ? AND is_active = 1
                """, (property_id, room_type_id))
                
                room_type_row = cursor.fetchone()
                if not room_type_row:
                    return {
                        'available': False,
                        'message': f"Room type not found"
                    }
                
                base_rooms = room_type_row[0]
                
                current_date = check_in_date
                total_price = 0
                nights = 0
                min_available = float('inf')
                availability_details = []
                
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Get pricing for this date
                    cursor.execute("""
                        SELECT current_price 
                        FROM room_inventory 
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (property_id, room_type_id, date_str))
                    
                    price_row = cursor.fetchone()
                    if not price_row:
                        return {
                            'available': False,
                            'message': f"No pricing available for {date_str}"
                        }
                    
                    price = price_row[0]
                    
                    # Calculate confirmed bookings excluding the specified booking
                    cursor.execute("""
                        SELECT COALESCE(SUM(rooms_booked), 0) as booked_rooms
                        FROM bookings 
                        WHERE property_id = ? AND room_type_id = ? 
                        AND booking_status = 'CONFIRMED'
                        AND booking_id != ?
                        AND check_in_date <= ? AND check_out_date > ?
                    """, (property_id, room_type_id, exclude_booking_id, date_str, date_str))
                    
                    booked_rooms = cursor.fetchone()[0]
                    
                    # Calculate active room blocks for this date
                    cursor.execute("""
                        SELECT COALESCE(SUM(rooms_blocked), 0) as blocked_rooms
                        FROM room_blocks 
                        WHERE property_id = ? AND room_type_id = ? 
                        AND block_status = 'ACTIVE'
                        AND block_date = ?
                        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    """, (property_id, room_type_id, date_str))
                    
                    blocked_rooms = cursor.fetchone()[0]
                    
                    # Calculate actual available rooms
                    actual_available = base_rooms - booked_rooms - blocked_rooms
                    
                    availability_details.append({
                        'date': date_str,
                        'available_rooms': actual_available,
                        'price': price
                    })
                    
                    if actual_available < rooms_needed:
                        return {
                            'available': False,
                            'message': f"Insufficient rooms on {date_str}. Available: {actual_available}, Needed: {rooms_needed}",
                            'availability_details': availability_details
                        }
                    
                    min_available = min(min_available, actual_available)
                    total_price += price * rooms_needed
                    nights += 1
                    current_date += timedelta(days=1)
                
                return {
                    'available': True,
                    'min_available': min_available,
                    'total_price': total_price,
                    'nights': nights,
                    'avg_nightly_price': total_price / nights if nights > 0 else 0,
                    'availability_details': availability_details
                }
                
        except Exception as e:
            return {
                'available': False,
                'message': f"Error checking availability: {str(e)}"
            }
    
    def modify_booking(self, booking_reference: str, modification_type: str,
                      new_check_in: Optional[date] = None, new_check_out: Optional[date] = None,
                      new_room_type_id: Optional[str] = None, new_rooms_count: Optional[int] = None,
                      new_guest_name: Optional[str] = None, new_guest_email: Optional[str] = None,
                      new_guest_phone: Optional[str] = None, additional_requests: Optional[str] = None,
                      modification_reason: str = "") -> Dict:
        """
        Modify an existing booking with availability validation using relational approach.
        Supports date changes, room changes, guest count changes, and guest info updates.
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current booking details
                cursor.execute("""
                    SELECT b.booking_id, b.property_id, b.room_type_id, b.guest_name,
                           b.guest_email, b.guest_phone, b.check_in_date, b.check_out_date,
                           b.nights, b.rooms_booked, b.total_price, b.booking_status,
                           b.special_requests, h.hotel_name, rt.room_name
                    FROM bookings b
                    JOIN hotels h ON b.property_id = h.property_id
                    JOIN room_types rt ON b.room_type_id = rt.room_type_id
                    WHERE b.booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                if not booking:
                    return {
                        'success': False,
                        'message': f"Booking {booking_reference} not found"
                    }
                
                (booking_id, property_id, current_room_type_id, current_guest_name,
                 current_guest_email, current_guest_phone, current_check_in, current_check_out,
                 current_nights, current_rooms_count, current_total_price, booking_status,
                 current_special_requests, hotel_name, current_room_name) = booking
                
                if booking_status != 'CONFIRMED':
                    return {
                        'success': False,
                        'message': f"Cannot modify booking with status: {booking_status}"
                    }
                
                # Parse current dates
                current_check_in_date = datetime.strptime(current_check_in, '%Y-%m-%d').date()
                current_check_out_date = datetime.strptime(current_check_out, '%Y-%m-%d').date()
                
                # Determine what's being modified
                date_change = new_check_in is not None or new_check_out is not None
                room_change = new_room_type_id is not None
                guest_count_change = new_rooms_count is not None and new_rooms_count != current_rooms_count
                guest_info_change = (new_guest_name is not None or new_guest_email is not None or 
                                   new_guest_phone is not None)
                
                # Set new values or keep current ones
                final_check_in = new_check_in if new_check_in else current_check_in_date
                final_check_out = new_check_out if new_check_out else current_check_out_date
                final_room_type_id = new_room_type_id if new_room_type_id else current_room_type_id
                final_rooms_count = new_rooms_count if new_rooms_count else current_rooms_count
                final_guest_name = new_guest_name if new_guest_name else current_guest_name
                final_guest_email = new_guest_email if new_guest_email else current_guest_email
                final_guest_phone = new_guest_phone if new_guest_phone else current_guest_phone
                
                # Validate new dates
                if final_check_in >= final_check_out:
                    return {
                        'success': False,
                        'message': "Check-out date must be after check-in date"
                    }
                
                # Calculate new nights and pricing
                new_nights = (final_check_out - final_check_in).days
                
                # If room type changed, validate it exists
                final_room_name = current_room_name
                if room_change:
                    cursor.execute("""
                        SELECT room_name FROM room_types
                        WHERE property_id = ? AND room_type_id = ? AND is_active = 1
                    """, (property_id, final_room_type_id))
                    
                    room_result = cursor.fetchone()
                    if not room_result:
                        return {
                            'success': False,
                            'message': f"New room type {final_room_type_id} not found"
                        }
                    final_room_name = room_result[0]
                
                # Check availability for the new dates/room if needed
                if date_change or room_change or guest_count_change:
                    # Temporarily exclude current booking from availability calculation
                    availability = self.check_availability_excluding_booking(
                        property_id=property_id,
                        room_type_id=final_room_type_id,
                        check_in_date=final_check_in,
                        check_out_date=final_check_out,
                        rooms_needed=final_rooms_count,
                        exclude_booking_id=booking_id
                    )
                    
                    if not availability['available']:
                        return {
                            'success': False,
                            'message': f"Modification not possible: {availability['message']}"
                        }
                    
                    new_total_price = availability['total_price']
                else:
                    # No availability check needed, just recalculate price if needed
                    new_total_price = current_total_price
                
                # Update booking record
                update_fields = []
                update_values = []
                
                if date_change:
                    update_fields.extend(['check_in_date = ?', 'check_out_date = ?', 'nights = ?'])
                    update_values.extend([final_check_in.strftime('%Y-%m-%d'), 
                                        final_check_out.strftime('%Y-%m-%d'), new_nights])
                
                if room_change:
                    update_fields.append('room_type_id = ?')
                    update_values.append(final_room_type_id)
                
                if guest_count_change:
                    update_fields.append('rooms_booked = ?')
                    update_values.append(final_rooms_count)
                
                if guest_info_change:
                    if new_guest_name:
                        update_fields.append('guest_name = ?')
                        update_values.append(final_guest_name)
                    if new_guest_email:
                        update_fields.append('guest_email = ?')
                        update_values.append(final_guest_email)
                    if new_guest_phone:
                        update_fields.append('guest_phone = ?')
                        update_values.append(final_guest_phone)
                
                if date_change or room_change or guest_count_change:
                    update_fields.append('total_price = ?')
                    update_values.append(new_total_price)
                
                # Add modification notes
                modification_note = f"Modified: {modification_type}"
                if modification_reason:
                    modification_note += f" - {modification_reason}"
                
                update_fields.append('special_requests = ?')
                if current_special_requests:
                    new_special_requests = f"{current_special_requests} | {modification_note}"
                else:
                    new_special_requests = modification_note
                update_values.append(new_special_requests)
                
                if additional_requests:
                    new_special_requests += f" | {additional_requests}"
                    update_values[-1] = new_special_requests
                
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                
                # Execute update
                update_query = f"UPDATE bookings SET {', '.join(update_fields)} WHERE booking_reference = ?"
                update_values.append(booking_reference)
                
                cursor.execute(update_query, update_values)
                conn.commit()
                
                return {
                    'success': True,
                    'booking_reference': booking_reference,
                    'hotel_name': hotel_name,
                    'modification_type': modification_type,
                    'changes': {
                        'dates': f"{final_check_in} to {final_check_out}" if date_change else "No change",
                        'room_type': final_room_name if room_change else "No change",
                        'rooms_count': final_rooms_count if guest_count_change else "No change",
                        'guest_info': "Updated" if guest_info_change else "No change",
                        'price_change': new_total_price - current_total_price if (date_change or room_change or guest_count_change) else 0
                    },
                    'new_total_price': new_total_price if (date_change or room_change or guest_count_change) else current_total_price,
                    'message': f"Booking {booking_reference} modified successfully"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Booking modification failed: {str(e)}"
            }

# Create the booking manager instance for Ella
booking_manager = BookingConfirmationManager()

# LANGCHAIN TOOLS FOR ELLA - CUSTOMER FUNCTIONS ONLY






@tool
def confirm_booking(hotel_name: str, room_type: str, guest_name: str, 
                   check_in_date: str, check_out_date: str,
                   guest_email: str = "", guest_phone: str = "",
                   rooms_booked: int = 1, special_requests: str = "") -> str:
    """
    Confirm a hotel booking for a customer.
    This creates a confirmed reservation in the hotel system.
    
    Args:
        hotel_name: Name of the hotel
        room_type: Type of room (e.g., 'Deluxe King Room')
        guest_name: Name of the guest
        check_in_date: Check-in date (YYYY-MM-DD format)
        check_out_date: Check-out date (YYYY-MM-DD format)
        guest_email: Guest email address (optional)
        guest_phone: Guest phone number (optional)
        rooms_booked: Number of rooms to book (default: 1)
        special_requests: Any special requests (optional)
    
    Returns:
        JSON string with booking confirmation details
    """
    
    try:
        # Parse dates
        check_in = datetime.strptime(check_in_date, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_date, '%Y-%m-%d').date()
        
        # Get guest_id from search session context
        from core.guest_id import get_guest_id
        guest_id = get_guest_id()
        
        # Find matching hotel and room type
        with booking_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT h.property_id, rt.room_type_id
                FROM hotels h
                JOIN room_types rt ON h.property_id = rt.property_id
                WHERE LOWER(h.hotel_name) LIKE LOWER(?) 
                AND (LOWER(rt.room_name) LIKE LOWER(?) OR LOWER(rt.room_name) LIKE LOWER(?))
                AND h.is_active = 1 AND rt.is_active = 1
                LIMIT 1
            """, (f"%{hotel_name}%", f"%{room_type}%", f"%{room_type.replace('Grand', 'Deluxe')}%"))
            
            match = cursor.fetchone()
            if not match:
                return f"BOOKING_ERROR:HOTEL_NOT_FOUND|{hotel_name}"
            
            property_id, room_type_id = match
        
        # Create booking with guest_id
        result = booking_manager.create_confirmed_booking(
            property_id=property_id,
            room_type_id=room_type_id,
            guest_name=guest_name,
            check_in_date=check_in,
            check_out_date=check_out,
            guest_email=guest_email or None,
            guest_phone=guest_phone or None,
            rooms_booked=rooms_booked,
            special_requests=special_requests or None,
            guest_id=guest_id
        )
        
        if result['success']:
            response_message = f"✅ BOOKING CONFIRMED!\n\n" \
                             f"🏨 Hotel: {result['hotel_name']}\n" \
                             f"🛏️ Room: {result['room_name']}\n" \
                             f"👤 Guest: {result['guest_name']}\n" \
                             f"📅 Check-in: {result['check_in_date']}\n" \
                             f"📅 Check-out: {result['check_out_date']}\n" \
                             f"🌙 Nights: {result['nights']}\n" \
                             f"🏠 Rooms: {result['rooms_booked']}\n" \
                             f"💰 Total: RM{result['total_price']:.2f}\n" \
                             f"🎫 Reference: {result['booking_reference']}\n\n"
            
            # Add PDF confirmation info if available - FORMAT FOR AUTO-PRELOADING
            if result.get('pdf_available'):
                response_message += f"📄 Booking Confirmation PDF: /booking-confirmation/{result['booking_reference']}\n\n"
            
            response_message += "Please save your booking reference for future inquiries."
            
            return response_message
        else:
            return f"BOOKING_ERROR:FAILED|{result['message']}"
            
    except ValueError:
        return "HOTEL_ERROR:INVALID_DATE"
    except Exception as e:
        return f"❌ Booking error: {str(e)}"

@tool
def get_payment_details(booking_reference: str) -> str:
    """
    Get detailed payment information for a booking including deposit requirements and payment history.
    
    Args:
        booking_reference: The booking reference number
    
    Returns:
        Detailed payment summary with deposit requirements, payment history, and next steps
    """
    
    try:
        # Get basic payment details from booking
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT b.booking_reference, b.guest_name, b.total_price, 
                       h.hotel_name, h.requires_prepayment, b.payment_status
                FROM bookings b
                JOIN hotels h ON b.property_id = h.property_id
                WHERE b.booking_reference = ?
            """, (booking_reference,))
            
            booking = cursor.fetchone()
            if not booking:
                return f"❌ Booking not found: {booking_reference}"
            
            booking_ref, guest_name, total_price, hotel_name, requires_prepayment, payment_status = booking
            
            return f"""💳 PAYMENT DETAILS

🏨 Hotel: {hotel_name}
🎫 Booking: {booking_reference}
👤 Guest: {guest_name}
💰 Total Amount: RM{total_price:.2f}
📊 Payment Status: {payment_status or 'PENDING'}

{'🏦 Hotel requires prepayment' if requires_prepayment else '💳 Payment due at check-in'}

💡 For detailed payment proof submission, use the booking agent tools."""
        
    except Exception as e:
        return f"❌ Error getting payment details: {str(e)}"

@tool
def process_payment(booking_reference: str, amount: float, payment_method: str = "Credit Card", transaction_ref: str = "", notes: str = "") -> str:
    """
    Process a payment for a booking (deposit or partial payment).
    
    Args:
        booking_reference: The booking reference number
        amount: Payment amount in RM
        payment_method: Payment method used
        transaction_ref: Transaction reference from payment gateway
        notes: Additional notes about the payment
    
    Returns:
        Payment confirmation with updated balance information
    """
    
    try:
        # Simple payment processing - update booking payment status
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get booking details
            cursor.execute("""
                SELECT booking_reference, total_price, payment_status
                FROM bookings 
                WHERE booking_reference = ?
            """, (booking_reference,))
            
            booking = cursor.fetchone()
            if not booking:
                return f"❌ Payment failed: Booking not found"
            
            current_total, payment_status = booking[1], booking[2]
            
            # Update payment status based on amount
            if amount >= current_total:
                new_status = "PAID"
            else:
                new_status = "PARTIALLY_PAID"
            
            # Update booking
            cursor.execute("""
                UPDATE bookings 
                SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE booking_reference = ?
            """, (new_status, booking_reference))
            
            conn.commit()
            
            balance_due = max(0, current_total - amount)
            
            return f"""✅ PAYMENT PROCESSED SUCCESSFULLY

🎫 Booking Reference: {booking_reference}
💰 Payment Amount: RM{amount:.2f}
💳 Payment Method: {payment_method}

💰 UPDATED PAYMENT STATUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Payment Status: {new_status}
⚠️  Balance Due: RM{balance_due:.2f}

✅ Payment confirmation updated in system.

{f"🎉 Booking fully paid!" if balance_due <= 0 else f"💳 Remaining balance: RM{balance_due:.2f}"}

💡 For payment proof upload, use booking agent tools."""
            
    except Exception as e:
        return f"❌ Error processing payment: {str(e)}"


@tool 
def check_booking_status(booking_reference: str) -> str:
    """
    Check the status of a booking using the booking reference with enhanced payment details.
    
    Args:
        booking_reference: The booking reference number
    
    Returns:
        Comprehensive booking details with payment breakdown
    """
    
    result = booking_manager.get_booking_status(booking_reference)
    
    if result['success']:
        booking = result
        
        status_emoji = {
            'CONFIRMED': '✅',
            'CANCELLED': '❌',
            'PENDING': '⏳',
            'COMPLETED': '🏁'
        }.get(booking['booking_status'], '❓')
        
        # Enhanced payment status mapping
        payment_emoji = {
            'FULLY_PAID': '✅',
            'DEPOSIT_PAID': '🟡', 
            'PARTIALLY_PAID': '⚠️',
            'UNPAID': '❌',
            'PENDING': '⏳',
            'PAID': '✅',
            'REFUNDED': '💸',
            'FAILED': '❌'
        }.get(booking.get('payment_status', 'PENDING'), '❓')
        
        # Simple payment section
        payment_section = f"""💰 PAYMENT INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Total Amount: {booking['currency']}{booking['total_price']:.2f}
📊 Payment Status: {booking.get('payment_status', 'PENDING')}

💡 For detailed payment tracking, use booking agent payment tools."""
        
        return f"""📋 BOOKING STATUS REPORT

🎫 Reference: {booking['booking_reference']}
{status_emoji} Status: {booking['booking_status']}
{payment_emoji} Payment: {booking.get('payment_status', 'PENDING')}

🏨 Hotel: {booking['hotel_name']}
📍 Location: {booking['hotel_location']}
🛏️ Room: {booking['room_name']}
👤 Guest: {booking['guest_name']}
📧 Email: {booking['guest_email'] or 'Not provided'}
📞 Phone: {booking['guest_phone'] or 'Not provided'}

📅 Check-in: {booking['check_in_date']}
📅 Check-out: {booking['check_out_date']}
🌙 Nights: {booking['nights']}
🏠 Rooms: {booking['rooms_booked']}

{payment_section}

📝 Special Requests: {booking['special_requests'] or 'None'}
⏰ Booked: {booking['booked_at']}"""
    else:
        return f"❌ {result['message']}"

@tool
def get_cancellation_policy(booking_reference: str) -> str:
    """
    Get cancellation policy and refund calculation for a booking.
    
    Args:
        booking_reference: The booking reference number
    
    Returns:
        Detailed cancellation policy and refund information
    """
    
    try:
        # Import the cancellation manager
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from cancellation_policy_system import CancellationPolicyManager
        
        manager = CancellationPolicyManager()
        summary = manager.get_cancellation_summary(booking_reference)
        
        return summary
        
    except Exception as e:
        return f"❌ Error getting cancellation policy: {str(e)}"

@tool
def cancel_booking(booking_reference: str, cancellation_reason: str = "Cancelled by guest") -> str:
    """
    Cancel a booking using the booking reference with automatic refund calculation.
    
    Args:
        booking_reference: The booking reference number
        cancellation_reason: Reason for cancellation (optional)
    
    Returns:
        Confirmation message with refund details
    """
    
    try:
        # Import the enhanced cancellation manager
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from cancellation_policy_system import CancellationPolicyManager
        
        manager = CancellationPolicyManager()
        result = manager.process_cancellation(booking_reference, cancellation_reason)
        
        if result['success']:
            return f"""✅ BOOKING CANCELLED SUCCESSFULLY

🎫 Booking Reference: {result['booking_reference']}
🏨 Hotel: {result['hotel_name']}
📅 Original Check-in: {result['check_in_date']}
📝 Cancellation Reason: {cancellation_reason}

💰 REFUND DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Total Booking Value: RM{result['total_price']:.2f}
💸 Refund Amount: RM{result['refund_amount']:.2f} ({result['refund_percentage']}%)
⚠️  Penalty Amount: RM{result['penalty_amount']:.2f}

📜 Applied Policy: {result['applicable_rule']['description'] if result['applicable_rule'] else 'No refund applicable'}

✅ PROCESSING STATUS:
• Booking Status: CANCELLED
• Inventory: Restored to available pool
• Refund Status: Initiated (5-7 business days)

Your cancellation has been processed successfully. You will receive a refund confirmation email shortly."""
        else:
            return f"❌ CANCELLATION FAILED: {result['message']}"
            
    except Exception as e:
        # Fallback to basic cancellation
        result = booking_manager.cancel_booking(booking_reference, cancellation_reason)
        
        if result['success']:
            return f"✅ BOOKING CANCELLED\n\n" \
                   f"🎫 Reference: {result['booking_reference']}\n" \
                   f"📝 Reason: {cancellation_reason}\n\n" \
                   f"Your booking has been cancelled. Refund processing will depend on the hotel's cancellation policy."
        else:
            return f"❌ CANCELLATION FAILED: {result['message']}"

@tool
def get_guest_bookings(guest_name: str, guest_email: str = "") -> str:
    """
    Get all bookings for a guest by name and/or email.
    
    Args:
        guest_name: Name of the guest
        guest_email: Email of the guest (optional, helps narrow search)
    
    Returns:
        List of all bookings for the guest
    """
    
    bookings = booking_manager.get_guest_bookings(guest_name, guest_email or None)
    
    if bookings:
        result = f"📋 BOOKINGS FOR {guest_name.upper()}\n"
        result += "=" * 50 + "\n"
        
        for i, booking in enumerate(bookings, 1):
            status_emoji = {
                'CONFIRMED': '✅',
                'CANCELLED': '❌',
                'PENDING': '⏳',
                'COMPLETED': '🏁'
            }.get(booking['booking_status'], '❓')
            
            result += f"\n[{i}] {status_emoji} {booking['booking_reference']}\n"
            result += f"🏨 {booking['hotel_name']} - {booking['room_name']}\n"
            result += f"📅 {booking['check_in_date']} to {booking['check_out_date']}\n"
            result += f"💰 {booking['currency']}{booking['total_price']:.2f}\n"
            result += f"⏰ Booked: {booking['booked_at'][:10]}\n"
        
        return result
    else:
        return f"BOOKING_ERROR:NO_BOOKINGS|{guest_name}"

@tool
def modify_booking(booking_reference: str, modification_type: str,
                  new_check_in: Optional[date] = None, new_check_out: Optional[date] = None,
                  new_room_type_id: Optional[str] = None, new_rooms_count: Optional[int] = None,
                  new_guest_name: Optional[str] = None, new_guest_email: Optional[str] = None,
                  new_guest_phone: Optional[str] = None, additional_requests: Optional[str] = None,
                  modification_reason: str = "") -> str:
    """
    Modify an existing booking (dates, room type, guest info, etc.).
    
    Args:
        booking_reference: The booking reference number
        modification_type: Type of modification (e.g., "DATE_CHANGE", "ROOM_CHANGE", "GUEST_INFO")
        new_check_in: New check-in date (YYYY-MM-DD format, optional)
        new_check_out: New check-out date (YYYY-MM-DD format, optional)
        new_room_type_id: New room type ID (optional)
        new_rooms_count: New number of rooms (optional)
        new_guest_name: New guest name (optional)
        new_guest_email: New guest email (optional)
        new_guest_phone: New guest phone (optional)
        additional_requests: Additional special requests (optional)
        modification_reason: Reason for modification (optional)
    
    Returns:
        Confirmation message about the modification
    """
    
    try:
        # Parse date strings if provided
        parsed_check_in = None
        parsed_check_out = None
        
        if new_check_in:
            if isinstance(new_check_in, str):
                parsed_check_in = datetime.strptime(new_check_in, '%Y-%m-%d').date()
            else:
                parsed_check_in = new_check_in
                
        if new_check_out:
            if isinstance(new_check_out, str):
                parsed_check_out = datetime.strptime(new_check_out, '%Y-%m-%d').date()
            else:
                parsed_check_out = new_check_out
        
        result = booking_manager.modify_booking(
            booking_reference=booking_reference,
            modification_type=modification_type,
            new_check_in=parsed_check_in,
            new_check_out=parsed_check_out,
            new_room_type_id=new_room_type_id,
            new_rooms_count=new_rooms_count,
            new_guest_name=new_guest_name,
            new_guest_email=new_guest_email,
            new_guest_phone=new_guest_phone,
            additional_requests=additional_requests,
            modification_reason=modification_reason
        )
        
        if result['success']:
            changes = result['changes']
            
            response = f"✅ BOOKING MODIFIED SUCCESSFULLY\n\n"
            response += f"🎫 Reference: {result['booking_reference']}\n"
            response += f"🏨 Hotel: {result['hotel_name']}\n"
            response += f"🔄 Modification: {result['modification_type']}\n\n"
            response += f"📋 CHANGES MADE:\n"
            response += f"📅 Dates: {changes['dates']}\n"
            response += f"🛏️ Room Type: {changes['room_type']}\n"
            response += f"🏠 Room Count: {changes['rooms_count']}\n"
            response += f"👤 Guest Info: {changes['guest_info']}\n"
            
            if changes['price_change'] != 0:
                price_symbol = "+" if changes['price_change'] > 0 else ""
                response += f"💰 Price Change: {price_symbol}RM{changes['price_change']:.2f}\n"
                response += f"💰 New Total: RM{result['new_total_price']:.2f}\n"
            
            return response
        else:
            return f"BOOKING_ERROR:MODIFICATION_FAILED|{result['message']}"
            
    except ValueError as e:
        return f"❌ Invalid date format: {str(e)}. Please use YYYY-MM-DD format."
    except Exception as e:
        return f"❌ Modification error: {str(e)}"

# Export all booking tools for the agent
BOOKING_TOOLS = [confirm_booking, check_booking_status, get_payment_details, process_payment, 
                get_cancellation_policy, cancel_booking, get_guest_bookings, modify_booking] 
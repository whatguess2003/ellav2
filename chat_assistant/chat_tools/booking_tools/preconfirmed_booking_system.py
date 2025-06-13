#!/usr/bin/env python3
"""
PRE_CONFIRMED Booking System
============================

Handles sophisticated booking status logic with payment window expiry:
- PRE_CONFIRMED: Room reserved, payment window active
- PENDING: Payment window expired, room released
- CONFIRMED: Payment received, room deducted from inventory
- Buffer bookings for late payments when room unavailable

Status Flow:
PRE_CONFIRMED (inventory: RESERVED) → payment window expires
    ↓ if paid: → CONFIRMED (inventory: RESERVED → DEDUCTED) 
    ↓ if unpaid: → PENDING (inventory: RESERVED → RELEASED)

PENDING (inventory: RELEASED) → guest pays late
    ↓ if room available: → CONFIRMED (inventory: RE-DEDUCTED)
    ↓ if room sold: → BUFFER_BOOKING (manual intervention needed)
"""

import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

class PreConfirmedBookingManager:
    """Manages PRE_CONFIRMED booking logic and status transitions."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path

    def get_connection(self):
        """Get database connection with foreign key support."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_pre_confirmed_booking(self, property_id: str, room_type_id: str, 
                                   guest_name: str, check_in_date: date, check_out_date: date,
                                   guest_email: Optional[str] = None, guest_phone: Optional[str] = None,
                                   rooms_booked: int = 1, total_price: float = 0.0,
                                   special_requests: Optional[str] = None) -> Dict:
        """
        Create a PRE_CONFIRMED booking with payment window logic.
        
        Returns:
            dict: Success status, booking details, and payment window info
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get hotel policy
                cursor.execute("""
                    SELECT hotel_name, requires_prepayment, payment_window_nights, 
                           deposit_percentage, deposit_amount
                    FROM hotels 
                    WHERE property_id = ?
                """, (property_id,))
                
                hotel_data = cursor.fetchone()
                if not hotel_data:
                    return {'success': False, 'message': f"Hotel {property_id} not found"}
                
                hotel_name, requires_prepayment, payment_window_nights, deposit_percentage, deposit_amount = hotel_data
                
                # If hotel doesn't require prepayment, create CONFIRMED booking directly
                if not requires_prepayment:
                    return self._create_confirmed_booking_direct(
                        property_id, room_type_id, guest_name, check_in_date, check_out_date,
                        guest_email, guest_phone, rooms_booked, total_price, special_requests
                    )
                
                # Calculate payment window expiry
                payment_window_expires = check_in_date - timedelta(days=payment_window_nights)
                days_until_checkin = (check_in_date - date.today()).days
                
                # Check if we're already past payment window
                if days_until_checkin <= payment_window_nights:
                    return {
                        'success': False, 
                        'message': f"Cannot create booking. Payment required {payment_window_nights} nights before check-in. "
                                 f"Current booking is only {days_until_checkin} nights before check-in."
                    }
                
                # Check room availability for the entire stay
                availability_check = self._check_room_availability(
                    property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                )
                
                if not availability_check['available']:
                    return {
                        'success': False,
                        'message': f"Insufficient rooms available. {availability_check['message']}"
                    }
                
                # Generate booking reference
                booking_reference = self._generate_booking_reference(hotel_name, check_in_date)
                nights = (check_out_date - check_in_date).days
                
                # Create PRE_CONFIRMED booking
                cursor.execute("""
                    INSERT INTO bookings (
                        booking_reference, property_id, room_type_id, guest_name, 
                        guest_email, guest_phone, check_in_date, check_out_date,
                        nights, rooms_booked, total_price, booking_status, payment_status,
                        payment_window_expires, special_requests, booked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PRE_CONFIRMED', 'UNPAID', ?, ?, CURRENT_TIMESTAMP)
                """, (
                    booking_reference, property_id, room_type_id, guest_name,
                    guest_email, guest_phone, check_in_date.strftime('%Y-%m-%d'),
                    check_out_date.strftime('%Y-%m-%d'), nights, rooms_booked,
                    total_price, payment_window_expires.strftime('%Y-%m-%d'), special_requests
                ))
                
                # Reserve inventory (don't deduct yet)
                inventory_result = self._reserve_room_inventory(
                    property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                )
                
                if not inventory_result['success']:
                    return {
                        'success': False,
                        'message': f"Failed to reserve inventory: {inventory_result['message']}"
                    }
                
                conn.commit()
                
                # Calculate deposit requirement
                deposit_required = 0
                if deposit_percentage and deposit_percentage > 0:
                    deposit_required = total_price * (deposit_percentage / 100)
                elif deposit_amount and deposit_amount > 0:
                    deposit_required = deposit_amount
                
                return {
                    'success': True,
                    'booking_reference': booking_reference,
                    'booking_status': 'PRE_CONFIRMED',
                    'payment_status': 'UNPAID',
                    'payment_window_expires': payment_window_expires.strftime('%Y-%m-%d'),
                    'days_to_payment_deadline': (payment_window_expires - date.today()).days,
                    'deposit_required': deposit_required,
                    'total_price': total_price,
                    'inventory_status': 'RESERVED',
                    'message': f"Booking PRE_CONFIRMED. Payment of RM{deposit_required:.2f} required by {payment_window_expires.strftime('%d %b %Y')}"
                }
                
        except Exception as e:
            return {'success': False, 'message': f"Error creating PRE_CONFIRMED booking: {str(e)}"}

    def check_payment_window_expiry(self) -> List[Dict]:
        """
        Check for bookings with expired payment windows and update status.
        
        Returns:
            list: Updated booking references and their new status
        """
        
        updated_bookings = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find PRE_CONFIRMED bookings with expired payment windows
                cursor.execute("""
                    SELECT booking_reference, property_id, room_type_id, 
                           check_in_date, check_out_date, rooms_booked
                    FROM bookings 
                    WHERE booking_status = 'PRE_CONFIRMED' 
                    AND payment_status = 'UNPAID'
                    AND payment_window_expires <= DATE('now')
                """)
                
                expired_bookings = cursor.fetchall()
                
                for booking_data in expired_bookings:
                    booking_ref, property_id, room_type_id, check_in_str, check_out_str, rooms_booked = booking_data
                    
                    # Update booking status to PENDING
                    cursor.execute("""
                        UPDATE bookings 
                        SET booking_status = 'PENDING', 
                            payment_window_expires = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE booking_reference = ?
                    """, (booking_ref,))
                    
                    # Release reserved inventory
                    check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
                    check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
                    
                    release_result = self._release_reserved_inventory(
                        property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                    )
                    
                    updated_bookings.append({
                        'booking_reference': booking_ref,
                        'old_status': 'PRE_CONFIRMED',
                        'new_status': 'PENDING',
                        'inventory_action': 'RELEASED',
                        'inventory_success': release_result['success']
                    })
                
                conn.commit()
                
        except Exception as e:
            print(f"Error checking payment window expiry: {str(e)}")
        
        return updated_bookings

    def process_late_payment(self, booking_reference: str, amount: float, 
                           payment_method: str = "Credit Card") -> Dict:
        """
        Process payment for PENDING booking and handle room availability.
        
        Returns:
            dict: Payment result and booking status update
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get booking details
                cursor.execute("""
                    SELECT b.booking_id, b.property_id, b.room_type_id, 
                           b.check_in_date, b.check_out_date, b.rooms_booked,
                           b.total_price, b.booking_status, b.payment_status,
                           h.hotel_name, h.deposit_percentage, h.deposit_amount
                    FROM bookings b
                    JOIN hotels h ON b.property_id = h.property_id
                    WHERE b.booking_reference = ?
                """, (booking_reference,))
                
                booking_data = cursor.fetchone()
                if not booking_data:
                    return {'success': False, 'message': f"Booking {booking_reference} not found"}
                
                (booking_id, property_id, room_type_id, check_in_str, check_out_str, 
                 rooms_booked, total_price, booking_status, payment_status, hotel_name,
                 deposit_percentage, deposit_amount) = booking_data
                
                check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
                
                # Record payment transaction
                cursor.execute("""
                    INSERT INTO payment_transactions (
                        booking_reference, amount, payment_method, transaction_status,
                        transaction_date, notes
                    ) VALUES (?, ?, ?, 'COMPLETED', CURRENT_TIMESTAMP, 'Late payment processed')
                """, (booking_reference, amount, payment_method))
                
                # Check if room is still available
                availability_check = self._check_room_availability(
                    property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                )
                
                if availability_check['available']:
                    # Room available - confirm booking and deduct inventory
                    deduct_result = self._deduct_room_inventory(
                        property_id, room_type_id, check_in_date, check_out_date, rooms_booked
                    )
                    
                    if deduct_result['success']:
                        # Update booking to CONFIRMED
                        new_payment_status = self._calculate_payment_status(
                            amount, total_price, deposit_percentage, deposit_amount
                        )
                        
                        cursor.execute("""
                            UPDATE bookings 
                            SET booking_status = 'CONFIRMED',
                                payment_status = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE booking_reference = ?
                        """, (new_payment_status, booking_reference))
                        
                        conn.commit()
                        
                        return {
                            'success': True,
                            'booking_status': 'CONFIRMED',
                            'payment_status': new_payment_status,
                            'inventory_action': 'DEDUCTED',
                            'message': f"Payment processed successfully. Booking confirmed."
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"Payment received but inventory deduction failed: {deduct_result['message']}"
                        }
                
                else:
                    # Room no longer available - add to buffer bookings
                    cursor.execute("""
                        INSERT INTO buffer_bookings (
                            booking_reference, original_room_type_id, reason, notes
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        booking_reference, room_type_id,
                        "Room unavailable after late payment",
                        f"Guest paid RM{amount} but {rooms_booked} x {room_type_id} no longer available for {check_in_str} to {check_out_str}"
                    ))
                    
                    # Update payment status but keep booking as PENDING
                    new_payment_status = self._calculate_payment_status(
                        amount, total_price, deposit_percentage, deposit_amount
                    )
                    
                    cursor.execute("""
                        UPDATE bookings 
                        SET payment_status = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE booking_reference = ?
                    """, (new_payment_status, booking_reference))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'booking_status': 'PENDING',
                        'payment_status': new_payment_status,
                        'inventory_action': 'BUFFER_BOOKING_CREATED',
                        'requires_manual_intervention': True,
                        'message': f"Payment received but room no longer available. Added to buffer booking list for manual resolution."
                    }
                    
        except Exception as e:
            return {'success': False, 'message': f"Error processing late payment: {str(e)}"}

    def get_buffer_bookings(self) -> List[Dict]:
        """Get all unresolved buffer bookings requiring manual intervention."""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT bb.buffer_id, bb.booking_reference, bb.original_room_type_id,
                           bb.reason, bb.created_at, bb.status, bb.notes,
                           b.guest_name, b.guest_email, b.guest_phone,
                           b.check_in_date, b.check_out_date, b.rooms_booked,
                           b.total_price, b.payment_status, h.hotel_name
                    FROM buffer_bookings bb
                    JOIN bookings b ON bb.booking_reference = b.booking_reference
                    JOIN hotels h ON b.property_id = h.property_id
                    WHERE bb.status = 'PENDING_RESOLUTION'
                    ORDER BY bb.created_at ASC
                """)
                
                buffer_bookings = []
                for row in cursor.fetchall():
                    (buffer_id, booking_ref, room_type_id, reason, created_at, status, notes,
                     guest_name, guest_email, guest_phone, check_in, check_out, rooms_booked,
                     total_price, payment_status, hotel_name) = row
                    
                    buffer_bookings.append({
                        'buffer_id': buffer_id,
                        'booking_reference': booking_ref,
                        'hotel_name': hotel_name,
                        'guest_name': guest_name,
                        'guest_email': guest_email,
                        'guest_phone': guest_phone,
                        'original_room_type': room_type_id,
                        'check_in_date': check_in,
                        'check_out_date': check_out,
                        'rooms_booked': rooms_booked,
                        'total_price': total_price,
                        'payment_status': payment_status,
                        'reason': reason,
                        'created_at': created_at,
                        'notes': notes
                    })
                
                return buffer_bookings
                
        except Exception as e:
            print(f"Error getting buffer bookings: {str(e)}")
            return []

    # Helper methods
    def _create_confirmed_booking_direct(self, property_id: str, room_type_id: str, 
                                       guest_name: str, check_in_date: date, check_out_date: date,
                                       guest_email: Optional[str], guest_phone: Optional[str],
                                       rooms_booked: int, total_price: float, 
                                       special_requests: Optional[str]) -> Dict:
        """Create CONFIRMED booking directly for no-prepayment hotels."""
        # This would call the existing booking_management.py logic
        from .booking_management import BookingConfirmationManager
        
        manager = BookingConfirmationManager()
        return manager.create_confirmed_booking(
            property_id, room_type_id, guest_name, check_in_date, check_out_date,
            guest_email, guest_phone, rooms_booked, total_price, special_requests
        )

    def _generate_booking_reference(self, hotel_name: str, check_in_date: date) -> str:
        """Generate unique booking reference."""
        import random
        import string
        
        # Clean hotel name
        clean_name = hotel_name.replace(" ", "_").replace("'", "")
        date_str = check_in_date.strftime("%Y%m%d")
        
        # Check for existing bookings with same pattern
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE booking_reference LIKE ?
            """, (f"{clean_name}_{date_str}_%",))
            
            count = cursor.fetchone()[0] + 1
            
        return f"{clean_name}_{date_str}_booking{count}"

    def _check_room_availability(self, property_id: str, room_type_id: str, 
                               check_in_date: date, check_out_date: date, 
                               rooms_needed: int) -> Dict:
        """Check if rooms are available for the entire stay period."""
        # This would use the existing availability checking logic
        from .booking_management import BookingConfirmationManager
        
        manager = BookingConfirmationManager()
        return manager.check_availability(
            property_id, room_type_id, check_in_date, check_out_date, rooms_needed
        )

    def _reserve_room_inventory(self, property_id: str, room_type_id: str,
                              check_in_date: date, check_out_date: date, rooms: int) -> Dict:
        """Reserve inventory for PRE_CONFIRMED booking (increment reserved_rooms)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = check_in_date
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Increment reserved_rooms
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET reserved_rooms = COALESCE(reserved_rooms, 0) + ?
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (rooms, property_id, room_type_id, date_str))
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                return {'success': True, 'message': 'Inventory reserved successfully'}
                
        except Exception as e:
            return {'success': False, 'message': f"Failed to reserve inventory: {str(e)}"}

    def _release_reserved_inventory(self, property_id: str, room_type_id: str,
                                  check_in_date: date, check_out_date: date, rooms: int) -> Dict:
        """Release reserved inventory when PRE_CONFIRMED becomes PENDING."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_date = check_in_date
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Decrement reserved_rooms
                    cursor.execute("""
                        UPDATE room_inventory 
                        SET reserved_rooms = GREATEST(0, COALESCE(reserved_rooms, 0) - ?)
                        WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
                    """, (rooms, property_id, room_type_id, date_str))
                    
                    current_date += timedelta(days=1)
                
                conn.commit()
                return {'success': True, 'message': 'Reserved inventory released successfully'}
                
        except Exception as e:
            return {'success': False, 'message': f"Failed to release inventory: {str(e)}"}

    def _deduct_room_inventory(self, property_id: str, room_type_id: str,
                             check_in_date: date, check_out_date: date, rooms: int) -> Dict:
        """Deduct from available inventory for CONFIRMED booking."""
        # This would use the existing inventory deduction logic
        from .booking_management import BookingConfirmationManager
        
        manager = BookingConfirmationManager()
        return manager.update_room_inventory(
            property_id, room_type_id, check_in_date, check_out_date, rooms, "booking_confirmation"
        )

    def _calculate_payment_status(self, amount_paid: float, total_price: float,
                                deposit_percentage: Optional[float], 
                                deposit_amount: Optional[float]) -> str:
        """Calculate appropriate payment status based on amount paid."""
        
        if amount_paid >= total_price:
            return "FULLY_PAID"
        
        # Calculate required deposit
        required_deposit = 0
        if deposit_percentage and deposit_percentage > 0:
            required_deposit = total_price * (deposit_percentage / 100)
        elif deposit_amount and deposit_amount > 0:
            required_deposit = deposit_amount
        
        if amount_paid >= required_deposit:
            return "DEPOSIT_PAID"
        elif amount_paid > 0:
            return "PARTIALLY_PAID"
        else:
            return "UNPAID"
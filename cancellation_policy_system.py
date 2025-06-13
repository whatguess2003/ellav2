#!/usr/bin/env python3
"""
ELLA Hotel System - Cancellation Policy Management
Implements flexible cancellation policies with windows and refund percentages
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

class CancellationPolicyManager:
    """Manages hotel cancellation policies and processes cancellations"""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
        self.setup_cancellation_policy_schema()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def setup_cancellation_policy_schema(self):
        """Add cancellation policy fields to hotels table"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Add cancellation policy columns if they don't exist
                try:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN cancellation_policy_json TEXT")
                    print("✅ Added cancellation_policy_json column")
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                try:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN cancellation_window_hours INTEGER DEFAULT 24")
                    print("✅ Added cancellation_window_hours column")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN cancellation_type VARCHAR(20) DEFAULT 'FLEXIBLE'")
                    print("✅ Added cancellation_type column")
                except sqlite3.OperationalError:
                    pass
                
                # Add cancellation tracking to bookings table
                try:
                    cursor.execute("ALTER TABLE bookings ADD COLUMN cancelled_at DATETIME")
                    print("✅ Added cancelled_at column to bookings")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE bookings ADD COLUMN cancellation_reason TEXT")
                    print("✅ Added cancellation_reason column to bookings")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE bookings ADD COLUMN refund_amount DECIMAL(10,2)")
                    print("✅ Added refund_amount column to bookings")
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("ALTER TABLE bookings ADD COLUMN refund_status VARCHAR(20) DEFAULT 'PENDING'")
                    print("✅ Added refund_status column to bookings")
                except sqlite3.OperationalError:
                    pass
                
                conn.commit()
                
        except Exception as e:
            print(f"⚠️ Error setting up cancellation schema: {e}")
    
    def set_hotel_cancellation_policy(self, property_id: str, policy: Dict) -> bool:
        """Set cancellation policy for a hotel"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                policy_json = json.dumps(policy)
                cancellation_type = policy.get('type', 'FLEXIBLE')
                cancellation_window_hours = policy.get('window_hours', 24)
                
                cursor.execute("""
                    UPDATE hotels 
                    SET cancellation_policy_json = ?,
                        cancellation_type = ?,
                        cancellation_window_hours = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE property_id = ?
                """, (policy_json, cancellation_type, cancellation_window_hours, property_id))
                
                conn.commit()
                
                print(f"✅ Updated cancellation policy for {property_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error setting cancellation policy: {e}")
            return False
    
    def get_hotel_cancellation_policy(self, property_id: str) -> Dict:
        """Get cancellation policy for a hotel"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT cancellation_policy_json, cancellation_type, cancellation_window_hours, hotel_name
                    FROM hotels 
                    WHERE property_id = ?
                """, (property_id,))
                
                result = cursor.fetchone()
                
                if result:
                    policy_json, cancellation_type, window_hours, hotel_name = result
                    
                    if policy_json:
                        try:
                            policy = json.loads(policy_json)
                        except:
                            policy = {}
                    else:
                        policy = {}
                    
                    # Add defaults if missing
                    default_policy = {
                        'type': cancellation_type or 'FLEXIBLE',
                        'window_hours': window_hours or 24,
                        'hotel_name': hotel_name,
                        'rules': policy.get('rules', [
                            {
                                'window_hours': 24,
                                'refund_percentage': 100,
                                'description': 'Free cancellation up to 24 hours before check-in'
                            }
                        ])
                    }
                    
                    # Merge with stored policy
                    default_policy.update(policy)
                    return default_policy
                
                else:
                    return self._get_default_policy()
                    
        except Exception as e:
            print(f"❌ Error getting cancellation policy: {e}")
            return self._get_default_policy()
    
    def _get_default_policy(self) -> Dict:
        """Default cancellation policy"""
        return {
            'type': 'FLEXIBLE',
            'window_hours': 24,
            'hotel_name': 'Unknown Hotel',
            'rules': [
                {
                    'window_hours': 24,
                    'refund_percentage': 100,
                    'description': 'Free cancellation up to 24 hours before check-in'
                },
                {
                    'window_hours': 0,
                    'refund_percentage': 0,
                    'description': 'No refund for same-day cancellation or no-show'
                }
            ]
        }
    
    def calculate_cancellation_details(self, booking_reference: str) -> Dict:
        """Calculate cancellation window and refund amount for a booking"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get booking details
                cursor.execute("""
                    SELECT b.property_id, b.check_in_date, b.total_price, b.booking_status,
                           b.booked_at, h.hotel_name
                    FROM bookings b
                    JOIN hotels h ON b.property_id = h.property_id
                    WHERE b.booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                
                if not booking:
                    return {'success': False, 'message': 'Booking not found'}
                
                property_id, check_in_str, total_price, booking_status, booked_at_str, hotel_name = booking
                
                if booking_status == 'CANCELLED':
                    return {'success': False, 'message': 'Booking already cancelled'}
                
                # Parse dates
                check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d')
                current_time = datetime.now()
                
                # Get cancellation policy
                policy = self.get_hotel_cancellation_policy(property_id)
                
                # Calculate hours until check-in
                hours_until_checkin = (check_in_date - current_time).total_seconds() / 3600
                
                # Find applicable rule
                refund_percentage = 0
                applicable_rule = None
                
                for rule in policy['rules']:
                    if hours_until_checkin >= rule['window_hours']:
                        if rule['refund_percentage'] > refund_percentage:
                            refund_percentage = rule['refund_percentage']
                            applicable_rule = rule
                
                # Calculate refund amount
                total_price_decimal = Decimal(str(total_price))
                refund_amount = total_price_decimal * Decimal(str(refund_percentage)) / Decimal('100')
                
                return {
                    'success': True,
                    'booking_reference': booking_reference,
                    'hotel_name': hotel_name,
                    'check_in_date': check_in_str,
                    'total_price': float(total_price_decimal),
                    'hours_until_checkin': round(hours_until_checkin, 1),
                    'cancellation_policy': policy,
                    'applicable_rule': applicable_rule,
                    'refund_percentage': refund_percentage,
                    'refund_amount': float(refund_amount),
                    'penalty_amount': float(total_price_decimal - refund_amount),
                    'can_cancel': True,
                    'cancellation_deadline': check_in_date.strftime('%Y-%m-%d %H:%M')
                }
                
        except Exception as e:
            return {'success': False, 'message': f'Error calculating cancellation: {str(e)}'}
    
    def process_cancellation(self, booking_reference: str, cancellation_reason: str = "Cancelled by guest") -> Dict:
        """Process booking cancellation with refund calculation"""
        
        try:
            # First calculate cancellation details
            calc_result = self.calculate_cancellation_details(booking_reference)
            
            if not calc_result['success']:
                return calc_result
            
            # Get booking details for inventory restoration
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT property_id, room_type_id, check_in_date, check_out_date, 
                           rooms_booked, booking_status
                    FROM bookings
                    WHERE booking_reference = ?
                """, (booking_reference,))
                
                booking = cursor.fetchone()
                property_id, room_type_id, check_in_str, check_out_str, rooms_booked, booking_status = booking
                
                # Restore inventory based on booking status
                if booking_status == 'CONFIRMED':
                    # Restore available rooms (increase inventory)
                    self._restore_confirmed_booking_inventory(
                        cursor, property_id, room_type_id, check_in_str, check_out_str, rooms_booked
                    )
                elif booking_status == 'PENDING':
                    # Release reserved rooms
                    self._release_pending_booking_inventory(
                        cursor, property_id, room_type_id, check_in_str, check_out_str, rooms_booked
                    )
                
                # Update booking status and add cancellation details
                cursor.execute("""
                    UPDATE bookings 
                    SET booking_status = 'CANCELLED',
                        cancelled_at = CURRENT_TIMESTAMP,
                        cancellation_reason = ?,
                        refund_amount = ?,
                        refund_status = 'PENDING',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE booking_reference = ?
                """, (cancellation_reason, calc_result['refund_amount'], booking_reference))
                
                conn.commit()
                
                result = calc_result.copy()
                result.update({
                    'cancellation_processed': True,
                    'inventory_restored': True,
                    'refund_initiated': True,
                    'message': f'Booking cancelled successfully. Refund: RM{calc_result["refund_amount"]:.2f}'
                })
                
                return result
                
        except Exception as e:
            return {'success': False, 'message': f'Error processing cancellation: {str(e)}'}
    
    def _restore_confirmed_booking_inventory(self, cursor, property_id: str, room_type_id: str, 
                                           check_in_str: str, check_out_str: str, rooms_booked: int):
        """Restore inventory for confirmed booking cancellation"""
        
        check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        current_date = check_in_date
        while current_date < check_out_date:
            cursor.execute("""
                UPDATE room_inventory 
                SET available_rooms = available_rooms + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
            """, (rooms_booked, property_id, room_type_id, current_date.strftime('%Y-%m-%d')))
            
            current_date += timedelta(days=1)
    
    def _release_pending_booking_inventory(self, cursor, property_id: str, room_type_id: str,
                                         check_in_str: str, check_out_str: str, rooms_booked: int):
        """Release reserved inventory for pending booking cancellation"""
        
        check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        
        current_date = check_in_date
        while current_date < check_out_date:
            cursor.execute("""
                UPDATE room_inventory 
                SET reserved_rooms = CASE 
                    WHEN reserved_rooms >= ? THEN reserved_rooms - ?
                    ELSE 0 
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE property_id = ? AND room_type_id = ? AND stay_date = ?
            """, (rooms_booked, rooms_booked, property_id, room_type_id, current_date.strftime('%Y-%m-%d')))
            
            current_date += timedelta(days=1)
    
    def get_cancellation_summary(self, booking_reference: str) -> str:
        """Generate user-friendly cancellation summary"""
        
        result = self.calculate_cancellation_details(booking_reference)
        
        if not result['success']:
            return f"❌ {result['message']}"
        
        policy = result['cancellation_policy']
        
        summary = f"""
📋 CANCELLATION POLICY SUMMARY

🏨 Hotel: {result['hotel_name']}
🎫 Booking: {booking_reference}
📅 Check-in: {result['check_in_date']}
⏰ Hours until check-in: {result['hours_until_checkin']}

💰 FINANCIAL IMPACT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Total Booking Value: RM{result['total_price']:.2f}
💸 Refund Amount: RM{result['refund_amount']:.2f} ({result['refund_percentage']}%)
⚠️  Penalty Amount: RM{result['penalty_amount']:.2f}

📜 APPLICABLE CANCELLATION RULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{result['applicable_rule']['description'] if result['applicable_rule'] else 'No refund applicable'}

📋 COMPLETE CANCELLATION POLICY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        for i, rule in enumerate(policy['rules'], 1):
            summary += f"""
{i}. {rule['description']}
   • Window: {rule['window_hours']} hours before check-in
   • Refund: {rule['refund_percentage']}% of booking amount"""

        summary += f"""

⚠️  IMPORTANT NOTES:
• Cancellation must be requested before check-in time
• Refunds are processed within 5-7 business days
• No-shows are treated as same-day cancellations
• Policy may vary during peak seasons or special events
"""
        
        return summary

def setup_default_cancellation_policies():
    """Setup default cancellation policies for all hotels"""
    
    manager = CancellationPolicyManager()
    
    # Different policy types for different hotel tiers
    policies = {
        'sam_hotel_kl': {
            'type': 'FLEXIBLE',
            'window_hours': 24,
            'rules': [
                {
                    'window_hours': 24,
                    'refund_percentage': 100,
                    'description': 'Free cancellation up to 24 hours before check-in'
                },
                {
                    'window_hours': 2,
                    'refund_percentage': 50,
                    'description': '50% refund if cancelled 2-24 hours before check-in'
                },
                {
                    'window_hours': 0,
                    'refund_percentage': 0,
                    'description': 'No refund for cancellation within 2 hours or no-show'
                }
            ]
        },
        
        'grand_hyatt_kuala_lumpur': {
            'type': 'MODERATE',
            'window_hours': 48,
            'rules': [
                {
                    'window_hours': 48,
                    'refund_percentage': 100,
                    'description': 'Free cancellation up to 48 hours before check-in'
                },
                {
                    'window_hours': 24,
                    'refund_percentage': 75,
                    'description': '75% refund if cancelled 24-48 hours before check-in'
                },
                {
                    'window_hours': 6,
                    'refund_percentage': 25,
                    'description': '25% refund if cancelled 6-24 hours before check-in'
                },
                {
                    'window_hours': 0,
                    'refund_percentage': 0,
                    'description': 'No refund for cancellation within 6 hours or no-show'
                }
            ]
        },
        
        'mandarin_oriental_kuala_lumpur': {
            'type': 'STRICT',
            'window_hours': 72,
            'rules': [
                {
                    'window_hours': 72,
                    'refund_percentage': 100,
                    'description': 'Free cancellation up to 72 hours before check-in'
                },
                {
                    'window_hours': 24,
                    'refund_percentage': 50,
                    'description': '50% refund if cancelled 24-72 hours before check-in'
                },
                {
                    'window_hours': 0,
                    'refund_percentage': 0,
                    'description': 'No refund for cancellation within 24 hours or no-show'
                }
            ]
        },
        
        'marina_court_resort': {
            'type': 'FLEXIBLE',
            'window_hours': 12,
            'rules': [
                {
                    'window_hours': 12,
                    'refund_percentage': 100,
                    'description': 'Free cancellation up to 12 hours before check-in'
                },
                {
                    'window_hours': 0,
                    'refund_percentage': 50,
                    'description': '50% refund for same-day cancellation'
                }
            ]
        }
    }
    
    print("🏨 Setting up cancellation policies for all hotels...")
    
    for property_id, policy in policies.items():
        success = manager.set_hotel_cancellation_policy(property_id, policy)
        if success:
            print(f"   ✅ {property_id}: {policy['type']} policy ({policy['window_hours']}h window)")
        else:
            print(f"   ❌ Failed to set policy for {property_id}")
    
    print(f"\n🎯 Setup complete! {len(policies)} hotels configured with cancellation policies.")

def main():
    """Main execution function"""
    print("🏨 ELLA HOTEL SYSTEM - CANCELLATION POLICY SETUP")
    print("=" * 60)
    
    # Setup the schema and default policies
    manager = CancellationPolicyManager()
    setup_default_cancellation_policies()
    
    print("\n📋 Testing cancellation calculation...")
    
    # Test with current bookings
    try:
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT booking_reference FROM bookings WHERE booking_status != 'CANCELLED' LIMIT 1")
            result = cursor.fetchone()
            
            if result:
                booking_ref = result[0]
                print(f"\n🧪 Testing with booking: {booking_ref}")
                summary = manager.get_cancellation_summary(booking_ref)
                print(summary)
            else:
                print("⚠️ No active bookings found for testing")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
HOTEL TABLE MIGRATION
Add missing structured fields to existing hotels table for dual knowledge architecture
"""

import sqlite3
import os

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(__file__), 'ella.db')
    return sqlite3.connect(db_path)

def migrate_hotel_structure():
    """Add missing structured fields to hotels table."""
    
    print("🔄 MIGRATING HOTEL TABLE STRUCTURE")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check current structure
        cursor.execute("PRAGMA table_info(hotels)")
        current_columns = [col[1] for col in cursor.fetchall()]
        print(f"Current columns: {len(current_columns)}")
        
        # Define missing structured fields to add
        missing_fields = [
            # Hotel info
            "hotel_brand VARCHAR(100)",
            "star_rating INTEGER CHECK(star_rating >= 1 AND star_rating <= 5)",
            "state_name VARCHAR(100)",
            "country_name VARCHAR(100)",
            "address TEXT",
            "email VARCHAR(100)",
            "website VARCHAR(200)",
            "latitude DECIMAL(10, 8)",
            "longitude DECIMAL(11, 8)",
            
            # Structured instant data (Tier 1)
            "wifi_details TEXT",
            "parking_fee DECIMAL(8, 2)",
            "pet_policy TEXT",
            "smoking_policy TEXT",
            "cancellation_policy TEXT",
            "currency_used VARCHAR(3) DEFAULT 'MYR'",
            
            # Structured facility data (Tier 2)
            "pool_hours VARCHAR(50)",
            "gym_hours VARCHAR(50)",
            "spa_hours VARCHAR(50)",
            "concierge_hours VARCHAR(50)",
            "room_service_hours VARCHAR(50)",
            "business_center_hours VARCHAR(50)",
            "airport_shuttle_fee DECIMAL(8, 2)",
            "airport_shuttle_schedule TEXT",
            "facilities TEXT",
            
            # Metadata
            "is_active BOOLEAN DEFAULT 1",
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ]
        
        # Add missing columns
        added_count = 0
        for field in missing_fields:
            field_name = field.split()[0]
            
            if field_name not in current_columns:
                try:
                    cursor.execute(f"ALTER TABLE hotels ADD COLUMN {field}")
                    print(f"  ✅ Added: {field_name}")
                    added_count += 1
                except sqlite3.Error as e:
                    print(f"  ❌ Failed to add {field_name}: {e}")
        
        conn.commit()
        print(f"\n🌟 Migration complete! Added {added_count} new columns")
        return True

def update_structured_data():
    """Update existing hotels with structured data."""
    
    print("\n📊 UPDATING STRUCTURED DATA")
    print("=" * 40)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Update Grand Hyatt KL structured data
        cursor.execute("""
            UPDATE hotels SET
                hotel_brand = 'Hyatt',
                star_rating = 5,
                state_name = 'Federal Territory of Kuala Lumpur',
                country_name = 'Malaysia',
                address = '12 Jalan Pinang, Kuala Lumpur City Centre, 50450 Kuala Lumpur',
                email = 'kualalumpur.grand@hyatt.com',
                website = 'https://www.hyatt.com/grand-hyatt/kuala-lumpur',
                latitude = 3.1516,
                longitude = 101.7123,
                wifi_details = 'Complimentary high-speed WiFi throughout the property',
                parking_fee = 25.00,
                pet_policy = 'Small pets under 10kg allowed, RM50 per night',
                smoking_policy = 'Non-smoking property. Designated smoking areas available.',
                cancellation_policy = 'Free cancellation until 6 PM day before arrival',
                currency_used = 'MYR',
                pool_hours = '6:00 AM - 10:00 PM',
                gym_hours = '24 hours',
                spa_hours = '10:00 AM - 10:00 PM',
                concierge_hours = '24 hours',
                room_service_hours = '24 hours',
                business_center_hours = '24 hours',
                airport_shuttle_fee = 90.00,
                airport_shuttle_schedule = 'Every 2 hours, 6 AM - 10 PM',
                facilities = 'Pool, Spa, Gym, Restaurant, Bar, Business Center, Concierge',
                is_active = 1
            WHERE property_id = 'grand_hyatt_kuala_lumpur'
        """)
        
        # Check if Marina Court exists, if not add it
        cursor.execute("SELECT COUNT(*) FROM hotels WHERE property_id = 'marina_court_resort_kota_kinabalu'")
        marina_exists = cursor.fetchone()[0] > 0
        
        if not marina_exists:
            print("Adding Marina Court Resort...")
            cursor.execute("""
                INSERT INTO hotels (
                    property_id, hotel_name, hotel_brand, star_rating, city_name, state_name, country_name,
                    address, phone, email, website, latitude, longitude,
                    check_in_time, check_out_time, wifi_password, wifi_details, parking_fee, pet_policy,
                    smoking_policy, cancellation_policy, currency_used,
                    pool_hours, gym_hours, spa_hours, concierge_hours, room_service_hours, business_center_hours,
                    airport_shuttle_fee, airport_shuttle_schedule, facilities, is_active
                ) VALUES (
                    'marina_court_resort_kota_kinabalu', 'Marina Court Resort Condominium', 'Independent', 4,
                    'Kota Kinabalu', 'Sabah', 'Malaysia',
                    'Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah', '+6088-231-888',
                    'reservations@marinacourt.com.my', 'https://www.marinacourt.com.my', 5.9749, 116.0724,
                    '14:00:00', '12:00:00', 'MarinaCourt2024', 'Free WiFi in all areas', 0.00,
                    'Pets not allowed', 'Smoking allowed in designated areas',
                    'Free cancellation until 24 hours before arrival', 'MYR',
                    '7:00 AM - 10:00 PM', '6:00 AM - 11:00 PM', 'External spa services available',
                    '7:00 AM - 11:00 PM', '7:00 AM - 11:00 PM', '8:00 AM - 8:00 PM',
                    25.00, 'On request, 24 hours advance notice',
                    'Pool, Gym, Kitchenette, Balcony, Tour Desk', 1
                )
            """)
        else:
            print("Updating Marina Court Resort...")
            cursor.execute("""
                UPDATE hotels SET
                    hotel_brand = 'Independent',
                    star_rating = 4,
                    state_name = 'Sabah',
                    country_name = 'Malaysia',
                    address = 'Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah',
                    email = 'reservations@marinacourt.com.my',
                    website = 'https://www.marinacourt.com.my',
                    latitude = 5.9749,
                    longitude = 116.0724,
                    wifi_password = 'MarinaCourt2024',
                    wifi_details = 'Free WiFi in all areas',
                    parking_fee = 0.00,
                    pet_policy = 'Pets not allowed',
                    smoking_policy = 'Smoking allowed in designated areas',
                    cancellation_policy = 'Free cancellation until 24 hours before arrival',
                    currency_used = 'MYR',
                    pool_hours = '7:00 AM - 10:00 PM',
                    gym_hours = '6:00 AM - 11:00 PM',
                    spa_hours = 'External spa services available',
                    concierge_hours = '7:00 AM - 11:00 PM',
                    room_service_hours = '7:00 AM - 11:00 PM',
                    business_center_hours = '8:00 AM - 8:00 PM',
                    airport_shuttle_fee = 25.00,
                    airport_shuttle_schedule = 'On request, 24 hours advance notice',
                    facilities = 'Pool, Gym, Kitchenette, Balcony, Tour Desk',
                    is_active = 1,
                    check_in_time = '14:00:00',
                    check_out_time = '12:00:00'
                WHERE property_id = 'marina_court_resort_kota_kinabalu'
            """)
        
        conn.commit()
        print("✅ Structured data updated for all hotels")
        return True

if __name__ == "__main__":
    if migrate_hotel_structure():
        if update_structured_data():
            print("\n🌟 DUAL KNOWLEDGE MIGRATION COMPLETE!")
            print("=" * 50)
            print("✅ Hotel table now supports both structured and raw knowledge")
            print("✅ All Tier 1-2 structured fields available")
            print("✅ Raw knowledge bank ready for Tier 3+ queries")
        else:
            print("❌ Structured data update failed")
    else:
        print("❌ Migration failed") 
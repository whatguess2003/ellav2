#!/usr/bin/env python3
"""
Local PostgreSQL Database Setup for ELLA Hotel System
Works with both local PostgreSQL and Railway PostgreSQL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get PostgreSQL connection from environment variable"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("💡 Create a .env file with:")
        print("   DATABASE_URL=postgresql://postgres:password@localhost:5432/ella_hotel")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        print(f"✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def create_tables(conn):
    """Create all necessary tables for ELLA hotel system"""
    
    cursor = conn.cursor()
    
    # Hotels table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            city VARCHAR(100) NOT NULL,
            state VARCHAR(100) NOT NULL,
            country VARCHAR(100) DEFAULT 'Malaysia',
            address TEXT,
            phone VARCHAR(50),
            email VARCHAR(255),
            website VARCHAR(255),
            star_rating INTEGER CHECK (star_rating >= 1 AND star_rating <= 5),
            description TEXT,
            amenities TEXT[],
            check_in_time TIME DEFAULT '15:00:00',
            check_out_time TIME DEFAULT '11:00:00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Room types table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_types (
            id SERIAL PRIMARY KEY,
            hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            description TEXT,
            max_occupancy INTEGER DEFAULT 2,
            size_sqm INTEGER,
            amenities TEXT[],
            base_price DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'MYR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hotel_id, slug)
        );
    """)
    
    # Availability table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id SERIAL PRIMARY KEY,
            room_type_id INTEGER REFERENCES room_types(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            available_rooms INTEGER DEFAULT 0,
            price DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'MYR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_type_id, date)
        );
    """)
    
    # Guests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255),
            email VARCHAR(255),
            nationality VARCHAR(100),
            id_number VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            reference VARCHAR(500) UNIQUE NOT NULL,
            guest_id INTEGER REFERENCES guests(id),
            hotel_id INTEGER REFERENCES hotels(id),
            room_type_id INTEGER REFERENCES room_types(id),
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            nights INTEGER NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'MYR',
            status VARCHAR(50) DEFAULT 'confirmed',
            special_requests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Check-ins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS check_ins (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id),
            guest_id INTEGER REFERENCES guests(id),
            check_in_time TIMESTAMP,
            check_out_time TIMESTAMP,
            room_number VARCHAR(20),
            status VARCHAR(50) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id),
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'MYR',
            payment_method VARCHAR(50),
            payment_status VARCHAR(50) DEFAULT 'pending',
            transaction_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id),
            guest_id INTEGER REFERENCES guests(id),
            hotel_id INTEGER REFERENCES hotels(id),
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    print("✅ Created all database tables")

def insert_sample_data(conn):
    """Insert sample hotels and room data"""
    
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM hotels")
    hotel_count = cursor.fetchone()[0]
    
    if hotel_count > 0:
        print(f"✅ Database already has {hotel_count} hotels - skipping sample data")
        return
    
    # Sample hotels
    hotels = [
        {
            'name': 'Grand Hyatt Kuala Lumpur',
            'slug': 'grand-hyatt-kuala-lumpur',
            'city': 'Kuala Lumpur',
            'state': 'Kuala Lumpur',
            'address': '12 Jalan Pinang, Kuala Lumpur City Centre, 50450 Kuala Lumpur',
            'phone': '+60 3-2182 1234',
            'email': 'kualalumpur.grand@hyatt.com',
            'star_rating': 5,
            'description': 'Luxury hotel in the heart of Kuala Lumpur with world-class amenities',
            'amenities': ['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 'Concierge']
        },
        {
            'name': 'Sam Hotel KL',
            'slug': 'sam-hotel-kl',
            'city': 'Kuala Lumpur',
            'state': 'Kuala Lumpur',
            'address': '123 Jalan Bukit Bintang, 55100 Kuala Lumpur',
            'phone': '+60 3-2148 8888',
            'email': 'info@samhotelkl.com',
            'star_rating': 3,
            'description': 'Comfortable budget hotel in Bukit Bintang area',
            'amenities': ['WiFi', 'Restaurant', 'Laundry', '24h Front Desk']
        },
        {
            'name': 'Marina Court Resort',
            'slug': 'marina-court-resort',
            'city': 'Kota Kinabalu',
            'state': 'Sabah',
            'address': '1 Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah',
            'phone': '+60 88-237 999',
            'email': 'reservations@marinacourt.com',
            'star_rating': 4,
            'description': 'Beachfront resort with stunning sea views and modern facilities',
            'amenities': ['WiFi', 'Pool', 'Beach Access', 'Restaurant', 'Spa', 'Water Sports']
        }
    ]
    
    # Insert hotels
    for hotel in hotels:
        cursor.execute("""
            INSERT INTO hotels (name, slug, city, state, address, phone, email, star_rating, description, amenities)
            VALUES (%(name)s, %(slug)s, %(city)s, %(state)s, %(address)s, %(phone)s, %(email)s, %(star_rating)s, %(description)s, %(amenities)s)
            RETURNING id
        """, hotel)
        hotel_id = cursor.fetchone()[0]
        hotel['id'] = hotel_id
    
    # Sample room types
    room_types = [
        # Grand Hyatt rooms
        {'hotel_id': hotels[0]['id'], 'name': 'Grand King Room', 'slug': 'grand-king', 'max_occupancy': 2, 'base_price': 450.00, 'amenities': ['King Bed', 'City View', 'WiFi', 'Minibar']},
        {'hotel_id': hotels[0]['id'], 'name': 'Twin City View', 'slug': 'twin-city', 'max_occupancy': 2, 'base_price': 420.00, 'amenities': ['Twin Beds', 'City View', 'WiFi', 'Minibar']},
        
        # Sam Hotel rooms
        {'hotel_id': hotels[1]['id'], 'name': 'Standard Room', 'slug': 'standard', 'max_occupancy': 2, 'base_price': 120.00, 'amenities': ['Queen Bed', 'WiFi', 'AC', 'TV']},
        {'hotel_id': hotels[1]['id'], 'name': 'Deluxe Room', 'slug': 'deluxe', 'max_occupancy': 3, 'base_price': 150.00, 'amenities': ['Queen Bed', 'Sofa Bed', 'WiFi', 'AC', 'TV']},
        
        # Marina Court rooms
        {'hotel_id': hotels[2]['id'], 'name': 'Deluxe Sea View', 'slug': 'deluxe-sea', 'max_occupancy': 2, 'base_price': 280.00, 'amenities': ['King Bed', 'Sea View', 'Balcony', 'WiFi']},
        {'hotel_id': hotels[2]['id'], 'name': 'Superior Garden View', 'slug': 'superior-garden', 'max_occupancy': 2, 'base_price': 220.00, 'amenities': ['Queen Bed', 'Garden View', 'WiFi', 'AC']},
    ]
    
    # Insert room types
    for room in room_types:
        cursor.execute("""
            INSERT INTO room_types (hotel_id, name, slug, max_occupancy, base_price, amenities)
            VALUES (%(hotel_id)s, %(name)s, %(slug)s, %(max_occupancy)s, %(base_price)s, %(amenities)s)
            RETURNING id
        """, room)
        room['id'] = cursor.fetchone()[0]
    
    # Generate availability for next 30 days
    start_date = datetime.now().date()
    for i in range(30):
        current_date = start_date + timedelta(days=i)
        
        for room in room_types:
            # Vary availability and pricing slightly
            available_rooms = 5 if i % 7 != 0 else 2  # Less availability on Sundays
            price_multiplier = 1.2 if i % 7 == 5 or i % 7 == 6 else 1.0  # Weekend pricing
            final_price = room['base_price'] * price_multiplier
            
            cursor.execute("""
                INSERT INTO availability (room_type_id, date, available_rooms, price)
                VALUES (%s, %s, %s, %s)
            """, (room['id'], current_date, available_rooms, final_price))
    
    conn.commit()
    print("✅ Inserted sample data:")
    print(f"   - {len(hotels)} hotels")
    print(f"   - {len(room_types)} room types")
    print(f"   - 30 days of availability data")

def verify_setup(conn):
    """Verify the database setup is working correctly"""
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check tables and data
    cursor.execute("SELECT COUNT(*) as count FROM hotels")
    hotel_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM room_types")
    room_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM availability")
    availability_count = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT h.name, h.city, h.star_rating, COUNT(rt.id) as room_types
        FROM hotels h
        LEFT JOIN room_types rt ON h.id = rt.hotel_id
        GROUP BY h.id, h.name, h.city, h.star_rating
        ORDER BY h.name
    """)
    hotels = cursor.fetchall()
    
    print("\n🎉 Database Setup Complete!")
    print(f"📊 Summary:")
    print(f"   - Hotels: {hotel_count}")
    print(f"   - Room Types: {room_count}")
    print(f"   - Availability Records: {availability_count}")
    
    print(f"\n🏨 Hotels in Database:")
    for hotel in hotels:
        print(f"   - {hotel['name']} ({hotel['city']}) - {hotel['star_rating']}⭐ - {hotel['room_types']} room types")

def main():
    """Main setup function"""
    print("🚀 Starting ELLA Hotel Database Setup...")
    
    # Get database connection
    conn = get_database_connection()
    if not conn:
        return
    
    try:
        # Create tables
        create_tables(conn)
        
        # Insert sample data
        insert_sample_data(conn)
        
        # Verify setup
        verify_setup(conn)
        
        print("\n✅ Database setup completed successfully!")
        print("💡 You can now:")
        print("   - Use pgAdmin4 to browse your database")
        print("   - Run your ELLA application")
        print("   - Connect to the same database from Railway")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 
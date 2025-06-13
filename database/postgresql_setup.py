#!/usr/bin/env python3
"""
PostgreSQL Database Setup for Railway Deployment
Migrates SQLite database to PostgreSQL for production use
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def get_database_url():
    """Get PostgreSQL connection URL from Railway environment"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Fallback to individual components
        host = os.getenv('PGHOST', 'localhost')
        port = os.getenv('PGPORT', '5432')
        database = os.getenv('PGDATABASE', 'ella_hotel')
        user = os.getenv('PGUSER', 'postgres')
        password = os.getenv('PGPASSWORD', '')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    return database_url

def create_postgresql_schema(pg_conn):
    """Create PostgreSQL schema matching SQLite structure"""
    
    schema_sql = """
    -- Drop existing tables if they exist
    DROP TABLE IF EXISTS booking_analytics CASCADE;
    DROP TABLE IF EXISTS media_analytics CASCADE;
    DROP TABLE IF EXISTS production_media_files CASCADE;
    DROP TABLE IF EXISTS hotel_bookings CASCADE;
    DROP TABLE IF EXISTS room_availability CASCADE;
    DROP TABLE IF EXISTS hotel_rooms CASCADE;
    DROP TABLE IF EXISTS hotels CASCADE;
    DROP TABLE IF EXISTS hotel_amenities CASCADE;
    DROP TABLE IF EXISTS room_amenities CASCADE;
    
    -- Hotels table
    CREATE TABLE hotels (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        location VARCHAR(255) NOT NULL,
        address TEXT,
        phone VARCHAR(50),
        email VARCHAR(255),
        star_rating INTEGER DEFAULT 3,
        description TEXT,
        check_in_time VARCHAR(10) DEFAULT '15:00',
        check_out_time VARCHAR(10) DEFAULT '12:00',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Hotel amenities
    CREATE TABLE hotel_amenities (
        id SERIAL PRIMARY KEY,
        hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
        amenity_name VARCHAR(100) NOT NULL,
        amenity_type VARCHAR(50) DEFAULT 'general',
        description TEXT,
        is_available BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Hotel rooms
    CREATE TABLE hotel_rooms (
        id SERIAL PRIMARY KEY,
        hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
        room_type VARCHAR(100) NOT NULL,
        room_name VARCHAR(255),
        base_price DECIMAL(10,2) NOT NULL,
        max_occupancy INTEGER DEFAULT 2,
        room_size VARCHAR(50),
        bed_type VARCHAR(100),
        description TEXT,
        is_available BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Room amenities
    CREATE TABLE room_amenities (
        id SERIAL PRIMARY KEY,
        room_id INTEGER REFERENCES hotel_rooms(id) ON DELETE CASCADE,
        amenity_name VARCHAR(100) NOT NULL,
        amenity_type VARCHAR(50) DEFAULT 'room',
        description TEXT,
        is_included BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Room availability
    CREATE TABLE room_availability (
        id SERIAL PRIMARY KEY,
        hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
        room_id INTEGER REFERENCES hotel_rooms(id) ON DELETE CASCADE,
        date DATE NOT NULL,
        available_rooms INTEGER DEFAULT 0,
        total_rooms INTEGER DEFAULT 1,
        price_per_night DECIMAL(10,2),
        is_blocked BOOLEAN DEFAULT false,
        block_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(hotel_id, room_id, date)
    );
    
    -- Hotel bookings
    CREATE TABLE hotel_bookings (
        id SERIAL PRIMARY KEY,
        booking_reference VARCHAR(50) UNIQUE NOT NULL,
        hotel_id INTEGER REFERENCES hotels(id),
        room_id INTEGER REFERENCES hotel_rooms(id),
        guest_name VARCHAR(255) NOT NULL,
        guest_email VARCHAR(255),
        guest_phone VARCHAR(50),
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
        nights INTEGER NOT NULL,
        rooms_booked INTEGER DEFAULT 1,
        adults INTEGER DEFAULT 2,
        children INTEGER DEFAULT 0,
        total_price DECIMAL(10,2) NOT NULL,
        booking_status VARCHAR(50) DEFAULT 'confirmed',
        payment_status VARCHAR(50) DEFAULT 'pending',
        special_requests TEXT,
        guest_id VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Media files (for hotel photos)
    CREATE TABLE production_media_files (
        id SERIAL PRIMARY KEY,
        file_id VARCHAR(100) UNIQUE NOT NULL,
        original_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(50) NOT NULL,
        file_size INTEGER,
        local_path TEXT,
        cloud_url TEXT,
        hotel_id INTEGER REFERENCES hotels(id),
        room_id INTEGER REFERENCES hotel_rooms(id),
        category VARCHAR(50) DEFAULT 'general',
        tags TEXT,
        description TEXT,
        is_public BOOLEAN DEFAULT true,
        uploaded_by VARCHAR(100) DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Analytics tables
    CREATE TABLE booking_analytics (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER REFERENCES hotel_bookings(id),
        event_type VARCHAR(50) NOT NULL,
        event_data JSONB,
        guest_id VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE media_analytics (
        id SERIAL PRIMARY KEY,
        file_id VARCHAR(100),
        event_type VARCHAR(50) NOT NULL,
        user_id VARCHAR(100),
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX idx_hotels_location ON hotels(location);
    CREATE INDEX idx_hotels_star_rating ON hotels(star_rating);
    CREATE INDEX idx_room_availability_date ON room_availability(date);
    CREATE INDEX idx_room_availability_hotel_date ON room_availability(hotel_id, date);
    CREATE INDEX idx_bookings_reference ON hotel_bookings(booking_reference);
    CREATE INDEX idx_bookings_guest ON hotel_bookings(guest_name, guest_email);
    CREATE INDEX idx_bookings_dates ON hotel_bookings(check_in_date, check_out_date);
    CREATE INDEX idx_media_hotel ON production_media_files(hotel_id);
    CREATE INDEX idx_media_category ON production_media_files(category);
    """
    
    with pg_conn.cursor() as cursor:
        cursor.execute(schema_sql)
    pg_conn.commit()
    print("✅ PostgreSQL schema created successfully")

def migrate_sqlite_to_postgresql():
    """Migrate data from SQLite to PostgreSQL"""
    
    # Connect to SQLite
    sqlite_path = os.path.join(os.path.dirname(__file__), 'ella.db')
    if not os.path.exists(sqlite_path):
        sqlite_path = 'ella.db'  # Try root directory
    
    if not os.path.exists(sqlite_path):
        print("❌ SQLite database not found. Creating empty PostgreSQL database.")
        return
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL
    database_url = get_database_url()
    pg_conn = psycopg2.connect(database_url)
    
    try:
        # Create schema
        create_postgresql_schema(pg_conn)
        
        # Migrate tables
        tables_to_migrate = [
            'hotels',
            'hotel_amenities', 
            'hotel_rooms',
            'room_amenities',
            'room_availability',
            'hotel_bookings',
            'production_media_files',
            'booking_analytics',
            'media_analytics'
        ]
        
        for table in tables_to_migrate:
            migrate_table(sqlite_conn, pg_conn, table)
        
        print("✅ Database migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a specific table from SQLite to PostgreSQL"""
    
    try:
        # Check if table exists in SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not sqlite_cursor.fetchone():
            print(f"⚠️ Table {table_name} not found in SQLite, skipping")
            return
        
        # Get data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"⚠️ No data in {table_name}, skipping")
            return
        
        # Get column names
        columns = [description[0] for description in sqlite_cursor.description]
        
        # Insert into PostgreSQL
        pg_cursor = pg_conn.cursor()
        
        # Handle special cases for auto-increment columns
        filtered_columns = []
        filtered_values = []
        
        for row in rows:
            row_values = []
            for i, col in enumerate(columns):
                if col == 'id' and table_name in ['hotels', 'hotel_rooms', 'hotel_bookings', 'production_media_files']:
                    # Skip auto-increment ID columns, let PostgreSQL handle them
                    continue
                filtered_columns.append(col) if i == 0 else None
                row_values.append(row[i])
            
            if len(filtered_columns) == 0:  # First row, set filtered columns
                filtered_columns = [col for col in columns if not (col == 'id' and table_name in ['hotels', 'hotel_rooms', 'hotel_bookings', 'production_media_files'])]
            
            filtered_values.append(row_values)
        
        # Create INSERT statement
        if filtered_columns and filtered_values:
            placeholders = ','.join(['%s'] * len(filtered_columns))
            insert_sql = f"INSERT INTO {table_name} ({','.join(filtered_columns)}) VALUES ({placeholders})"
            
            pg_cursor.executemany(insert_sql, filtered_values)
            pg_conn.commit()
            
            print(f"✅ Migrated {len(filtered_values)} rows to {table_name}")
        
    except Exception as e:
        print(f"❌ Failed to migrate {table_name}: {e}")
        pg_conn.rollback()

def seed_sample_data(pg_conn):
    """Add sample hotel data"""
    
    sample_data_sql = """
    -- Insert sample hotels
    INSERT INTO hotels (name, location, address, phone, star_rating, description) VALUES
    ('Grand Hyatt Kuala Lumpur', 'Kuala Lumpur', 'Jalan Pinang, Kuala Lumpur City Centre, 50088 Kuala Lumpur', '+60 3-2182 1234', 5, 'Luxury 5-star hotel in the heart of KLCC'),
    ('Sam Hotel KL', 'Kuala Lumpur', 'Jalan Chow Kit, 50350 Kuala Lumpur', '+60 3-4041 7777', 3, 'Budget-friendly hotel in Chow Kit area'),
    ('Marina Court Resort Condominium', 'Kota Kinabalu', 'Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah', '+60 88-318 888', 4, 'Beachfront resort in Kota Kinabalu')
    ON CONFLICT DO NOTHING;
    
    -- Insert sample rooms
    INSERT INTO hotel_rooms (hotel_id, room_type, room_name, base_price, max_occupancy, bed_type, description) VALUES
    (1, 'Deluxe King', 'Grand Deluxe King Room', 450.00, 2, 'King Bed', 'Spacious room with city view and luxury amenities'),
    (1, 'Deluxe Twin', 'Grand Deluxe Twin Room', 450.00, 2, 'Twin Beds', 'Comfortable twin bed room with modern facilities'),
    (2, 'Standard Double', 'Standard Double Room', 120.00, 2, 'Double Bed', 'Clean and comfortable budget room'),
    (3, 'Ocean View Suite', 'Marina Ocean View Suite', 280.00, 4, 'King + Sofa Bed', 'Beautiful ocean view suite with balcony')
    ON CONFLICT DO NOTHING;
    
    -- Insert sample availability (next 30 days)
    INSERT INTO room_availability (hotel_id, room_id, date, available_rooms, total_rooms, price_per_night)
    SELECT 
        h.id as hotel_id,
        r.id as room_id,
        CURRENT_DATE + INTERVAL '1 day' * generate_series(0, 29) as date,
        CASE 
            WHEN h.id = 1 THEN 5  -- Grand Hyatt has 5 rooms per type
            WHEN h.id = 2 THEN 10 -- Sam Hotel has 10 rooms per type
            ELSE 3                -- Marina Court has 3 rooms per type
        END as available_rooms,
        CASE 
            WHEN h.id = 1 THEN 5
            WHEN h.id = 2 THEN 10
            ELSE 3
        END as total_rooms,
        r.base_price as price_per_night
    FROM hotels h
    CROSS JOIN hotel_rooms r
    WHERE r.hotel_id = h.id
    ON CONFLICT (hotel_id, room_id, date) DO NOTHING;
    """
    
    with pg_conn.cursor() as cursor:
        cursor.execute(sample_data_sql)
    pg_conn.commit()
    print("✅ Sample data inserted successfully")

def test_postgresql_connection():
    """Test PostgreSQL connection and basic operations"""
    
    try:
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Test basic query
            cursor.execute("SELECT COUNT(*) as hotel_count FROM hotels")
            result = cursor.fetchone()
            
            print(f"✅ PostgreSQL connection successful")
            print(f"📊 Hotels in database: {result['hotel_count']}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up PostgreSQL database for Railway...")
    
    try:
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        
        # Create schema and seed data
        create_postgresql_schema(conn)
        seed_sample_data(conn)
        
        conn.close()
        
        print("✅ Database setup completed successfully!")
        
        # Test the setup
        test_postgresql_connection()
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("Make sure PostgreSQL service is added to Railway project")
        exit(1) 
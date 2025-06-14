#!/usr/bin/env python3
"""
ELLA PostgreSQL Schema Creation Script
Creates database schema for Railway PostgreSQL deployment
"""

import os
import sys
from database.postgresql_connection import db_manager, execute_update

def create_database_schema():
    """Create all database tables and indexes"""
    
    print("🚀 Starting ELLA PostgreSQL Schema Creation...")
    print(f"🔗 Database Type: {db_manager.db_type}")
    
    if db_manager.db_type != 'postgresql':
        print("⚠️  Warning: Not connected to PostgreSQL. Schema optimized for PostgreSQL.")
    
    # Drop tables if they exist (for clean reinstall)
    drop_tables = [
        "DROP TABLE IF EXISTS reviews CASCADE",
        "DROP TABLE IF EXISTS payments CASCADE", 
        "DROP TABLE IF EXISTS check_ins CASCADE",
        "DROP TABLE IF EXISTS bookings CASCADE",
        "DROP TABLE IF EXISTS availability CASCADE",
        "DROP TABLE IF EXISTS room_types CASCADE",
        "DROP TABLE IF EXISTS guests CASCADE",
        "DROP TABLE IF EXISTS hotels CASCADE"
    ]
    
    print("🗑️  Dropping existing tables...")
    for drop_sql in drop_tables:
        try:
            execute_update(drop_sql)
            print(f"   ✅ {drop_sql.split()[4]}")
        except Exception as e:
            print(f"   ⚠️  {drop_sql.split()[4]}: {e}")
    
    # Create tables
    tables = {
        "hotels": """
            CREATE TABLE hotels (
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
            )
        """,
        
        "room_types": """
            CREATE TABLE room_types (
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
            )
        """,
        
        "availability": """
            CREATE TABLE availability (
                id SERIAL PRIMARY KEY,
                room_type_id INTEGER REFERENCES room_types(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                available_rooms INTEGER DEFAULT 0,
                price DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'MYR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(room_type_id, date)
            )
        """,
        
        "guests": """
            CREATE TABLE guests (
                id SERIAL PRIMARY KEY,
                phone VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(255),
                email VARCHAR(255),
                nationality VARCHAR(100),
                id_number VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        "bookings": """
            CREATE TABLE bookings (
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
            )
        """,
        
        "check_ins": """
            CREATE TABLE check_ins (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER REFERENCES bookings(id),
                guest_id INTEGER REFERENCES guests(id),
                check_in_time TIMESTAMP,
                check_out_time TIMESTAMP,
                room_number VARCHAR(20),
                status VARCHAR(50) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        "payments": """
            CREATE TABLE payments (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER REFERENCES bookings(id),
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'MYR',
                payment_method VARCHAR(50),
                payment_status VARCHAR(50) DEFAULT 'pending',
                transaction_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        "reviews": """
            CREATE TABLE reviews (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER REFERENCES bookings(id),
                guest_id INTEGER REFERENCES guests(id),
                hotel_id INTEGER REFERENCES hotels(id),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    }
    
    print("🏗️  Creating database tables...")
    for table_name, create_sql in tables.items():
        try:
            execute_update(create_sql)
            print(f"   ✅ {table_name}")
        except Exception as e:
            print(f"   ❌ {table_name}: {e}")
            return False
    
    # Create indexes
    indexes = [
        "CREATE INDEX idx_hotels_city ON hotels(city)",
        "CREATE INDEX idx_hotels_state ON hotels(state)",
        "CREATE INDEX idx_room_types_hotel_id ON room_types(hotel_id)",
        "CREATE INDEX idx_availability_date ON availability(date)",
        "CREATE INDEX idx_availability_room_type_date ON availability(room_type_id, date)",
        "CREATE INDEX idx_bookings_guest_id ON bookings(guest_id)",
        "CREATE INDEX idx_bookings_hotel_id ON bookings(hotel_id)",
        "CREATE INDEX idx_bookings_dates ON bookings(check_in_date, check_out_date)",
        "CREATE INDEX idx_guests_phone ON guests(phone)"
    ]
    
    print("📊 Creating database indexes...")
    for index_sql in indexes:
        try:
            execute_update(index_sql)
            index_name = index_sql.split()[2]
            print(f"   ✅ {index_name}")
        except Exception as e:
            index_name = index_sql.split()[2]
            print(f"   ⚠️  {index_name}: {e}")
    
    print("🎉 ELLA PostgreSQL Schema Created Successfully!")
    return True

def verify_schema():
    """Verify that all tables were created"""
    print("\n🔍 Verifying schema creation...")
    
    expected_tables = ['hotels', 'room_types', 'availability', 'guests', 'bookings', 'check_ins', 'payments', 'reviews']
    
    try:
        from database.postgresql_connection import execute_query
        
        if db_manager.db_type == 'postgresql':
            # PostgreSQL query
            result = execute_query("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('hotels', 'room_types', 'availability', 'guests', 'bookings', 'check_ins', 'payments', 'reviews')
                ORDER BY table_name
            """)
        else:
            # SQLite query
            result = execute_query("""
                SELECT name as table_name FROM sqlite_master 
                WHERE type='table' 
                AND name IN ('hotels', 'room_types', 'availability', 'guests', 'bookings', 'check_ins', 'payments', 'reviews')
                ORDER BY name
            """)
        
        created_tables = [row['table_name'] for row in result]
        
        print(f"📋 Tables created: {len(created_tables)}/{len(expected_tables)}")
        for table in expected_tables:
            if table in created_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - MISSING")
        
        if len(created_tables) == len(expected_tables):
            print("🎊 All tables created successfully!")
            return True
        else:
            print("⚠️  Some tables missing!")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("=" * 60)
    print("ELLA PostgreSQL Schema Creation")
    print("=" * 60)
    
    # Check database connection
    health = db_manager.health_check()
    if health['status'] != 'healthy':
        print(f"❌ Database connection failed: {health.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Create schema
    success = create_database_schema()
    if not success:
        print("❌ Schema creation failed!")
        sys.exit(1)
    
    # Verify schema
    verified = verify_schema()
    if not verified:
        print("⚠️  Schema verification had issues!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ ELLA PostgreSQL Schema Ready!")
    print("🎯 Next step: Run seed_data.py to add sample hotels")
    print("=" * 60)

if __name__ == "__main__":
    main() 
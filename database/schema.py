#!/usr/bin/env python3
"""
Hotel Database Schema Definition
Hierarchical structure: Country -> State -> City -> Hotel -> Room -> Inventory -> Bookings
"""

import sqlite3
from datetime import datetime
from typing import Optional

class HotelDatabaseSchema:
    """Manages the hotel database schema creation and structure."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def create_all_tables(self):
        """Create all tables in the proper order (respecting foreign key dependencies)."""
        
        print("🏗️ CREATING HOTEL DATABASE SCHEMA")
        print("=" * 50)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # 1. Countries table
            print("📍 Creating countries table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS countries (
                    country_name VARCHAR(100) PRIMARY KEY,
                    currency_code VARCHAR(3) NOT NULL,
                    phone_prefix VARCHAR(10),
                    country_code VARCHAR(2),  -- Optional reference for legacy systems
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. States table
            print("🏛️ Creating states table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    state_name VARCHAR(100) PRIMARY KEY,
                    country_name VARCHAR(100) NOT NULL,
                    timezone VARCHAR(50),
                    state_code VARCHAR(10),  -- Optional reference for legacy systems
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (country_name) REFERENCES countries(country_name)
                )
            """)
            
            # 3. Cities table
            print("🏙️ Creating cities table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    city_name VARCHAR(100) NOT NULL,
                    state_name VARCHAR(100) NOT NULL,
                    country_name VARCHAR(100) NOT NULL,
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    airport_code VARCHAR(3),
                    city_code VARCHAR(10),  -- Optional reference for legacy systems
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (city_name, state_name, country_name),
                    FOREIGN KEY (state_name) REFERENCES states(state_name),
                    FOREIGN KEY (country_name) REFERENCES countries(country_name)
                )
            """)
            
            # 4. Hotels table
            print("🏨 Creating hotels table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hotels (
                    property_id VARCHAR(200) PRIMARY KEY,
                    hotel_name VARCHAR(200) NOT NULL,
                    hotel_brand VARCHAR(100),
                    star_rating INTEGER CHECK(star_rating >= 1 AND star_rating <= 5),
                    city_name VARCHAR(100) NOT NULL,
                    state_name VARCHAR(100) NOT NULL,
                    country_name VARCHAR(100) NOT NULL,
                    address TEXT,
                    postcode VARCHAR(20),
                    phone VARCHAR(20),
                    email VARCHAR(100),
                    website VARCHAR(200),
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    distance_to_airport_km DECIMAL(5, 2),
                    check_in_time TIME DEFAULT '15:00:00',
                    check_out_time TIME DEFAULT '12:00:00',
                    description TEXT,
                    facilities TEXT, -- JSON array of facilities
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (city_name, state_name, country_name) REFERENCES cities(city_name, state_name, country_name)
                )
            """)
            
            # 5. Room types table
            print("🛏️ Creating room_types table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_types (
                    room_type_id VARCHAR(200) PRIMARY KEY,
                    property_id VARCHAR(200) NOT NULL,
                    room_name VARCHAR(100) NOT NULL,
                    room_description TEXT,
                    bed_type VARCHAR(50), -- King, Queen, Twin, Single
                    view_type VARCHAR(50), -- Sea, Pool, City, Garden, Mountain
                    room_size_sqm INTEGER,
                    max_occupancy INTEGER NOT NULL,
                    base_price_per_night DECIMAL(10, 2) NOT NULL,
                    amenities TEXT, -- JSON array of room amenities
                    room_features TEXT, -- JSON array of room features
                    total_rooms INTEGER NOT NULL DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES hotels(property_id)
                )
            """)
            
            # 6. Room inventory table (availability and pricing per date)
            print("📅 Creating room_inventory table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_inventory (
                    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id VARCHAR(200) NOT NULL,
                    room_type_id VARCHAR(200) NOT NULL,
                    stay_date DATE NOT NULL,
                    available_rooms INTEGER NOT NULL DEFAULT 0,
                    base_price DECIMAL(10, 2) NOT NULL,
                    current_price DECIMAL(10, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'MYR',
                    price_last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    demand_level VARCHAR(20) DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, PEAK
                    min_stay_nights INTEGER DEFAULT 1,
                    max_stay_nights INTEGER DEFAULT 30,
                    booking_rules TEXT, -- JSON for special booking rules
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES hotels(property_id),
                    FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id),
                    UNIQUE(property_id, room_type_id, stay_date)
                )
            """)
            
            # 7. Bookings table
            print("📝 Creating bookings table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_reference VARCHAR(50) UNIQUE NOT NULL,
                    property_id VARCHAR(200) NOT NULL,
                    room_type_id VARCHAR(200) NOT NULL,
                    guest_name VARCHAR(200) NOT NULL,
                    guest_email VARCHAR(100),
                    guest_phone VARCHAR(20),
                    check_in_date DATE NOT NULL,
                    check_out_date DATE NOT NULL,
                    nights INTEGER NOT NULL,
                    rooms_booked INTEGER NOT NULL DEFAULT 1,
                    total_price DECIMAL(10, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'MYR',
                    booking_status VARCHAR(20) DEFAULT 'CONFIRMED', -- PENDING, CONFIRMED, CANCELLED, COMPLETED
                    payment_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PAID, REFUNDED
                    special_requests TEXT,
                    booked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES hotels(property_id),
                    FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id)
                )
            """)
            
            # 8. Hotel amenities table
            print("🏊 Creating hotel_amenities table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hotel_amenities (
                    amenity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id VARCHAR(200) NOT NULL,
                    amenity_name VARCHAR(100) NOT NULL,
                    amenity_category VARCHAR(50), -- Dining, Recreation, Business, Transport
                    amenity_description TEXT,
                    is_free BOOLEAN DEFAULT 1,
                    operating_hours VARCHAR(100),
                    FOREIGN KEY (property_id) REFERENCES hotels(property_id)
                )
            """)
            
            # 9. Hotel knowledge base table
            print("🧠 Creating hotel_knowledge table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hotel_knowledge (
                    knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id VARCHAR(200) NOT NULL,
                    category VARCHAR(50) NOT NULL, -- 'dining', 'attractions', 'transport', 'cultural', 'shopping', 'nightlife'
                    subcategory VARCHAR(50), -- 'fine_dining', 'casual', 'street_food', 'museums', 'temples'
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    price_range VARCHAR(100), -- 'RM50-100', 'RM200+ per person', 'FREE'
                    distance VARCHAR(100), -- '5 minutes walk', '15 minutes by car'
                    contact_info VARCHAR(500), -- Phone, website, booking details
                    insider_tips TEXT, -- Hotel staff recommendations and secrets
                    tags VARCHAR(500), -- Searchable tags: 'halal,romantic,city_view,kids_friendly'
                    best_time VARCHAR(200), -- 'sunset', 'weekends', 'avoid peak hours'
                    is_recommended BOOLEAN DEFAULT 1, -- Hotel's top picks
                    last_verified DATE, -- When hotel staff last checked this info
                    created_by VARCHAR(100) DEFAULT 'hotel_staff', -- 'hotel_staff', 'leon_agent', 'concierge'
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES hotels(property_id)
                )
            """)
            
            # Create indexes for performance
            print("⚡ Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_hotels_city ON hotels(city_name)",
                "CREATE INDEX IF NOT EXISTS idx_hotels_country ON hotels(country_name)",
                "CREATE INDEX IF NOT EXISTS idx_room_types_property ON room_types(property_id)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_date ON room_inventory(stay_date)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_property ON room_inventory(property_id)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_room_type ON room_inventory(room_type_id)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON room_inventory(property_id, room_type_id, stay_date)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_dates ON bookings(check_in_date, check_out_date)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_property ON bookings(property_id)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status)",
                "CREATE INDEX IF NOT EXISTS idx_knowledge_property ON hotel_knowledge(property_id)",
                "CREATE INDEX IF NOT EXISTS idx_knowledge_category ON hotel_knowledge(category)",
                "CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON hotel_knowledge(tags)",
                "CREATE INDEX IF NOT EXISTS idx_knowledge_active ON hotel_knowledge(is_active, is_recommended)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            
            print("✅ Database schema created successfully!")
            print("\n📊 Schema Summary:")
            print("   🌏 Countries -> States -> Cities (Geographic hierarchy)")
            print("   🏨 Hotels (Properties in cities)")
            print("   🛏️ Room Types (Different room categories per hotel)")
            print("   📅 Room Inventory (Availability & pricing per date)")
            print("   📝 Bookings (Guest reservations)")
            print("   🏊 Hotel Amenities (Facilities and services)")
            print("   🧠 Hotel Knowledge (Curated local recommendations)")
    
    def initialize_malaysia(self):
        """Initialize Malaysia as the base country with states and major cities."""
        
        print("\n🇲🇾 INITIALIZING MALAYSIA")
        print("=" * 30)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert Malaysia
            print("🇲🇾 Adding Malaysia...")
            cursor.execute("""
                INSERT OR IGNORE INTO countries 
                (country_name, currency_code, phone_prefix, country_code)
                VALUES ('Malaysia', 'MYR', '+60', 'MY')
            """)
            
            # Insert Malaysian states
            print("🏛️ Adding Malaysian states...")
            states = [
                ('Kuala Lumpur', 'Malaysia', 'Asia/Kuala_Lumpur', 'KL'),
                ('Sabah', 'Malaysia', 'Asia/Kuching', 'SBH'),
                ('Penang', 'Malaysia', 'Asia/Kuala_Lumpur', 'PNG'),
                ('Johor', 'Malaysia', 'Asia/Kuala_Lumpur', 'JHR'),
                ('Selangor', 'Malaysia', 'Asia/Kuala_Lumpur', 'SLR'),
                ('Perak', 'Malaysia', 'Asia/Kuala_Lumpur', 'PRK'),
                ('Kedah', 'Malaysia', 'Asia/Kuala_Lumpur', 'KDH'),
                ('Terengganu', 'Malaysia', 'Asia/Kuala_Lumpur', 'TRG'),
                ('Kelantan', 'Malaysia', 'Asia/Kuala_Lumpur', 'KTN'),
                ('Pahang', 'Malaysia', 'Asia/Kuala_Lumpur', 'PHG'),
                ('Melaka', 'Malaysia', 'Asia/Kuala_Lumpur', 'MLK'),
                ('Negeri Sembilan', 'Malaysia', 'Asia/Kuala_Lumpur', 'N9'),
                ('Sarawak', 'Malaysia', 'Asia/Kuching', 'SWK'),
                ('Labuan', 'Malaysia', 'Asia/Kuching', 'LBN'),
                ('Putrajaya', 'Malaysia', 'Asia/Kuala_Lumpur', 'PJY')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO states 
                (state_name, country_name, timezone, state_code)
                VALUES (?, ?, ?, ?)
            """, states)
            
            # Insert major cities
            print("🏙️ Adding major cities...")
            cities = [
                ('Kuala Lumpur', 'Kuala Lumpur', 'Malaysia', 3.1390, 101.6869, 'KUL', 'KL01'),
                ('Kota Kinabalu', 'Sabah', 'Malaysia', 5.9788, 116.0753, 'BKI', 'SBH01'),
                ('Georgetown', 'Penang', 'Malaysia', 5.4141, 100.3288, 'PEN', 'PNG01'),
                ('Johor Bahru', 'Johor', 'Malaysia', 1.4927, 103.7414, 'JHB', 'JHR01'),
                ('Shah Alam', 'Selangor', 'Malaysia', 3.0733, 101.5185, 'KUL', 'SLR01'),
                ('Ipoh', 'Perak', 'Malaysia', 4.5975, 101.0901, 'IPH', 'PRK01'),
                ('Alor Setar', 'Kedah', 'Malaysia', 6.1248, 100.3678, 'AOR', 'KDH01'),
                ('Melaka City', 'Melaka', 'Malaysia', 2.1896, 102.2501, 'MKZ', 'MLK01'),
                ('Sandakan', 'Sabah', 'Malaysia', 5.8402, 118.1179, 'SDK', 'SBH02'),
                ('Butterworth', 'Penang', 'Malaysia', 5.3991, 100.3640, 'PEN', 'PNG02')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO cities 
                (city_name, state_name, country_name, latitude, longitude, airport_code, city_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, cities)
            
            conn.commit()
            
            print("✅ Malaysia geography initialized!")
            print("   🇲🇾 1 Country: Malaysia")
            print("   🏛️ 15 States: KL, Sabah, Penang, etc.")
            print("   🏙️ 10 Major Cities: KL, KK, Georgetown, etc.")
    
    def get_schema_info(self) -> dict:
        """Get information about the database schema."""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = {
                'tables': tables,
                'table_count': len(tables),
                'created_at': datetime.now().isoformat()
            }
            
            # Get row counts
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    schema_info[f'{table}_count'] = count
                except:
                    schema_info[f'{table}_count'] = 0
            
            return schema_info
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)."""
        
        print("⚠️ DROPPING ALL TABLES")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Drop tables in reverse order (respecting foreign key dependencies)
            tables = [
                'hotel_knowledge',
                'hotel_amenities',
                'bookings', 
                'room_inventory',
                'room_types',
                'hotels',
                'cities',
                'states', 
                'countries'
            ]
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"   🗑️ Dropped {table}")
            
            conn.commit()
            print("✅ All tables dropped!")

def create_hotel_database():
    """Main function to create the hotel database schema."""
    
    schema = HotelDatabaseSchema()
    
    # Create all tables
    schema.create_all_tables()
    
    # Initialize Malaysia
    schema.initialize_malaysia()
    
    # Show schema info
    info = schema.get_schema_info()
    print(f"\n📊 FINAL DATABASE INFO:")
    print(f"   📁 Tables created: {info['table_count']}")
    print(f"   🇲🇾 Countries: {info.get('countries_count', 0)}")
    print(f"   🏛️ States: {info.get('states_count', 0)}")
    print(f"   🏙️ Cities: {info.get('cities_count', 0)}")
    print(f"   🏨 Hotels: {info.get('hotels_count', 0)}")
    print(f"   🛏️ Room Types: {info.get('room_types_count', 0)}")
    print(f"   📅 Inventory Records: {info.get('room_inventory_count', 0)}")
    print(f"   📝 Bookings: {info.get('bookings_count', 0)}")
    
    return schema

if __name__ == "__main__":
    print("🏗️ HOTEL DATABASE SCHEMA CREATOR")
    print("=" * 50)
    
    # Ask user if they want to recreate the database
    recreate = input("🤔 Do you want to recreate the database? (y/N): ").lower().strip()
    
    if recreate == 'y':
        schema = HotelDatabaseSchema()
        schema.drop_all_tables()
        print()
    
    create_hotel_database()
    print("\n🎉 Database schema creation complete!")
    print("📝 Next steps:")
    print("   1. Run onboarding.py to add hotels")
    print("   2. Run manage_availability.py to set room inventory")
    print("   3. Test booking functionality") 
#!/usr/bin/env python3
"""
Complete Database Seeding - Non-Interactive
Sets up schema, hotels, and knowledge base in one go
"""

import sqlite3
from datetime import datetime, date, timedelta
import json

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect("ella.db")

def create_schema_non_interactive():
    """Create database schema without interactive prompts."""
    
    print("🏗️ CREATING HOTEL DATABASE SCHEMA")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Disable foreign key constraints during creation
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Drop existing tables in reverse dependency order
        tables_to_drop = [
            'hotel_faq_answers', 'concierge_faq_master', 'hotel_special_deals',
            'hotel_knowledge', 'hotel_amenities', 'bookings', 
            'room_inventory', 'room_types', 'hotels', 
            'cities', 'states', 'countries'
        ]
        
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # 1. Countries table
        print("📍 Creating countries table...")
        cursor.execute("""
            CREATE TABLE countries (
                country_name VARCHAR(100) PRIMARY KEY,
                currency_code VARCHAR(3) NOT NULL,
                phone_prefix VARCHAR(10),
                country_code VARCHAR(2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. States table
        print("🏛️ Creating states table...")
        cursor.execute("""
            CREATE TABLE states (
                state_name VARCHAR(100) PRIMARY KEY,
                country_name VARCHAR(100) NOT NULL,
                timezone VARCHAR(50),
                state_code VARCHAR(10),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (country_name) REFERENCES countries(country_name)
            )
        """)
        
        # 3. Cities table
        print("🏙️ Creating cities table...")
        cursor.execute("""
            CREATE TABLE cities (
                city_name VARCHAR(100) NOT NULL,
                state_name VARCHAR(100) NOT NULL,
                country_name VARCHAR(100) NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                airport_code VARCHAR(3),
                city_code VARCHAR(10),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (city_name, state_name, country_name),
                FOREIGN KEY (state_name) REFERENCES states(state_name),
                FOREIGN KEY (country_name) REFERENCES countries(country_name)
            )
        """)
        
        # 4. Hotels table
        print("🏨 Creating hotels table...")
        cursor.execute("""
            CREATE TABLE hotels (
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
                facilities TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (city_name, state_name, country_name) REFERENCES cities(city_name, state_name, country_name)
            )
        """)
        
        # 5. Room types table
        print("🛏️ Creating room_types table...")
        cursor.execute("""
            CREATE TABLE room_types (
                room_type_id VARCHAR(200) PRIMARY KEY,
                property_id VARCHAR(200) NOT NULL,
                room_name VARCHAR(100) NOT NULL,
                room_description TEXT,
                bed_type VARCHAR(50),
                view_type VARCHAR(50),
                room_size_sqm INTEGER,
                max_occupancy INTEGER NOT NULL,
                base_price_per_night DECIMAL(10, 2) NOT NULL,
                amenities TEXT,
                room_features TEXT,
                total_rooms INTEGER NOT NULL DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # 6. Room inventory table
        print("📅 Creating room_inventory table...")
        cursor.execute("""
            CREATE TABLE room_inventory (
                inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                room_type_id VARCHAR(200) NOT NULL,
                stay_date DATE NOT NULL,
                available_rooms INTEGER NOT NULL DEFAULT 0,
                base_price DECIMAL(10, 2) NOT NULL,
                current_price DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'MYR',
                price_last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                demand_level VARCHAR(20) DEFAULT 'NORMAL',
                min_stay_nights INTEGER DEFAULT 1,
                max_stay_nights INTEGER DEFAULT 30,
                booking_rules TEXT,
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
            CREATE TABLE bookings (
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
                booking_status VARCHAR(20) DEFAULT 'CONFIRMED',
                payment_status VARCHAR(20) DEFAULT 'PENDING',
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
            CREATE TABLE hotel_amenities (
                amenity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                amenity_name VARCHAR(100) NOT NULL,
                amenity_category VARCHAR(50),
                amenity_description TEXT,
                is_free BOOLEAN DEFAULT 1,
                operating_hours VARCHAR(100),
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # 9. Hotel knowledge table
        print("🧠 Creating hotel_knowledge table...")
        cursor.execute("""
            CREATE TABLE hotel_knowledge (
                knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(50),
                title VARCHAR(200) NOT NULL,
                description TEXT,
                price_range VARCHAR(100),
                distance VARCHAR(100),
                contact_info VARCHAR(200),
                insider_tips TEXT,
                tags VARCHAR(500),
                best_time VARCHAR(100),
                is_recommended BOOLEAN DEFAULT 0,
                last_verified DATE,
                created_by VARCHAR(100) DEFAULT 'system',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # 10. Hotel special deals table (EXCLUSIVE OFFERS)
        print("💎 Creating hotel_special_deals table...")
        cursor.execute("""
            CREATE TABLE hotel_special_deals (
                deal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                deal_type VARCHAR(50) NOT NULL,
                deal_title VARCHAR(200) NOT NULL,
                deal_description TEXT,
                regular_price DECIMAL(10, 2),
                special_price DECIMAL(10, 2),
                savings_amount DECIMAL(10, 2),
                savings_percentage DECIMAL(5, 2),
                deal_category VARCHAR(50),
                partner_name VARCHAR(200),
                booking_method VARCHAR(100),
                restrictions TEXT,
                valid_from DATE,
                valid_until DATE,
                is_exclusive BOOLEAN DEFAULT 1,
                commission_rate DECIMAL(5, 2),
                deal_status VARCHAR(20) DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # Create indexes
        print("⚡ Creating indexes...")
        cursor.execute("CREATE INDEX idx_hotels_city ON hotels(city_name, state_name, country_name)")
        cursor.execute("CREATE INDEX idx_room_inventory_date ON room_inventory(stay_date)")
        cursor.execute("CREATE INDEX idx_room_inventory_property ON room_inventory(property_id)")
        cursor.execute("CREATE INDEX idx_hotel_knowledge_property ON hotel_knowledge(property_id)")
        cursor.execute("CREATE INDEX idx_hotel_knowledge_category ON hotel_knowledge(category, subcategory)")
        cursor.execute("CREATE INDEX idx_hotel_knowledge_tags ON hotel_knowledge(tags)")
        cursor.execute("CREATE INDEX idx_special_deals_property ON hotel_special_deals(property_id)")
        cursor.execute("CREATE INDEX idx_special_deals_category ON hotel_special_deals(deal_category)")
        cursor.execute("CREATE INDEX idx_special_deals_status ON hotel_special_deals(deal_status)")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        print("✅ Database schema created successfully!")

def seed_geography():
    """Seed geography data (countries, states, cities)."""
    
    print("\n🇲🇾 SEEDING GEOGRAPHY DATA")
    print("=" * 30)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Add Malaysia
        cursor.execute("""
            INSERT INTO countries (country_name, currency_code, phone_prefix, country_code)
            VALUES ('Malaysia', 'MYR', '+60', 'MY')
        """)
        
        # Add Malaysian states
        states = [
            ('Kuala Lumpur', 'Malaysia', 'Asia/Kuala_Lumpur', 'KL'),
            ('Selangor', 'Malaysia', 'Asia/Kuala_Lumpur', 'SGR'),
            ('Sabah', 'Malaysia', 'Asia/Kuching', 'SBH'),
            ('Penang', 'Malaysia', 'Asia/Kuala_Lumpur', 'PNG'),
            ('Johor', 'Malaysia', 'Asia/Kuala_Lumpur', 'JHR')
        ]
        
        cursor.executemany("""
            INSERT INTO states (state_name, country_name, timezone, state_code)
            VALUES (?, ?, ?, ?)
        """, states)
        
        # Add major cities
        cities = [
            ('Kuala Lumpur', 'Kuala Lumpur', 'Malaysia', 3.1390, 101.6869, 'KUL', 'KL'),
            ('Kota Kinabalu', 'Sabah', 'Malaysia', 5.9804, 116.0735, 'BKI', 'KK'),
            ('Georgetown', 'Penang', 'Malaysia', 5.4164, 100.3327, 'PEN', 'PG'),
            ('Sepang', 'Selangor', 'Malaysia', 2.7297, 101.6997, 'KUL', 'SPG'),
            ('Johor Bahru', 'Johor', 'Malaysia', 1.4927, 103.7414, 'JHB', 'JB')
        ]
        
        cursor.executemany("""
            INSERT INTO cities (city_name, state_name, country_name, latitude, longitude, airport_code, city_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, cities)
        
        conn.commit()
        print("✅ Geography data seeded!")

def seed_hotels():
    """Seed hotel data."""
    
    print("\n🏨 SEEDING HOTEL DATA")
    print("=" * 25)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        hotels = [
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'hotel_name': 'Grand Hyatt Kuala Lumpur',
                'hotel_brand': 'Hyatt',
                'star_rating': 5,
                'city_name': 'Kuala Lumpur',
                'state_name': 'Kuala Lumpur',
                'country_name': 'Malaysia',
                'address': '12 Jalan Pinang, Kuala Lumpur City Centre',
                'postcode': '50450',
                'phone': '+603-2182-1234',
                'email': 'kuala.lumpur@hyatt.com',
                'latitude': 3.1478,
                'longitude': 101.7013,
                'distance_to_airport_km': 55.0,
                'description': 'Luxury hotel in the heart of KLCC with direct access to Pavilion shopping mall',
                'facilities': json.dumps(['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Concierge'])
            },
            {
                'property_id': 'marina_court_resort_kk',
                'hotel_name': 'Marina Court Resort',
                'hotel_brand': 'Independent',
                'star_rating': 4,
                'city_name': 'Kota Kinabalu',
                'state_name': 'Sabah',
                'country_name': 'Malaysia',
                'address': 'Jalan Tun Fuad Stephens, Kota Kinabalu',
                'postcode': '88000',
                'phone': '+6088-237-999',
                'email': 'info@marinacourt.com',
                'latitude': 5.9749,
                'longitude': 116.0724,
                'distance_to_airport_km': 8.0,
                'description': 'Waterfront resort with sea views and easy access to island hopping',
                'facilities': json.dumps(['WiFi', 'Sea View', 'Restaurant', 'Tour Desk'])
            },
            {
                'property_id': 'mandarin_oriental_kl',
                'hotel_name': 'Mandarin Oriental Kuala Lumpur',
                'hotel_brand': 'Mandarin Oriental',
                'star_rating': 5,
                'city_name': 'Kuala Lumpur',
                'state_name': 'Kuala Lumpur',
                'country_name': 'Malaysia',
                'address': 'Kuala Lumpur City Centre',
                'postcode': '50088',
                'phone': '+603-2380-8888',
                'email': 'mokul-reservations@mohg.com',
                'latitude': 3.1516,
                'longitude': 101.7125,
                'distance_to_airport_km': 60.0,
                'description': 'Iconic luxury hotel with twin towers views and world-class service',
                'facilities': json.dumps(['WiFi', 'Pool', 'Concierge', 'Spa', 'Fine Dining'])
            },
            {
                'property_id': 'sam_hotel_kl',
                'hotel_name': 'Sam Hotel Kuala Lumpur',
                'hotel_brand': 'Independent',
                'star_rating': 3,
                'city_name': 'Kuala Lumpur',
                'state_name': 'Kuala Lumpur',
                'country_name': 'Malaysia',
                'address': 'Jalan Masjid India, Kuala Lumpur',
                'postcode': '50100',
                'phone': '+603-2692-7768',
                'email': 'info@samhotel.com.my',
                'latitude': 3.1478,
                'longitude': 101.6953,
                'distance_to_airport_km': 50.0,
                'description': 'Budget-friendly hotel in heritage area with easy access to Little India',
                'facilities': json.dumps(['WiFi', 'Restaurant', 'Heritage Location'])
            }
        ]
        
        for hotel in hotels:
            cursor.execute("""
                INSERT INTO hotels (
                    property_id, hotel_name, hotel_brand, star_rating,
                    city_name, state_name, country_name, address, postcode,
                    phone, email, latitude, longitude, distance_to_airport_km,
                    description, facilities
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hotel['property_id'], hotel['hotel_name'], hotel['hotel_brand'], hotel['star_rating'],
                hotel['city_name'], hotel['state_name'], hotel['country_name'], hotel['address'], hotel['postcode'],
                hotel['phone'], hotel['email'], hotel['latitude'], hotel['longitude'], hotel['distance_to_airport_km'],
                hotel['description'], hotel['facilities']
            ))
            print(f"   ✅ {hotel['hotel_name']}")
        
        conn.commit()
        print("✅ Hotels seeded!")

def seed_room_types():
    """Seed room types for hotels."""
    
    print("\n🛏️ SEEDING ROOM TYPES")
    print("=" * 25)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        room_types = [
            # Grand Hyatt KL
            {
                'room_type_id': 'grand_hyatt_kl_deluxe_king',
                'property_id': 'grand_hyatt_kuala_lumpur',
                'room_name': 'Deluxe King Room',
                'room_description': 'Spacious room with king bed and city views',
                'bed_type': 'King',
                'view_type': 'City',
                'room_size_sqm': 40,
                'max_occupancy': 2,
                'base_price_per_night': 450.00,
                'amenities': json.dumps(['WiFi', 'Mini Bar', 'Safe', 'Air Conditioning']),
                'room_features': json.dumps(['City View', 'Work Desk', 'Marble Bathroom']),
                'total_rooms': 50
            },
            {
                'room_type_id': 'grand_hyatt_kl_twin_room',
                'property_id': 'grand_hyatt_kuala_lumpur',
                'room_name': 'Twin Bed Room',
                'room_description': 'Comfortable room with two single beds',
                'bed_type': 'Twin',
                'view_type': 'City',
                'room_size_sqm': 35,
                'max_occupancy': 2,
                'base_price_per_night': 420.00,
                'amenities': json.dumps(['WiFi', 'Mini Bar', 'Safe', 'Air Conditioning']),
                'room_features': json.dumps(['City View', 'Work Desk']),
                'total_rooms': 30
            },
            # Sam Hotel KL
            {
                'room_type_id': 'sam_hotel_kl_standard_double',
                'property_id': 'sam_hotel_kl',
                'room_name': 'Standard Double Room',
                'room_description': 'Cozy room with double bed in heritage location',
                'bed_type': 'Double',
                'view_type': 'Street',
                'room_size_sqm': 25,
                'max_occupancy': 2,
                'base_price_per_night': 120.00,
                'amenities': json.dumps(['WiFi', 'Air Conditioning', 'TV']),
                'room_features': json.dumps(['Heritage Building', 'Local Area']),
                'total_rooms': 40
            }
        ]
        
        for room in room_types:
            cursor.execute("""
                INSERT INTO room_types (
                    room_type_id, property_id, room_name, room_description,
                    bed_type, view_type, room_size_sqm, max_occupancy,
                    base_price_per_night, amenities, room_features, total_rooms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                room['room_type_id'], room['property_id'], room['room_name'], room['room_description'],
                room['bed_type'], room['view_type'], room['room_size_sqm'], room['max_occupancy'],
                room['base_price_per_night'], room['amenities'], room['room_features'], room['total_rooms']
            ))
            print(f"   ✅ {room['room_name']} - {room['property_id']}")
        
        conn.commit()
        print("✅ Room types seeded!")

def seed_room_inventory():
    """Seed room inventory for the next 30 days."""
    
    print("\n📅 SEEDING ROOM INVENTORY")
    print("=" * 30)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all room types
        cursor.execute("SELECT room_type_id, property_id, base_price_per_night, total_rooms FROM room_types")
        room_types = cursor.fetchall()
        
        # Create inventory for next 30 days
        today = date.today()
        for i in range(30):
            stay_date = today + timedelta(days=i)
            
            for room_type_id, property_id, base_price, total_rooms in room_types:
                # Vary availability and pricing slightly
                available_rooms = max(1, total_rooms - (i % 5))  # Some rooms always booked
                current_price = base_price * (1 + (i % 7) * 0.1)  # Price varies by day
                
                cursor.execute("""
                    INSERT INTO room_inventory (
                        property_id, room_type_id, stay_date, available_rooms,
                        base_price, current_price, currency
                    ) VALUES (?, ?, ?, ?, ?, ?, 'MYR')
                """, (property_id, room_type_id, stay_date, available_rooms, base_price, current_price))
        
        conn.commit()
        print(f"✅ Room inventory created for next 30 days!")

def create_faq_master():
    """Create master FAQ list that all hotels will answer."""
    
    print("\n❓ CREATING MASTER FAQ SYSTEM")
    print("=" * 35)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create master FAQ table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concierge_faq_master (
                faq_id VARCHAR(20) PRIMARY KEY,
                category VARCHAR(50) NOT NULL,
                question TEXT NOT NULL,
                question_variations TEXT,
                priority_level INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Master FAQ questions that every hotel should answer
        master_faqs = [
            # DINING FAQs
            ('FAQ_D001', 'dining', 'Where is the best restaurant nearby?', 'restaurant,makan,food,where to eat', 1),
            ('FAQ_D002', 'dining', 'What is open for late night food?', 'late night,24 hours,supper,midnight', 2),
            ('FAQ_D003', 'dining', 'Where can I get halal food?', 'halal,muslim,islamic food', 1),
            ('FAQ_D004', 'dining', 'What is the local specialty dish?', 'local food,specialty,signature dish,must try', 2),
            ('FAQ_D005', 'dining', 'Where can I get cheap food?', 'budget,cheap,affordable,street food', 2),
            
            # ATTRACTIONS FAQs  
            ('FAQ_A001', 'attractions', 'What should we visit today?', 'attractions,sightseeing,visit,see', 1),
            ('FAQ_A002', 'attractions', 'What is the main landmark here?', 'landmark,famous,iconic,must see', 1),
            ('FAQ_A003', 'attractions', 'What can kids do here?', 'kids,children,family,playground', 2),
            ('FAQ_A004', 'attractions', 'What is free to visit?', 'free,no cost,percuma', 2),
            
            # TRANSPORT FAQs
            ('FAQ_T001', 'transport', 'How do I get to the airport?', 'airport,flight,terminal', 1),
            ('FAQ_T002', 'transport', 'How do I get around the city?', 'transport,taxi,grab,bus,lrt', 1),
            ('FAQ_T003', 'transport', 'Where can I rent a car?', 'car rental,drive,vehicle', 3),
            
            # SHOPPING FAQs
            ('FAQ_S001', 'shopping', 'Where is the nearest mall?', 'shopping,mall,shop,buy', 2),
            ('FAQ_S002', 'shopping', 'Where can I buy souvenirs?', 'souvenirs,gifts,local products', 2),
            
            # PRACTICAL FAQs
            ('FAQ_P001', 'practical', 'Where is the nearest hospital?', 'hospital,emergency,clinic,doctor', 1),
            ('FAQ_P002', 'practical', 'Where can I exchange money?', 'money changer,exchange,currency', 2),
            ('FAQ_P003', 'practical', 'Where is the nearest ATM?', 'atm,cash,bank,money', 2),
            ('FAQ_P004', 'practical', 'Where can I buy a local SIM card?', 'sim card,phone,mobile,internet', 2)
        ]
        
        # Insert master FAQs
        cursor.executemany("""
            INSERT OR REPLACE INTO concierge_faq_master 
            (faq_id, category, question, question_variations, priority_level)
            VALUES (?, ?, ?, ?, ?)
        """, master_faqs)
        
        conn.commit()
        print(f"✅ Master FAQ created! ({len(master_faqs)} standard questions)")

def seed_hotel_faq_answers():
    """Convert existing hotel knowledge to FAQ-based answers."""
    
    print("\n💬 SEEDING HOTEL FAQ ANSWERS")
    print("=" * 35)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Drop existing hotel_knowledge if exists and recreate as FAQ answers
        cursor.execute("DROP TABLE IF EXISTS hotel_faq_answers")
        
        cursor.execute("""
            CREATE TABLE hotel_faq_answers (
                answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                faq_id VARCHAR(20) NOT NULL,
                answer_title VARCHAR(200),
                answer_content TEXT NOT NULL,
                practical_details VARCHAR(500),
                insider_tip TEXT,
                contact_info VARCHAR(200),
                price_range VARCHAR(100),
                distance_info VARCHAR(100),
                is_special_deal BOOLEAN DEFAULT 0,
                deal_savings_amount VARCHAR(200),
                deal_description TEXT,
                priority_score INTEGER DEFAULT 5,
                last_updated DATE DEFAULT CURRENT_DATE,
                verified_by VARCHAR(100) DEFAULT 'hotel_staff',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # Create index for FAQ queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hotel_faq_property ON hotel_faq_answers(property_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hotel_faq_id ON hotel_faq_answers(faq_id)
        """)
        
        # Hotel FAQ answers for Grand Hyatt KL
        grand_hyatt_answers = [
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'faq_id': 'FAQ_D001',
                'answer_title': 'Atmosphere 360° - KL Tower (SPECIAL DEAL)',
                'answer_content': 'Halal fine dining with 360° rotating city views. Hotel guests get exclusive 20% discount!',
                'practical_details': 'RM180-250 per person (20% off for hotel guests)',
                'insider_tip': 'Request window table at sunset (7:30pm). Show room key for discount.',
                'contact_info': 'Tel: +603-2020-5055 | Book through hotel concierge',
                'distance_info': '15 minutes by hotel car (RM25)',
                'is_special_deal': True,
                'deal_savings_amount': 'Save 20% off total bill',
                'deal_description': 'Exclusive discount for hotel guests only',
                'priority_score': 10
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'faq_id': 'FAQ_D002',
                'answer_title': 'Jalan Alor Night Market',
                'answer_content': 'Famous street food paradise with authentic local flavors. Must-try KL experience.',
                'practical_details': 'RM40-60 for 2 people',
                'insider_tip': 'Try Char Kway Teow at Wong Ah Wah. Avoid peak hours (8-9pm) for shorter queues.',
                'contact_info': 'Open 6pm-2am daily | Multiple stalls',
                'distance_info': '20 minutes walk or 10 minutes Grab (RM12-15)',
                'is_special_deal': False,
                'priority_score': 5
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'faq_id': 'FAQ_A001',
                'answer_title': 'Petronas Twin Towers & KLCC Park (HOTEL SPECIAL)',
                'answer_content': 'Iconic twin towers with skybridge. Hotel guests get 30% discount on skybridge tickets!',
                'practical_details': 'FREE (park) | RM60 skybridge (30% off for hotel guests)',
                'insider_tip': 'Book through hotel concierge to get discount tickets. Fountain show is free and family-friendly.',
                'contact_info': 'Book at hotel concierge | Fountain show: 8:30pm & 9:30pm',
                'distance_info': '5 minutes walk via skybridge',
                'is_special_deal': True,
                'deal_savings_amount': 'Save RM25 per ticket (30% off)',
                'deal_description': 'Exclusive hotel guest discount on skybridge tickets',
                'priority_score': 10
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'faq_id': 'FAQ_S001',
                'answer_title': 'Pavilion Kuala Lumpur (VIP PRIVILEGES)',
                'answer_content': 'Premier shopping mall. Hotel guests get VIP privileges including personal shopping assistant!',
                'practical_details': 'VIP services FREE for hotel guests (normally RM150)',
                'insider_tip': 'Show room key at Customer Service for VIP card. Includes 10% extra discount at luxury brands.',
                'contact_info': '10am-10pm daily | VIP lounge Level 6',
                'distance_info': 'Direct connection via skybridge',
                'is_special_deal': True,
                'deal_savings_amount': 'FREE VIP services (save RM150)',
                'deal_description': 'Exclusive VIP shopping privileges for hotel guests',
                'priority_score': 10
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'faq_id': 'FAQ_T001',
                'answer_title': 'Hotel Premium Airport Transfer',
                'answer_content': 'Luxury airport transfer with English-speaking driver and complimentary city tour.',
                'practical_details': 'RM90 to KLIA (includes 30-min city highlights tour)',
                'insider_tip': 'Book 24hrs ahead. Driver provides bottled water and local tips.',
                'contact_info': 'Book at concierge desk | 24/7 availability',
                'distance_info': '45-60 minutes depending on traffic',
                'is_special_deal': False,
                'priority_score': 6
            }
        ]
        
        # Hotel FAQ answers for Sam Hotel KL
        sam_hotel_answers = [
            {
                'property_id': 'sam_hotel_kl',
                'faq_id': 'FAQ_D001',
                'answer_title': 'Restoran Yusoof Dan Zakhir (HOTEL GUEST SPECIAL)',
                'answer_content': 'Famous nasi kandar since 1917. Hotel guests get 15% discount on total bill!',
                'practical_details': 'RM15-25 per person (15% off for hotel guests)',
                'insider_tip': 'Show hotel room key for discount. Try fish curry and mixed vegetables.',
                'contact_info': 'Open 6am-11pm daily | No reservations needed',
                'distance_info': '2 minutes walk from hotel',
                'is_special_deal': True,
                'deal_savings_amount': 'Save 15% off total bill',
                'deal_description': 'Exclusive discount arrangement with hotel',
                'priority_score': 10
            },
            {
                'property_id': 'sam_hotel_kl',
                'faq_id': 'FAQ_A001',
                'answer_title': 'Merdeka Square',
                'answer_content': 'Historic square where Malaysian independence was declared. Colonial architecture and museums nearby.',
                'practical_details': 'FREE | Museum entries RM5-10',
                'insider_tip': 'Visit early morning for photos without crowds. Sultan Abdul Samad Building is stunning at sunset.',
                'contact_info': 'Open 24/7 | Museums 9am-6pm',
                'distance_info': '10 minutes walk',
                'is_special_deal': False,
                'priority_score': 5
            },
            {
                'property_id': 'sam_hotel_kl',
                'faq_id': 'FAQ_S001',
                'answer_title': 'Petaling Street Market (Chinatown)',
                'answer_content': 'Bustling street market with bargain shopping, street food, and local atmosphere.',
                'practical_details': 'RM10-50 for souvenirs',
                'insider_tip': 'Bargain expected - start at 30% of asking price. Try fresh fruit juices and dim sum.',
                'contact_info': 'Open 10am-10pm daily | Peak hours 6-9pm',
                'distance_info': '15 minutes walk',
                'is_special_deal': False,
                'priority_score': 5
            }
        ]
        
        # Insert all FAQ answers
        all_answers = grand_hyatt_answers + sam_hotel_answers
        
        for answer in all_answers:
            cursor.execute("""
                INSERT INTO hotel_faq_answers (
                    property_id, faq_id, answer_title, answer_content,
                    practical_details, insider_tip, contact_info, distance_info,
                    is_special_deal, deal_savings_amount, deal_description, priority_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                answer['property_id'], answer['faq_id'], answer['answer_title'], 
                answer['answer_content'], answer['practical_details'], 
                answer['insider_tip'], answer['contact_info'], answer['distance_info'],
                answer.get('is_special_deal', False), answer.get('deal_savings_amount', None), 
                answer.get('deal_description', None), answer.get('priority_score', 5)
            ))
            print(f"   ✅ {answer['answer_title']} - {answer['faq_id']}")
        
        conn.commit()
        print(f"✅ Hotel FAQ answers seeded! ({len(all_answers)} answers)")

def seed_hotel_special_deals():
    """Seed exclusive hotel deals and special offers."""
    
    print("\n💎 SEEDING HOTEL SPECIAL DEALS")
    print("=" * 35)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Exclusive deals for Grand Hyatt KL
        grand_hyatt_deals = [
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'deal_type': 'ATTRACTION_TICKET',
                'deal_title': 'Petronas Twin Towers Skybridge - Hotel Guest Discount',
                'deal_description': 'Exclusive 30% discount on Petronas Twin Towers Skybridge tickets for hotel guests. Skip the online queue with hotel pre-booking service.',
                'regular_price': 85.00,
                'special_price': 59.50,
                'savings_amount': 25.50,
                'savings_percentage': 30.0,
                'deal_category': 'ATTRACTION',
                'partner_name': 'Petronas Twin Towers',
                'booking_method': 'Book at hotel concierge desk with room key',
                'restrictions': 'Valid for hotel guests only. Must show room key card.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 15.0
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'deal_type': 'SPA_PACKAGE',
                'deal_title': 'Hyatt Spa + KL Tower Atmosphere 360° Dinner Package',
                'deal_description': 'Exclusive package: 90-minute spa treatment + romantic dinner at Atmosphere 360° with guaranteed window table and complimentary champagne.',
                'regular_price': 580.00,
                'special_price': 450.00,
                'savings_amount': 130.00,
                'savings_percentage': 22.4,
                'deal_category': 'DINING_SPA',
                'partner_name': 'Hyatt Spa + Atmosphere 360°',
                'booking_method': 'Book through hotel concierge - available to hotel guests only',
                'restrictions': 'Minimum 24-hour advance booking. Subject to availability.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 20.0
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'deal_type': 'SHOPPING_PRIVILEGE',
                'deal_title': 'Pavilion KL VIP Shopping Experience',
                'deal_description': 'Exclusive hotel guest privileges: Personal shopping assistant, VIP lounge access, additional 10% discount at luxury brands, and complimentary gift wrapping.',
                'regular_price': 150.00,
                'special_price': 0.00,
                'savings_amount': 150.00,
                'savings_percentage': 100.0,
                'deal_category': 'SHOPPING',
                'partner_name': 'Pavilion Kuala Lumpur',
                'booking_method': 'Request VIP card at hotel concierge with room key',
                'restrictions': 'Valid for hotel guests only. Minimum RM500 shopping spend.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 5.0
            },
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'deal_type': 'TRANSPORT_DEAL',
                'deal_title': 'Premium Airport Transfer + City Tour Package',
                'deal_description': 'Exclusive hotel guest package: Luxury airport pickup + 3-hour KL city highlights tour with English-speaking guide, including photo stops at major landmarks.',
                'regular_price': 180.00,
                'special_price': 120.00,
                'savings_amount': 60.00,
                'savings_percentage': 33.3,
                'deal_category': 'TRANSPORT',
                'partner_name': 'Hyatt Premium Transport',
                'booking_method': 'Book at hotel concierge desk - 24hr advance notice required',
                'restrictions': 'Available for hotel guests only. Subject to availability.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 25.0
            }
        ]
        
        # Budget-friendly deals for Sam Hotel KL
        sam_hotel_deals = [
            {
                'property_id': 'sam_hotel_kl',
                'deal_type': 'CULTURAL_TOUR',
                'deal_title': 'Heritage Quarter Walking Tour + Traditional Lunch',
                'deal_description': 'Exclusive 3-hour guided heritage walk through Little India, Chinatown & Merdeka Square with traditional Malaysian lunch at century-old restaurant.',
                'regular_price': 75.00,
                'special_price': 45.00,
                'savings_amount': 30.00,
                'savings_percentage': 40.0,
                'deal_category': 'CULTURAL',
                'partner_name': 'Sam Heritage Tours',
                'booking_method': 'Book at hotel reception - available to hotel guests only',
                'restrictions': 'Minimum 2 participants. Tours run daily except Mondays.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 30.0
            },
            {
                'property_id': 'sam_hotel_kl',
                'deal_type': 'FOOD_EXPERIENCE',
                'deal_title': 'Street Food Discovery Tour + Cooking Class',
                'deal_description': 'Exclusive hotel guest experience: Guided street food tour at Jalan Alor + hands-on cooking class for 3 signature Malaysian dishes with take-home recipes.',
                'regular_price': 95.00,
                'special_price': 65.00,
                'savings_amount': 30.00,
                'savings_percentage': 31.6,
                'deal_category': 'CULINARY',
                'partner_name': 'Sam Culinary Adventures',
                'booking_method': 'Book through hotel reception - hotel guests only',
                'restrictions': 'Evening tours only. Minimum 24-hour advance booking.',
                'valid_from': date.today(),
                'valid_until': date(2025, 12, 31),
                'commission_rate': 35.0
            }
        ]
        
        # Insert all special deals
        all_deals = grand_hyatt_deals + sam_hotel_deals
        
        for deal in all_deals:
            cursor.execute("""
                INSERT INTO hotel_special_deals (
                    property_id, deal_type, deal_title, deal_description,
                    regular_price, special_price, savings_amount, savings_percentage,
                    deal_category, partner_name, booking_method, restrictions,
                    valid_from, valid_until, commission_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal['property_id'], deal['deal_type'], deal['deal_title'], deal['deal_description'],
                deal['regular_price'], deal['special_price'], deal['savings_amount'], deal['savings_percentage'],
                deal['deal_category'], deal['partner_name'], deal['booking_method'], deal['restrictions'],
                deal['valid_from'], deal['valid_until'], deal['commission_rate']
            ))
            print(f"   💎 {deal['deal_title']} - Save RM{deal['savings_amount']}")
        
        conn.commit()
        print(f"✅ Hotel special deals seeded! ({len(all_deals)} exclusive offers)")

def main():
    """Run complete database seeding."""
    
    print("🌱 COMPLETE DATABASE SEEDING")
    print("=" * 50)
    print("This will recreate the entire database with fresh data.")
    print("=" * 50)
    
    try:
        # Step 1: Create schema
        create_schema_non_interactive()
        
        # Step 2: Seed geography
        seed_geography()
        
        # Step 3: Seed hotels
        seed_hotels()
        
        # Step 4: Seed room types
        seed_room_types()
        
        # Step 5: Seed room inventory
        seed_room_inventory()
        
        # Step 6: Create master FAQ system
        create_faq_master()
        
        # Step 7: Seed hotel FAQ answers
        seed_hotel_faq_answers()
        
        # Step 8: Seed hotel special deals
        seed_hotel_special_deals()
        
        print("\n" + "=" * 50)
        print("🎉 DATABASE SEEDING COMPLETE!")
        print("=" * 50)
        print("✅ Schema created")
        print("✅ Geography seeded (Malaysia)")
        print("✅ Hotels seeded (4 properties)")
        print("✅ Room types seeded")
        print("✅ Room inventory seeded (30 days)")
        print("✅ Master FAQ system created")
        print("✅ Hotel FAQ answers seeded")
        print("✅ Hotel special deals seeded")
        print("\n🚀 Ready for FAQ-based concierge intelligence!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 
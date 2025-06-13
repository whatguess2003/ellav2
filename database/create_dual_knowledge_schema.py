#!/usr/bin/env python3
"""
DUAL KNOWLEDGE BANK DATABASE SCHEMA
Supports both structured information (fast lookup) and raw information (semantic search)

ARCHITECTURE:
1. STRUCTURED KNOWLEDGE: hotels table with verified data fields (Tier 1-2)
2. RAW KNOWLEDGE: hotel_knowledge_bank table with staff-written text (Tier 3+)
"""

import sqlite3
from datetime import date
import os

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(__file__), 'ella.db')
    return sqlite3.connect(db_path)

def create_dual_knowledge_schema():
    """Create comprehensive schema for both structured and raw knowledge."""
    
    print("🏗️ CREATING DUAL KNOWLEDGE BANK SCHEMA")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if base tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hotels'")
        hotels_exists = cursor.fetchone()
        
        print("📊 STRUCTURED KNOWLEDGE LAYER")
        print("-" * 30)
        
        if not hotels_exists:
            print("Creating hotels table for structured data...")
            # Create comprehensive hotels table for structured data (Tier 1-2)
            cursor.execute("""
                CREATE TABLE hotels (
                    property_id VARCHAR(200) PRIMARY KEY,
                    hotel_name VARCHAR(200) NOT NULL,
                    hotel_brand VARCHAR(100),
                    star_rating INTEGER CHECK(star_rating >= 1 AND star_rating <= 5),
                    city_name VARCHAR(100) NOT NULL,
                    state_name VARCHAR(100),
                    country_name VARCHAR(100),
                    address TEXT,
                    phone VARCHAR(20),
                    email VARCHAR(100),
                    website VARCHAR(200),
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    
                    -- STRUCTURED INSTANT DATA (Tier 1)
                    check_in_time TIME DEFAULT '15:00:00',
                    check_out_time TIME DEFAULT '12:00:00',
                    wifi_password VARCHAR(50),
                    wifi_details TEXT,
                    parking_fee DECIMAL(8, 2),
                    pet_policy TEXT,
                    smoking_policy TEXT,
                    cancellation_policy TEXT,
                    currency_used VARCHAR(3) DEFAULT 'MYR',
                    
                    -- STRUCTURED FACILITY DATA (Tier 2)
                    pool_hours VARCHAR(50),
                    gym_hours VARCHAR(50),
                    spa_hours VARCHAR(50),
                    concierge_hours VARCHAR(50),
                    room_service_hours VARCHAR(50),
                    business_center_hours VARCHAR(50),
                    airport_shuttle_fee DECIMAL(8, 2),
                    airport_shuttle_schedule TEXT,
                    facilities TEXT,
                    
                    -- METADATA
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Hotels table created for structured data")
        else:
            print("✅ Hotels table already exists")
        
        print("\n📝 RAW KNOWLEDGE LAYER")
        print("-" * 30)
        
        # Drop existing raw knowledge table if exists (for clean slate)
        cursor.execute("DROP TABLE IF EXISTS hotel_knowledge_bank")
        
        # Create raw text knowledge bank (Tier 3+)
        cursor.execute("""
            CREATE TABLE hotel_knowledge_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id VARCHAR(200) NOT NULL,
                knowledge_text TEXT NOT NULL,
                staff_author VARCHAR(100) DEFAULT 'hotel_staff',
                knowledge_type VARCHAR(50) DEFAULT 'general',
                created_date DATE DEFAULT CURRENT_DATE,
                last_updated DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT 1,
                version INTEGER DEFAULT 1,
                review_status VARCHAR(20) DEFAULT 'approved',
                FOREIGN KEY (property_id) REFERENCES hotels(property_id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX idx_hotel_knowledge_property ON hotel_knowledge_bank(property_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_hotel_knowledge_active ON hotel_knowledge_bank(is_active)
        """)
        cursor.execute("""
            CREATE INDEX idx_hotel_knowledge_type ON hotel_knowledge_bank(knowledge_type)
        """)
        
        print("✅ Raw knowledge bank table created")
        
        conn.commit()
        print("\n🌟 DUAL KNOWLEDGE ARCHITECTURE READY!")
        return True

def seed_structured_data():
    """Seed structured hotel data for fast lookup (Tier 1-2)."""
    
    print("\n📊 SEEDING STRUCTURED KNOWLEDGE")
    print("=" * 40)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM hotels")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("✅ Structured data already exists")
            return True
        
        structured_hotels = [
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'hotel_name': 'Grand Hyatt Kuala Lumpur',
                'hotel_brand': 'Hyatt',
                'star_rating': 5,
                'city_name': 'Kuala Lumpur',
                'state_name': 'Federal Territory of Kuala Lumpur',
                'country_name': 'Malaysia',
                'address': '12 Jalan Pinang, Kuala Lumpur City Centre, 50450 Kuala Lumpur',
                'phone': '+603-2182-1234',
                'email': 'kualalumpur.grand@hyatt.com',
                'website': 'https://www.hyatt.com/grand-hyatt/kuala-lumpur',
                'latitude': 3.1516,
                'longitude': 101.7123,
                
                # Structured instant data
                'check_in_time': '15:00:00',
                'check_out_time': '12:00:00',
                'wifi_password': 'GrandHyatt2024',
                'wifi_details': 'Complimentary high-speed WiFi throughout the property',
                'parking_fee': 25.00,
                'pet_policy': 'Small pets under 10kg allowed, RM50 per night',
                'smoking_policy': 'Non-smoking property. Designated smoking areas available.',
                'cancellation_policy': 'Free cancellation until 6 PM day before arrival',
                'currency_used': 'MYR',
                
                # Structured facility data
                'pool_hours': '6:00 AM - 10:00 PM',
                'gym_hours': '24 hours',
                'spa_hours': '10:00 AM - 10:00 PM',
                'concierge_hours': '24 hours',
                'room_service_hours': '24 hours',
                'business_center_hours': '24 hours',
                'airport_shuttle_fee': 90.00,
                'airport_shuttle_schedule': 'Every 2 hours, 6 AM - 10 PM',
                'facilities': 'Pool, Spa, Gym, Restaurant, Bar, Business Center, Concierge'
            },
            {
                'property_id': 'marina_court_resort_kota_kinabalu',
                'hotel_name': 'Marina Court Resort Condominium',
                'hotel_brand': 'Independent',
                'star_rating': 4,
                'city_name': 'Kota Kinabalu',
                'state_name': 'Sabah',
                'country_name': 'Malaysia',
                'address': 'Jalan Tun Fuad Stephens, 88000 Kota Kinabalu, Sabah',
                'phone': '+6088-231-888',
                'email': 'reservations@marinacourt.com.my',
                'website': 'https://www.marinacourt.com.my',
                'latitude': 5.9749,
                'longitude': 116.0724,
                
                # Structured instant data
                'check_in_time': '14:00:00',
                'check_out_time': '12:00:00',
                'wifi_password': 'MarinaCourt2024',
                'wifi_details': 'Free WiFi in all areas',
                'parking_fee': 0.00,
                'pet_policy': 'Pets not allowed',
                'smoking_policy': 'Smoking allowed in designated areas',
                'cancellation_policy': 'Free cancellation until 24 hours before arrival',
                'currency_used': 'MYR',
                
                # Structured facility data
                'pool_hours': '7:00 AM - 10:00 PM',
                'gym_hours': '6:00 AM - 11:00 PM',
                'spa_hours': 'External spa services available',
                'concierge_hours': '7:00 AM - 11:00 PM',
                'room_service_hours': '7:00 AM - 11:00 PM',
                'business_center_hours': '8:00 AM - 8:00 PM',
                'airport_shuttle_fee': 25.00,
                'airport_shuttle_schedule': 'On request, 24 hours advance notice',
                'facilities': 'Pool, Gym, Kitchenette, Balcony, Tour Desk'
            }
        ]
        
        for hotel in structured_hotels:
            # Insert structured hotel data
            columns = list(hotel.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = list(hotel.values())
            
            query = f"""
                INSERT INTO hotels ({', '.join(columns)})
                VALUES ({placeholders})
            """
            cursor.execute(query, values)
            print(f"   ✅ {hotel['hotel_name']} - Structured data")
        
        conn.commit()
        print(f"✅ Structured knowledge seeded! ({len(structured_hotels)} hotels)")
        return True

def seed_raw_knowledge():
    """Seed raw text knowledge from hotel staff (Tier 3+)."""
    
    print("\n📝 SEEDING RAW KNOWLEDGE")
    print("=" * 40)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Grand Hyatt KL - Raw Staff Knowledge (1-2 pages)
        grand_hyatt_knowledge = """
GRAND HYATT KUALA LUMPUR - STAFF KNOWLEDGE BANK
Written by: Concierge Team Lead Ahmad Rahman
Last Updated: December 2024

LOCATION & ACCESS:
We're right in the heart of KLCC, directly connected to Petronas Twin Towers via covered skybridge. Guests can walk to KLCC park, Suria KLCC shopping mall, and Petronas Twin Towers without getting wet even during monsoon season. The skybridge connection is our biggest advantage - guests love this convenience.

EXCLUSIVE DEALS & PARTNERSHIPS:
- Petronas Twin Towers Skybridge: We get 30% discount for hotel guests (RM85 becomes RM59.50). Must book through us, show room key. Skip online queues.
- Pavilion KL VIP Privileges: Hotel guests get FREE VIP card (normally RM150). Includes personal shopping assistant, 10% extra discount at luxury brands, VIP lounge access Level 6.
- Atmosphere 360° Restaurant: Hotel guests get 20% off total bill. Located at KL Tower, 15 minutes by our car (RM25). Book through us for window table at sunset.

DINING RECOMMENDATIONS:
Best authentic local food within walking distance:
- Jalan Alor Night Market (20 min walk, RM12-15 Grab): Must-try Wong Ah Wah for Char Kway Teow. Avoid 8-9pm peak. Budget RM40-60 for 2 people.
- Suria KLCC Food Court (5 min walk): Clean, air-conditioned, halal options. Great for families. RM25-35 per person.
- Madam Kwan's (Suria KLCC): Upscale Malaysian cuisine, famous for nasi lemak. RM60-80 per person.

SHOPPING AREAS:
1. Suria KLCC (connected): International brands, department store, good for souvenirs on Level 2.
2. Pavilion KL (skybridge): Luxury shopping, our guests get VIP privileges. Show room key at Customer Service.
3. Bukit Bintang area (15 min walk): Local shopping, street food, nightlife. Safe to walk evening.

ATTRACTIONS & ACTIVITIES:
KLCC Park (5 min walk): FREE, beautiful at sunset. Fountain shows 8:30pm & 9:30pm nightly. Kids playground, jogging track.
Petronas Twin Towers: Book skybridge tickets through us for discount. Best photos from KLCC park at sunset.
KL Tower: Great city views, Atmosphere 360° restaurant partnership. We arrange transport.
Aquaria KLCC: Inside convention center, good for families. We can arrange tickets.

TRANSPORTATION:
- Our premium airport transfer: RM90 to KLIA, includes 30-min city tour. Book 24hrs ahead.
- Grab/taxi: Always available, 5-min walk to main road pickup.
- LRT: KLCC station connected underground, easy access to other areas.
- Walking: KLCC area very walkable, covered walkways everywhere.

RELIGIOUS FACILITIES:
Asy-Syakirin Mosque: Located in KLCC park, 7-minute walk. Beautiful architecture, prayer times posted.
St. Andrew's Church: 10 minutes walk, English services Sundays.

SPECIAL SERVICES:
Concierge team available 24/7. We arrange:
- Restaurant reservations with best tables
- Attraction tickets with discounts
- City tours with English-speaking guides
- Airport transfer with city highlights tour
- Shopping assistance with VIP privileges

INSIDER TIPS:
- Show room key everywhere - many places give hotel guest discounts
- Skybridge to Petronas best photo spot is Level 41
- Pavilion KL Customer Service Level 6 for VIP card
- Jalan Alor best after 7pm but before 8pm crowd
- KLCC park fountain show free but get there 15 mins early for good spot
- Grab pickup at Suria KLCC basement faster than main road

WEATHER CONSIDERATIONS:
KL weather unpredictable. Afternoon thunderstorms common. All our recommendations have covered access or indoor alternatives. Skybridge system means guests can stay dry.

SAFETY NOTES:
KLCC area very safe 24/7. Well-lit, security patrols, CCTV everywhere. Petty theft rare but keep valuables secure. Emergency numbers programmed in room phones.

CONTACT INFO:
Concierge Direct: +603-2182-1234 ext. 1200
WhatsApp Concierge: +6012-345-6789
Email: concierge.kl@hyatt.com
We respond within 15 minutes during business hours.
        """
        
        # Marina Court Resort KK - Raw Staff Knowledge
        marina_court_knowledge = """
MARINA COURT RESORT KOTA KINABALU - STAFF KNOWLEDGE BANK
Written by: Front Office Manager Sarah Lim
Last Updated: December 2024

LOCATION ADVANTAGES:
We're strategically located in Kota Kinabalu city center, walking distance to major attractions. Our biggest selling point is proximity to waterfront and sunset views. Guests can walk to Signal Hill Observatory, Atkinson Clock Tower, and floating mosque within 20 minutes.

SUNSET VIEWING SPOTS:
- Signal Hill Observatory: 15 minutes walk uphill, FREE, 360° city views. Best sunset spot in KK. Bring water, can be hot climb.
- Waterfront Esplanade: 10 minutes walk, FREE, popular evening spot. Food stalls, night market vibes.
- Floating Mosque: 20 minutes walk or RM15 Grab. Beautiful architecture, sunset reflection photos.

LOCAL FOOD GEMS:
Night Markets (staff favorites):
- Filipino Market: 15 minutes walk, authentic local food. Try fresh seafood, BBQ stingray. RM20-30 per person.
- Gaya Street Sunday Market: If staying weekend, 12 minutes walk. Local fruits, handicrafts, traditional breakfast.
- Waterfront food courts: 10 minutes walk, safe, varied options, sea breeze dining.

SABAH SPECIALTIES:
Must-try local dishes we recommend:
- Hinava (raw fish salad): Fresh and unique to Sabah
- Butod (sago worm): For adventurous eaters only
- Tenom coffee: Local coffee variety, very strong
- Fresh seafood: Cheaper than Peninsular Malaysia

ISLAND HOPPING:
Tunku Abdul Rahman Marine Park: 
- 10 minutes boat ride from Jesselton Point (15 min walk from hotel)
- We arrange island hopping packages: RM80-120 per person
- Best islands: Sapi, Mamutik for beaches and snorkeling
- Bring own snorkel gear or rent at jetty

MOUNT KINABALU TOURS:
- Day trip to Kinabalu Park: RM200-300 per person via our tour desk
- 2-day climbing packages: RM800-1200 per person
- Hot springs + canopy walk day trip: RM180 per person
- Book 2-3 days advance, weather dependent

CULTURAL EXPERIENCES:
Mari Mari Cultural Village: 
- 45 minutes from city, we arrange transport
- Traditional Sabah tribal experiences
- Includes cultural shows, traditional food
- Half-day tour RM150 per person

SHOPPING:
Suria Sabah: 12 minutes walk, main shopping mall. Good for souvenirs, local products.
Handicraft Market: 8 minutes walk, local art and crafts. Bargaining expected.
Gaya Street: Weekend market, local products, pearls, traditional items.

TRANSPORTATION:
- Airport distance: 15 minutes, RM25-30 by taxi
- City buses: RM2-3, frequent service to major areas
- Grab available but limited drivers
- Walking: Most attractions within 20 minutes walk

RELIGIOUS SITES:
- Kota Kinabalu City Mosque (Floating Mosque): 20 minutes walk, beautiful architecture
- Sacred Heart Cathedral: 10 minutes walk, English masses
- Chinese temples: Various locations, cultural significance

ADVENTURE ACTIVITIES:
- White water rafting: Kiulu River, full day RM250 per person
- Jungle trekking: Various difficulty levels, we arrange guides
- Diving: Sipadan world-famous, but need advance booking
- Firefly watching: Evening tours available

WEATHER & SEASONS:
- Dry season: March-September, best for outdoor activities
- Wet season: October-February, afternoon showers common
- Temperature consistent 26-32°C year-round
- Humidity high, bring light breathable clothes

SAFETY CONSIDERATIONS:
KK generally safe but standard precautions:
- Waterfront area well-patrolled
- Avoid isolated areas after dark
- Watch belongings at markets
- Sun protection essential for island trips

STAFF RECOMMENDATIONS:
Best photo spots: Signal Hill sunset, floating mosque reflection, TARP marine park
Best local experience: Filipino market + sunset at waterfront
Best day trip: Island hopping to Sapi and Mamutik islands
Best cultural experience: Mari Mari Cultural Village

CONTACT & SERVICES:
Front Desk: +6088-231-888
Tour Desk: Extension 1500
We arrange all tours, transport, and reservations. Sabah tourism experts on staff.

INSIDER TIPS:
- Book island hopping early morning for best weather
- Bring reef-safe sunscreen for marine park
- Try local fruits at Gaya Street market
- Waterfront best in evening, too hot midday
- Mount Kinabalu tours weather-dependent, have backup plans
        """
        
        # Insert raw knowledge
        knowledge_entries = [
            {
                'property_id': 'grand_hyatt_kuala_lumpur',
                'knowledge_text': grand_hyatt_knowledge,
                'staff_author': 'Ahmad Rahman - Concierge Team Lead',
                'knowledge_type': 'comprehensive'
            },
            {
                'property_id': 'marina_court_resort_kota_kinabalu',
                'knowledge_text': marina_court_knowledge,
                'staff_author': 'Sarah Lim - Front Office Manager',
                'knowledge_type': 'comprehensive'
            }
        ]
        
        for entry in knowledge_entries:
            cursor.execute("""
                INSERT INTO hotel_knowledge_bank (
                    property_id, knowledge_text, staff_author, knowledge_type
                ) VALUES (?, ?, ?, ?)
            """, (entry['property_id'], entry['knowledge_text'], 
                  entry['staff_author'], entry['knowledge_type']))
            
            hotel_name = entry['property_id'].replace('_', ' ').title()
            print(f"   ✅ {hotel_name} - {len(entry['knowledge_text'])} chars")
        
        conn.commit()
        print(f"✅ Raw knowledge seeded! ({len(knowledge_entries)} hotels)")
        return True

if __name__ == "__main__":
    # Create comprehensive dual knowledge architecture
    if create_dual_knowledge_schema():
        if seed_structured_data():
            if seed_raw_knowledge():
                print("\n🌟 DUAL KNOWLEDGE ARCHITECTURE COMPLETE!")
                print("=" * 50)
                print("✅ STRUCTURED LAYER: Fast lookup data (Tier 1-2)")
                print("✅ RAW LAYER: Staff-written knowledge (Tier 3+)")
                print("✅ Optimized for both instant responses and semantic search")
                print("✅ Scalable to 100+ hotels")
            else:
                print("❌ Raw knowledge seeding failed")
        else:
            print("❌ Structured data seeding failed")
    else:
        print("❌ Schema creation failed") 
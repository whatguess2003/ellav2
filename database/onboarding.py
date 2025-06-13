#!/usr/bin/env python3
"""
Hotel Onboarding System
Add hotels one by one to prevent duplicates and ensure data quality
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

class HotelOnboardingSystem:
    """Manages hotel onboarding to prevent duplicates and ensure data quality."""
    
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def check_hotel_exists(self, hotel_name: str, city_name: str, state_name: str) -> bool:
        """Check if hotel already exists in the database."""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM hotels 
                WHERE LOWER(hotel_name) = LOWER(?) AND city_name = ? AND state_name = ?
            """, (hotel_name, city_name, state_name))
            
            count = cursor.fetchone()[0]
            return count > 0
    
    def get_available_cities(self) -> List[Dict]:
        """Get list of available cities."""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT city_name, state_name, country_name, airport_code, city_code
                FROM cities
                ORDER BY city_name
            """)
            
            cities = []
            for row in cursor.fetchall():
                cities.append({
                    'city_name': row[0],
                    'state_name': row[1],
                    'country_name': row[2],
                    'airport_code': row[3],
                    'city_code': row[4]  # Optional legacy reference
                })
            
            return cities
    
    def add_hotel(self, hotel_data: Dict) -> Dict:
        """Add a new hotel to the database."""
        
        try:
            # Validate required fields
            required_fields = ['hotel_name', 'city_name', 'state_name', 'star_rating']
            for field in required_fields:
                if field not in hotel_data or not hotel_data[field]:
                    return {
                        'success': False,
                        'message': f"Missing required field: {field}"
                    }
            
            # Check if hotel already exists
            if self.check_hotel_exists(hotel_data['hotel_name'], hotel_data['city_name'], hotel_data['state_name']):
                return {
                    'success': False,
                    'message': f"Hotel '{hotel_data['hotel_name']}' already exists in {hotel_data['city_name']}, {hotel_data['state_name']}"
                }
            
            # Generate property_id
            property_id = self.generate_property_id(hotel_data['hotel_name'], hotel_data['city_name'], hotel_data['state_name'])
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify city exists
                cursor.execute("""
                    SELECT country_name 
                    FROM cities 
                    WHERE city_name = ? AND state_name = ?
                """, (hotel_data['city_name'], hotel_data['state_name']))
                
                city_info = cursor.fetchone()
                if not city_info:
                    return {
                        'success': False,
                        'message': f"Invalid location: {hotel_data['city_name']}, {hotel_data['state_name']}"
                    }
                
                country_name = city_info[0]
                
                # Insert hotel
                cursor.execute("""
                    INSERT INTO hotels (
                        property_id, hotel_name, hotel_brand, star_rating,
                        city_name, state_name, country_name, address, postcode,
                        phone, email, website, latitude, longitude,
                        distance_to_airport_km, check_in_time, check_out_time,
                        description, facilities, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    property_id,
                    hotel_data['hotel_name'],
                    hotel_data.get('hotel_brand'),
                    hotel_data['star_rating'],
                    hotel_data['city_name'],
                    hotel_data['state_name'],
                    country_name,
                    hotel_data.get('address'),
                    hotel_data.get('postcode'),
                    hotel_data.get('phone'),
                    hotel_data.get('email'),
                    hotel_data.get('website'),
                    hotel_data.get('latitude'),
                    hotel_data.get('longitude'),
                    hotel_data.get('distance_to_airport_km'),
                    hotel_data.get('check_in_time', '15:00:00'),
                    hotel_data.get('check_out_time', '12:00:00'),
                    hotel_data.get('description'),
                    json.dumps(hotel_data.get('facilities', [])),
                    hotel_data.get('is_active', 1)
                ))
                
                # Add hotel amenities if provided
                if 'amenities' in hotel_data:
                    for amenity in hotel_data['amenities']:
                        cursor.execute("""
                            INSERT INTO hotel_amenities (
                                property_id, amenity_name, amenity_category,
                                amenity_description, is_free, operating_hours
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            property_id,
                            amenity['name'],
                            amenity.get('category'),
                            amenity.get('description'),
                            amenity.get('is_free', 1),
                            amenity.get('operating_hours')
                        ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Hotel '{hotel_data['hotel_name']}' added successfully",
                    'property_id': property_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error adding hotel: {str(e)}"
            }
    
    def add_room_type(self, property_id: str, room_data: Dict) -> Dict:
        """Add a room type to a hotel."""
        
        try:
            # Validate required fields
            required_fields = ['room_name', 'max_occupancy', 'base_price_per_night']
            for field in required_fields:
                if field not in room_data or room_data[field] is None:
                    return {
                        'success': False,
                        'message': f"Missing required field: {field}"
                    }
            
            # Generate room_type_id
            room_type_id = self.generate_room_type_id(property_id, room_data['room_name'])
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if hotel exists
                cursor.execute("SELECT hotel_name FROM hotels WHERE property_id = ?", (property_id,))
                hotel = cursor.fetchone()
                if not hotel:
                    return {
                        'success': False,
                        'message': f"Hotel with property_id '{property_id}' not found"
                    }
                
                # Insert room type
                cursor.execute("""
                    INSERT INTO room_types (
                        room_type_id, property_id, room_name, room_description,
                        bed_type, view_type, room_size_sqm, max_occupancy,
                        base_price_per_night, amenities, room_features,
                        total_rooms, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    room_type_id,
                    property_id,
                    room_data['room_name'],
                    room_data.get('room_description'),
                    room_data.get('bed_type'),
                    room_data.get('view_type'),
                    room_data.get('room_size_sqm'),
                    room_data['max_occupancy'],
                    room_data['base_price_per_night'],
                    json.dumps(room_data.get('amenities', [])),
                    json.dumps(room_data.get('room_features', [])),
                    room_data.get('total_rooms', 1),
                    room_data.get('is_active', 1)
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f"Room type '{room_data['room_name']}' added to {hotel[0]}",
                    'room_type_id': room_type_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Error adding room type: {str(e)}"
            }
    
    def generate_property_id(self, hotel_name: str, city_name: str, state_name: str) -> str:
        """Generate a human-readable property ID using raw names."""
        
        # Clean and format hotel name and city
        hotel_clean = hotel_name.lower().replace(' ', '-').replace("'", "").replace(',', '').replace('.', '').replace('&', 'and').replace('@', 'at')
        city_clean = city_name.lower().replace(' ', '-').replace("'", "").replace(',', '').replace('.', '')
        
        # Remove common words that add noise
        noise_words = ['hotel', 'resort', 'inn', 'suites', 'the', 'a', 'an']
        hotel_parts = [part for part in hotel_clean.split('-') if part not in noise_words and part]
        hotel_clean = '-'.join(hotel_parts) if hotel_parts else hotel_clean
        
        # Create property ID: hotel-name_city-name
        property_id = f"{hotel_clean}_{city_clean}"
        
        # Ensure uniqueness by checking database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hotels WHERE property_id LIKE ?", (f"{property_id}%",))
            count = cursor.fetchone()[0]
            
            if count > 0:
                property_id = f"{property_id}_{count + 1}"
        
        return property_id
    
    def generate_room_type_id(self, property_id: str, room_name: str) -> str:
        """Generate a human-readable room type ID using raw names."""
        
        # Clean room name
        room_clean = room_name.lower().replace(' ', '-').replace("'", "").replace(',', '').replace('.', '').replace('&', 'and').replace('@', 'at')
        
        # Remove common room words that add noise
        noise_words = ['room', 'suite', 'view', 'the', 'a', 'an', 'with']
        room_parts = [part for part in room_clean.split('-') if part not in noise_words and part]
        room_clean = '-'.join(room_parts) if room_parts else room_clean
        
        # Create room type ID: property-id_room-name
        room_type_id = f"{property_id}_{room_clean}"
        
        # Ensure uniqueness by checking database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM room_types WHERE room_type_id LIKE ?", (f"{room_type_id}%",))
            count = cursor.fetchone()[0]
            
            if count > 0:
                room_type_id = f"{room_type_id}_{count + 1}"
        
        return room_type_id
    
    def list_hotels(self) -> List[Dict]:
        """List all hotels in the database."""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT h.property_id, h.hotel_name, h.hotel_brand, h.star_rating,
                       h.city_name, h.state_name, h.is_active,
                       COUNT(rt.room_type_id) as room_types_count
                FROM hotels h
                LEFT JOIN room_types rt ON h.property_id = rt.property_id
                GROUP BY h.property_id
                ORDER BY h.hotel_name
            """)
            
            hotels = []
            for row in cursor.fetchall():
                hotels.append({
                    'property_id': row[0],
                    'hotel_name': row[1],
                    'hotel_brand': row[2],
                    'star_rating': row[3],
                    'city_name': row[4],
                    'state_name': row[5],
                    'is_active': bool(row[6]),
                    'room_types_count': row[7]
                })
            
            return hotels
    
    def get_hotel_details(self, property_id: str) -> Optional[Dict]:
        """Get detailed information about a specific hotel."""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get hotel info
            cursor.execute("""
                SELECT h.*, c.country_name
                FROM hotels h
                JOIN cities c ON h.city_name = c.city_name AND h.state_name = c.state_name
                WHERE h.property_id = ?
            """, (property_id,))
            
            hotel_row = cursor.fetchone()
            if not hotel_row:
                return None
            
            # Get room types
            cursor.execute("""
                SELECT * FROM room_types WHERE property_id = ? ORDER BY room_name
            """, (property_id,))
            
            room_types = []
            for room_row in cursor.fetchall():
                room_types.append({
                    'room_type_id': room_row[0],
                    'room_name': room_row[2],
                    'room_description': room_row[3],
                    'bed_type': room_row[4],
                    'view_type': room_row[5],
                    'room_size_sqm': room_row[6],
                    'max_occupancy': room_row[7],
                    'base_price_per_night': room_row[8],
                    'total_rooms': room_row[11],
                    'is_active': bool(room_row[12])
                })
            
            # Get amenities
            cursor.execute("""
                SELECT amenity_name, amenity_category, amenity_description, is_free
                FROM hotel_amenities WHERE property_id = ?
            """, (property_id,))
            
            amenities = []
            for amenity_row in cursor.fetchall():
                amenities.append({
                    'name': amenity_row[0],
                    'category': amenity_row[1],
                    'description': amenity_row[2],
                    'is_free': bool(amenity_row[3])
                })
            
            hotel_details = {
                'property_id': hotel_row[0],
                'hotel_name': hotel_row[1],
                'hotel_brand': hotel_row[2],
                'star_rating': hotel_row[3],
                'city_name': hotel_row[4],
                'state_name': hotel_row[5],
                'country_name': hotel_row[21],  # From the joined cities table
                'address': hotel_row[7],
                'phone': hotel_row[9],
                'email': hotel_row[10],
                'website': hotel_row[11],
                'distance_to_airport_km': hotel_row[14],
                'description': hotel_row[17],
                'room_types': room_types,
                'amenities': amenities,
                'is_active': bool(hotel_row[18])
            }
            
            return hotel_details

def interactive_hotel_onboarding():
    """Interactive command-line hotel onboarding."""
    
    print("🏨 HOTEL ONBOARDING SYSTEM")
    print("=" * 40)
    
    onboarding = HotelOnboardingSystem()
    
    while True:
        print("\n📋 OPTIONS:")
        print("1. Add new hotel")
        print("2. Add room type to existing hotel")
        print("3. List all hotels")
        print("4. View hotel details")
        print("5. Show available cities")
        print("6. Exit")
        
        choice = input("\n🤔 Choose an option (1-6): ").strip()
        
        if choice == '1':
            add_new_hotel(onboarding)
        elif choice == '2':
            add_room_type_to_hotel(onboarding)
        elif choice == '3':
            list_all_hotels(onboarding)
        elif choice == '4':
            view_hotel_details(onboarding)
        elif choice == '5':
            show_available_cities(onboarding)
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

def add_new_hotel(onboarding: HotelOnboardingSystem):
    """Add a new hotel interactively."""
    
    print("\n🏨 ADD NEW HOTEL")
    print("-" * 20)
    
    # Show available cities
    cities = onboarding.get_available_cities()
    print("\n🏙️ Available cities:")
    for city in cities:
        print(f"   {city['city_name']}, {city['state_name']} (Airport: {city['airport_code'] or 'N/A'})")
    
    # Get hotel data
    hotel_data = {}
    hotel_data['hotel_name'] = input("\n🏨 Hotel name: ").strip()
    hotel_data['city_name'] = input("🏙️ City name: ").strip()
    hotel_data['state_name'] = input("🏛️ State name: ").strip()
    
    try:
        hotel_data['star_rating'] = int(input("⭐ Star rating (1-5): "))
    except ValueError:
        print("❌ Invalid star rating")
        return
    
    hotel_data['hotel_brand'] = input("🏢 Hotel brand (optional): ").strip() or None
    hotel_data['address'] = input("📍 Address (optional): ").strip() or None
    hotel_data['phone'] = input("📞 Phone (optional): ").strip() or None
    hotel_data['email'] = input("📧 Email (optional): ").strip() or None
    
    # Add hotel
    result = onboarding.add_hotel(hotel_data)
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"🆔 Property ID: {result['property_id']}")
        
        # Ask if they want to add room types
        add_rooms = input("\n🛏️ Do you want to add room types now? (y/N): ").lower().strip()
        if add_rooms == 'y':
            add_room_types_to_new_hotel(onboarding, result['property_id'])
    else:
        print(f"❌ {result['message']}")

def add_room_types_to_new_hotel(onboarding: HotelOnboardingSystem, property_id: str):
    """Add room types to a newly created hotel."""
    
    while True:
        print(f"\n🛏️ ADD ROOM TYPE TO {property_id}")
        print("-" * 30)
        
        room_data = {}
        room_data['room_name'] = input("🛏️ Room name: ").strip()
        
        try:
            room_data['max_occupancy'] = int(input("👥 Max occupancy: "))
            room_data['base_price_per_night'] = float(input("💰 Base price per night (MYR): "))
        except ValueError:
            print("❌ Invalid number")
            continue
        
        room_data['bed_type'] = input("🛏️ Bed type (King/Queen/Twin/Single, optional): ").strip() or None
        room_data['view_type'] = input("🌊 View type (Sea/Pool/City/Garden, optional): ").strip() or None
        
        try:
            size_input = input("📐 Room size (sqm, optional): ").strip()
            room_data['room_size_sqm'] = int(size_input) if size_input else None
        except ValueError:
            room_data['room_size_sqm'] = None
        
        # Add room type
        result = onboarding.add_room_type(property_id, room_data)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
        # Ask if they want to add another room type
        another = input("\n🤔 Add another room type? (y/N): ").lower().strip()
        if another != 'y':
            break

def add_room_type_to_hotel(onboarding: HotelOnboardingSystem):
    """Add room type to existing hotel."""
    
    print("\n🛏️ ADD ROOM TYPE TO EXISTING HOTEL")
    print("-" * 40)
    
    # Show hotels
    hotels = onboarding.list_hotels()
    if not hotels:
        print("❌ No hotels found. Please add a hotel first.")
        return
    
    print("\n🏨 Available hotels:")
    for hotel in hotels:
        print(f"   {hotel['property_id']}: {hotel['hotel_name']} ({hotel['city_name']})")
    
    property_id = input("\n🆔 Enter property ID: ").strip()
    
    # Get room data and add
    room_data = {}
    room_data['room_name'] = input("🛏️ Room name: ").strip()
    
    try:
        room_data['max_occupancy'] = int(input("👥 Max occupancy: "))
        room_data['base_price_per_night'] = float(input("💰 Base price per night (MYR): "))
    except ValueError:
        print("❌ Invalid number")
        return
    
    result = onboarding.add_room_type(property_id, room_data)
    
    if result['success']:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")

def list_all_hotels(onboarding: HotelOnboardingSystem):
    """List all hotels."""
    
    hotels = onboarding.list_hotels()
    
    if not hotels:
        print("\n❌ No hotels found.")
        return
    
    print(f"\n🏨 ALL HOTELS ({len(hotels)} total)")
    print("-" * 60)
    
    for hotel in hotels:
        status = "✅ Active" if hotel['is_active'] else "❌ Inactive"
        print(f"{hotel['property_id']}: {hotel['hotel_name']} ({hotel['star_rating']}⭐)")
        print(f"   📍 {hotel['city_name']}, {hotel['state_name']}")
        print(f"   🛏️ {hotel['room_types_count']} room types | {status}")
        print()

def view_hotel_details(onboarding: HotelOnboardingSystem):
    """View detailed hotel information."""
    
    property_id = input("\n🆔 Enter property ID: ").strip()
    
    details = onboarding.get_hotel_details(property_id)
    
    if not details:
        print("❌ Hotel not found.")
        return
    
    print(f"\n🏨 {details['hotel_name']} ({details['star_rating']}⭐)")
    print("=" * 50)
    print(f"🆔 Property ID: {details['property_id']}")
    print(f"📍 Location: {details['city_name']}, {details['state_name']}, {details['country_name']}")
    if details['address']:
        print(f"🏠 Address: {details['address']}")
    if details['phone']:
        print(f"📞 Phone: {details['phone']}")
    if details['distance_to_airport_km']:
        print(f"✈️ Airport distance: {details['distance_to_airport_km']} km")
    
    if details['room_types']:
        print(f"\n🛏️ ROOM TYPES ({len(details['room_types'])})")
        for room in details['room_types']:
            print(f"   • {room['room_name']} - RM{room['base_price_per_night']}/night")
            print(f"     👥 Max: {room['max_occupancy']} | 🛏️ {room['bed_type'] or 'N/A'} | 🌊 {room['view_type'] or 'N/A'}")
    
    if details['amenities']:
        print(f"\n🏊 AMENITIES ({len(details['amenities'])})")
        for amenity in details['amenities']:
            free_text = " (Free)" if amenity['is_free'] else " (Paid)"
            print(f"   • {amenity['name']}{free_text}")

def show_available_cities(onboarding: HotelOnboardingSystem):
    """Show available cities."""
    
    cities = onboarding.get_available_cities()
    
    print(f"\n🏙️ AVAILABLE CITIES ({len(cities)} total)")
    print("-" * 40)
    
    for city in cities:
        airport_text = f" ({city['airport_code']})" if city['airport_code'] else ""
        print(f"{city['city_name']}, {city['state_name']}{airport_text}")

if __name__ == "__main__":
    interactive_hotel_onboarding() 
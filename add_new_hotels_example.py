#!/usr/bin/env python3
"""
Example: Adding New Hotels to ELLA Database
Shows how to add hotels programmatically
"""

from manage_database import DatabaseManager

def add_sample_hotels():
    """Add some example hotels to demonstrate the process"""
    
    manager = DatabaseManager()
    
    # Example hotels to add
    new_hotels = [
        {
            'name': 'Shangri-La Hotel Kuala Lumpur',
            'slug': 'shangri-la-kuala-lumpur',
            'city': 'Kuala Lumpur',
            'state': 'Kuala Lumpur',
            'star_rating': 5,
            'description': 'Luxury hotel with panoramic city views and world-class amenities',
            'amenities': ['WiFi', 'Pool', 'Spa', 'Gym', 'Restaurant', 'Bar', 'Concierge', 'Business Center']
        },
        {
            'name': 'Hotel Istana Kuala Lumpur',
            'slug': 'hotel-istana-kuala-lumpur',
            'city': 'Kuala Lumpur', 
            'state': 'Kuala Lumpur',
            'star_rating': 4,
            'description': 'Contemporary hotel in the heart of Kuala Lumpur with modern facilities',
            'amenities': ['WiFi', 'Pool', 'Gym', 'Restaurant', 'Business Center']
        },
        {
            'name': 'The Majestic Hotel Kuala Lumpur',
            'slug': 'majestic-hotel-kuala-lumpur',
            'city': 'Kuala Lumpur',
            'state': 'Kuala Lumpur', 
            'star_rating': 5,
            'description': 'Historic luxury hotel blending colonial charm with modern elegance',
            'amenities': ['WiFi', 'Pool', 'Spa', 'Restaurant', 'Bar', 'Heritage Tours']
        },
        {
            'name': 'Gaya Island Resort',
            'slug': 'gaya-island-resort',
            'city': 'Kota Kinabalu',
            'state': 'Sabah',
            'star_rating': 5,
            'description': 'Eco-luxury resort on pristine Gaya Island with overwater villas',
            'amenities': ['WiFi', 'Beach Access', 'Spa', 'Water Sports', 'Nature Tours', 'Restaurant']
        },
        {
            'name': 'Cameron Highlands Resort',
            'slug': 'cameron-highlands-resort',
            'city': 'Cameron Highlands',
            'state': 'Pahang',
            'star_rating': 4,
            'description': 'Colonial-style resort in the cool highlands with tea plantation views',
            'amenities': ['WiFi', 'Spa', 'Restaurant', 'Tea Tours', 'Golf', 'Nature Walks']
        }
    ]
    
    print("🏨 Adding new hotels to ELLA database...")
    print(f"📊 Current database type: {manager.db_manager.db_type}")
    
    # Add each hotel
    for hotel in new_hotels:
        print(f"\n➕ Adding: {hotel['name']}")
        success = manager.add_hotel(hotel)
        
        if success:
            print(f"   ✅ Added successfully")
        else:
            print(f"   ❌ Failed to add")
    
    print("\n🎉 Hotel addition process complete!")
    
    # Show updated status
    print("\n" + "="*50)
    manager.health_check()

def create_custom_hotel():
    """Example of creating a custom hotel"""
    
    custom_hotel = {
        'name': input("Hotel name: "),
        'slug': input("Hotel slug (lowercase-with-dashes): "),
        'city': input("City: "),
        'state': input("State: "),
        'star_rating': int(input("Star rating (1-5): ")),
        'description': input("Description: "),
        'amenities': input("Amenities (comma-separated): ").split(',')
    }
    
    manager = DatabaseManager()
    success = manager.add_hotel(custom_hotel)
    
    if success:
        print(f"✅ Successfully added {custom_hotel['name']}!")
    else:
        print(f"❌ Failed to add {custom_hotel['name']}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--custom':
        create_custom_hotel()
    else:
        add_sample_hotels() 
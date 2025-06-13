"""
Database Connection Manager
Automatically switches between SQLite (local) and PostgreSQL (Railway)
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Union, Dict, Any, List

class DatabaseManager:
    def __init__(self):
        self.is_production = bool(os.getenv('DATABASE_URL') or os.getenv('PGHOST'))
        self.database_url = self._get_database_url()
        
    def _get_database_url(self):
        """Get database connection URL"""
        if self.is_production:
            # Railway PostgreSQL
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                host = os.getenv('PGHOST')
                port = os.getenv('PGPORT', '5432')
                database = os.getenv('PGDATABASE')
                user = os.getenv('PGUSER')
                password = os.getenv('PGPASSWORD')
                database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            return database_url
        else:
            # Local SQLite
            return 'ella.db'
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        if self.is_production:
            # PostgreSQL connection
            conn = psycopg2.connect(self.database_url)
            try:
                yield conn
            finally:
                conn.close()
        else:
            # SQLite connection
            conn = sqlite3.connect(self.database_url)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            try:
                yield conn
            finally:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            if self.is_production:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            # Convert to list of dicts for consistency
            if results:
                if self.is_production:
                    return [dict(row) for row in results]
                else:
                    return [dict(row) for row in results]
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return cursor.rowcount
    
    def check_availability(self, hotel_name: str, check_in: str, check_out: str = None) -> Dict[str, Any]:
        """Check room availability for a hotel"""
        try:
            # First, find the hotel
            if self.is_production:
                hotel_query = """
                    SELECT id, name, location, star_rating 
                    FROM hotels 
                    WHERE LOWER(name) LIKE LOWER(%s) OR LOWER(name) LIKE LOWER(%s)
                """
            else:
                hotel_query = """
                    SELECT id, name, location, star_rating 
                    FROM hotels 
                    WHERE LOWER(name) LIKE LOWER(?) OR LOWER(name) LIKE LOWER(?)
                """
            
            hotel_pattern = f"%{hotel_name}%"
            hotels = self.execute_query(hotel_query, (hotel_pattern, hotel_pattern))
            
            if not hotels:
                return {
                    'success': False,
                    'message': f'Hotel "{hotel_name}" not found',
                    'available_rooms': []
                }
            
            hotel = hotels[0]
            hotel_id = hotel['id']
            
            # Check availability
            if self.is_production:
                availability_query = """
                    SELECT 
                        r.room_type,
                        r.room_name,
                        r.base_price,
                        r.max_occupancy,
                        r.bed_type,
                        ra.available_rooms,
                        ra.price_per_night,
                        ra.date
                    FROM hotel_rooms r
                    LEFT JOIN room_availability ra ON r.id = ra.room_id 
                    WHERE r.hotel_id = %s AND ra.date = %s
                    AND ra.available_rooms > 0
                """
            else:
                availability_query = """
                    SELECT 
                        r.room_type,
                        r.room_name,
                        r.base_price,
                        r.max_occupancy,
                        r.bed_type,
                        ra.available_rooms,
                        ra.price_per_night,
                        ra.date
                    FROM hotel_rooms r
                    LEFT JOIN room_availability ra ON r.id = ra.room_id 
                    WHERE r.hotel_id = ? AND ra.date = ?
                    AND ra.available_rooms > 0
                """
            
            available_rooms = self.execute_query(availability_query, (hotel_id, check_in))
            
            return {
                'success': True,
                'hotel': hotel,
                'check_in_date': check_in,
                'available_rooms': available_rooms,
                'message': f"Found {len(available_rooms)} available room types at {hotel['name']}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Availability check failed: {str(e)}',
                'available_rooms': []
            }
    
    def search_hotels(self, location: str = None, budget_max: float = None) -> List[Dict[str, Any]]:
        """Search for hotels by location and budget"""
        try:
            query_parts = ["SELECT * FROM hotels WHERE 1=1"]
            params = []
            
            if location:
                if self.is_production:
                    query_parts.append("AND LOWER(location) LIKE LOWER(%s)")
                else:
                    query_parts.append("AND LOWER(location) LIKE LOWER(?)")
                params.append(f"%{location}%")
            
            if budget_max:
                # Join with rooms to check price
                query_parts = ["""
                    SELECT DISTINCT h.*, MIN(r.base_price) as min_price
                    FROM hotels h
                    JOIN hotel_rooms r ON h.id = r.hotel_id
                    WHERE 1=1
                """]
                
                if location:
                    if self.is_production:
                        query_parts.append("AND LOWER(h.location) LIKE LOWER(%s)")
                    else:
                        query_parts.append("AND LOWER(h.location) LIKE LOWER(?)")
                
                query_parts.append("GROUP BY h.id, h.name, h.location, h.address, h.phone, h.email, h.star_rating, h.description, h.check_in_time, h.check_out_time, h.created_at, h.updated_at")
                
                if self.is_production:
                    query_parts.append("HAVING MIN(r.base_price) <= %s")
                else:
                    query_parts.append("HAVING MIN(r.base_price) <= ?")
                params.append(budget_max)
            
            query_parts.append("ORDER BY star_rating DESC, name")
            
            query = " ".join(query_parts)
            return self.execute_query(query, tuple(params) if params else None)
            
        except Exception as e:
            print(f"Hotel search error: {e}")
            return []
    
    def get_hotel_details(self, hotel_name: str) -> Dict[str, Any]:
        """Get detailed information about a hotel"""
        try:
            # Find hotel
            if self.is_production:
                hotel_query = "SELECT * FROM hotels WHERE LOWER(name) LIKE LOWER(%s)"
            else:
                hotel_query = "SELECT * FROM hotels WHERE LOWER(name) LIKE LOWER(?)"
            
            hotels = self.execute_query(hotel_query, (f"%{hotel_name}%",))
            
            if not hotels:
                return {'success': False, 'message': f'Hotel "{hotel_name}" not found'}
            
            hotel = hotels[0]
            
            # Get room types
            if self.is_production:
                rooms_query = """
                    SELECT room_type, room_name, base_price, max_occupancy, bed_type, description
                    FROM hotel_rooms 
                    WHERE hotel_id = %s
                    ORDER BY base_price
                """
            else:
                rooms_query = """
                    SELECT room_type, room_name, base_price, max_occupancy, bed_type, description
                    FROM hotel_rooms 
                    WHERE hotel_id = ?
                    ORDER BY base_price
                """
            
            rooms = self.execute_query(rooms_query, (hotel['id'],))
            
            # Get amenities
            if self.is_production:
                amenities_query = """
                    SELECT amenity_name, amenity_type, description
                    FROM hotel_amenities 
                    WHERE hotel_id = %s AND is_available = true
                """
            else:
                amenities_query = """
                    SELECT amenity_name, amenity_type, description
                    FROM hotel_amenities 
                    WHERE hotel_id = ? AND is_available = 1
                """
            
            amenities = self.execute_query(amenities_query, (hotel['id'],))
            
            return {
                'success': True,
                'hotel': hotel,
                'rooms': rooms,
                'amenities': amenities
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error getting hotel details: {str(e)}'}

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def check_availability(hotel_name: str, check_in: str, check_out: str = None):
    """Check room availability"""
    return db_manager.check_availability(hotel_name, check_in, check_out)

def search_hotels(location: str = None, budget_max: float = None):
    """Search hotels"""
    return db_manager.search_hotels(location, budget_max)

def get_hotel_details(hotel_name: str):
    """Get hotel details"""
    return db_manager.get_hotel_details(hotel_name) 
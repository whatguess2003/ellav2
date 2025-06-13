from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
from datetime import datetime, timedelta
import uvicorn
from contextlib import asynccontextmanager
from enum import Enum

# PMS Room Status Enum - Following industry standards
class RoomStatus(str, Enum):
    CLEAN_VACANT = "CLEAN_VACANT"           # Ready for guest
    DIRTY_VACANT = "DIRTY_VACANT"           # Needs housekeeping
    OCCUPIED = "OCCUPIED"                   # Guest is in room
    RESERVED = "RESERVED"                   # Assigned but not checked in
    OUT_OF_ORDER = "OUT_OF_ORDER"          # Maintenance required
    MAINTENANCE = "MAINTENANCE"             # Under repair
    BLOCKED = "BLOCKED"                     # Administratively blocked

# Booking Status Enum
class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"                 # Booking confirmed
    CHECKED_IN = "CHECKED_IN"               # Guest checked in
    CHECKED_OUT = "CHECKED_OUT"             # Guest checked out
    CANCELLED = "CANCELLED"                 # Booking cancelled
    NO_SHOW = "NO_SHOW"                     # Guest didn't show

# Assignment Status Enum
class AssignmentStatus(str, Enum):
    ASSIGNED = "ASSIGNED"                   # Room assigned, awaiting check-in
    CHECKED_IN = "CHECKED_IN"               # Guest checked in
    CHECKED_OUT = "CHECKED_OUT"             # Guest checked out
    CANCELLED = "CANCELLED"                 # Assignment cancelled

# New cleaner status system
class CleanlinessStatus(str, Enum):
    CLEAN = "CLEAN"                         # Room is clean and ready
    DIRTY = "DIRTY"                         # Room needs housekeeping
    MAINTENANCE = "MAINTENANCE"             # Room under maintenance
    OUT_OF_ORDER = "OUT_OF_ORDER"          # Room not available

class OccupancyStatus(str, Enum):
    VACANT = "VACANT"                       # No guest on this date
    RESERVED = "RESERVED"                   # Guest assigned but not checked in
    OCCUPIED = "OCCUPIED"                   # Guest is checked in
    BLOCKED = "BLOCKED"                     # Administratively blocked

class DashboardService:
    def __init__(self, db_path: str = "ella.db"):
        self.db_path = db_path
    
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def validate_room_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate if room status transition is allowed following PMS business rules"""
        
        # Define allowed transitions
        allowed_transitions = {
            RoomStatus.CLEAN_VACANT: [RoomStatus.RESERVED, RoomStatus.OUT_OF_ORDER, RoomStatus.BLOCKED, RoomStatus.MAINTENANCE, RoomStatus.DIRTY_VACANT],
            RoomStatus.DIRTY_VACANT: [RoomStatus.CLEAN_VACANT, RoomStatus.RESERVED, RoomStatus.OUT_OF_ORDER, RoomStatus.MAINTENANCE],
            RoomStatus.RESERVED: [RoomStatus.OCCUPIED, RoomStatus.CLEAN_VACANT, RoomStatus.DIRTY_VACANT],
            RoomStatus.OCCUPIED: [RoomStatus.DIRTY_VACANT, RoomStatus.OUT_OF_ORDER],
            RoomStatus.OUT_OF_ORDER: [RoomStatus.DIRTY_VACANT, RoomStatus.RESERVED, RoomStatus.MAINTENANCE],
            RoomStatus.MAINTENANCE: [RoomStatus.DIRTY_VACANT, RoomStatus.RESERVED, RoomStatus.OUT_OF_ORDER],
            RoomStatus.BLOCKED: [RoomStatus.CLEAN_VACANT, RoomStatus.DIRTY_VACANT]
        }
        
        return new_status in allowed_transitions.get(current_status, [])
    
    def validate_booking_dates(self, check_in_date: str, check_out_date: str) -> Tuple[bool, str]:
        """Validate booking dates follow business rules"""
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check-in cannot be in the past (except today)
            if check_in < today:
                return False, "Check-in date cannot be in the past"
            
            # Check-out must be after check-in
            if check_out <= check_in:
                return False, "Check-out date must be after check-in date"
            
            # Maximum stay length (e.g., 30 days)
            max_stay_days = 30
            if (check_out - check_in).days > max_stay_days:
                return False, f"Maximum stay is {max_stay_days} days"
            
            return True, "Valid dates"
            
        except ValueError:
            return False, "Invalid date format"
    
    def get_room_occupancy_status(self, room_id: str, date: str) -> str:
        """Get room occupancy status for a specific date"""
        conn = self.get_db_connection()
        try:
            # Check for assignments on this date
            assignment = conn.execute("""
                SELECT assignment_status, check_in_date, check_out_date
                FROM room_assignments 
                WHERE room_id = ? 
                AND assignment_status IN (?, ?)
                AND check_in_date <= ? AND check_out_date > ?
            """, (room_id, AssignmentStatus.ASSIGNED, AssignmentStatus.CHECKED_IN, date, date)).fetchone()
            
            if assignment:
                if assignment['assignment_status'] == AssignmentStatus.CHECKED_IN:
                    return OccupancyStatus.OCCUPIED
                else:
                    return OccupancyStatus.RESERVED
            
            return OccupancyStatus.VACANT
            
        finally:
            conn.close()

    def check_room_availability(self, room_id: str, check_in_date: str, check_out_date: str, exclude_booking_id: str = None) -> Tuple[bool, str]:
        """Check if room is available for given dates"""
        conn = self.get_db_connection()
        try:
            # Check for existing assignments that overlap
            query = """
                SELECT ra.assignment_id, ra.booking_id, ra.guest_name, ra.check_in_date, ra.check_out_date
                FROM room_assignments ra
                WHERE ra.room_id = ? 
                AND ra.assignment_status IN (?, ?)
                AND NOT (ra.check_out_date <= ? OR ra.check_in_date >= ?)
            """
            params = [room_id, AssignmentStatus.ASSIGNED, AssignmentStatus.CHECKED_IN, check_in_date, check_out_date]
            
            # Exclude specific booking if provided (for updates)
            if exclude_booking_id:
                query += " AND ra.booking_id != ?"
                params.append(exclude_booking_id)
            
            conflicts = conn.execute(query, params).fetchall()
            
            if conflicts:
                conflict = conflicts[0]
                return False, f"Room is occupied by {conflict['guest_name']} from {conflict['check_in_date']} to {conflict['check_out_date']}"
            
            return True, "Room is available"
            
        finally:
            conn.close()
    
    def get_suitable_rooms(self, property_id: str, room_type_id: str, check_in_date: str, check_out_date: str, num_guests: int = 1) -> List[Dict]:
        """Get rooms that are suitable and available for the booking"""
        conn = self.get_db_connection()
        try:
            # Get rooms of the specified type that can accommodate the guests
            suitable_rooms = conn.execute("""
                SELECT r.*, rt.room_name, rt.max_occupancy
                FROM rooms r
                JOIN room_types rt ON r.room_type_id = rt.room_type_id
                WHERE r.property_id = ? 
                AND r.room_type_id = ?
                AND rt.max_occupancy >= ?
                AND r.room_status IN (?, ?)
                AND r.is_active = 1
                ORDER BY r.floor, r.room_number
            """, (property_id, room_type_id, num_guests, RoomStatus.CLEAN_VACANT, RoomStatus.DIRTY_VACANT)).fetchall()
            
            # Filter by availability
            available_rooms = []
            for room in suitable_rooms:
                is_available, message = self.check_room_availability(room['room_id'], check_in_date, check_out_date)
                if is_available:
                    room_dict = dict(room)
                    room_dict['availability_message'] = message
                    available_rooms.append(room_dict)
            
            return available_rooms
            
        finally:
            conn.close()
    
    def get_hotels_summary(self) -> List[Dict]:
        """Get all hotels with summary statistics"""
        conn = self.get_db_connection()
        try:
            # Get hotels with basic stats
            hotels = conn.execute("""
                SELECT 
                    h.property_id,
                    h.hotel_name,
                    h.star_rating,
                    h.city_name,
                    h.country_name,
                    COUNT(DISTINCT rt.room_type_id) as room_types_count,
                    COALESCE(SUM(rt.total_rooms), 0) as total_rooms
                FROM hotels h
                LEFT JOIN room_types rt ON h.property_id = rt.property_id
                GROUP BY h.property_id, h.hotel_name, h.star_rating, h.city_name, h.country_name
            """).fetchall()
            
            result = []
            for hotel in hotels:
                # Get active bookings count using property_id
                active_bookings = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM bookings 
                    WHERE property_id = ? 
                    AND booking_status NOT IN ('CANCELLED', 'NO_SHOW')
                    AND check_out_date >= date('now')
                """, (hotel['property_id'],)).fetchone()['count']
                
                result.append({
                    "property_id": hotel['property_id'],
                    "hotel_name": hotel['hotel_name'],
                    "star_rating": hotel['star_rating'],
                    "city_name": hotel['city_name'],
                    "country_name": hotel['country_name'],
                    "room_types_count": hotel['room_types_count'],
                    "total_rooms": hotel['total_rooms'],
                    "active_bookings": active_bookings
                })
            
            return result
        finally:
            conn.close()
    
    def get_hotel_dashboard_data(self, property_id: str) -> Dict:
        """Get complete dashboard data for a specific hotel"""
        conn = self.get_db_connection()
        try:
            # Get hotel basic info
            hotel = conn.execute("""
                SELECT * FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Get room types
            room_types = conn.execute("""
                SELECT * FROM room_types WHERE property_id = ?
            """, (property_id,)).fetchall()
            
            # Get recent bookings (last 30 days) using property_id
            recent_bookings = conn.execute("""
                SELECT b.*, rt.room_name
                FROM bookings b
                LEFT JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE b.property_id = ? 
                AND b.booked_at >= date('now', '-30 days')
                ORDER BY b.booked_at DESC
            """, (property_id,)).fetchall()
            
            # Get analytics data
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            analytics = self.calculate_analytics(property_id, thirty_days_ago, today, conn)
            
            return {
                "success": True,
                "hotel": dict(hotel),
                "room_types": [dict(rt) for rt in room_types],
                "recent_bookings": [dict(b) for b in recent_bookings],
                "analytics": analytics
            }
        finally:
            conn.close()
    
    def get_inventory_calendar(self, property_id: str, start_date: str, days: int = 30) -> Dict:
        """Get inventory calendar data optimized for timeline display"""
        conn = self.get_db_connection()
        try:
            # Get hotel info
            hotel = conn.execute("""
                SELECT hotel_name FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Get room types
            room_types = conn.execute("""
                SELECT * FROM room_types WHERE property_id = ?
            """, (property_id,)).fetchall()
            
            # Calculate end date
            start = datetime.strptime(start_date, '%Y-%m-%d')
            dates = [(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
            
            # Get inventory data for all room types and dates
            inventory_data = {}
            for room_type in room_types:
                room_type_id = room_type['room_type_id']
                inventory_data[room_type_id] = {}
                
                # Get existing inventory records
                inventory_records = conn.execute("""
                    SELECT stay_date, available_rooms, current_price 
                    FROM room_inventory 
                    WHERE room_type_id = ? AND stay_date BETWEEN ? AND ?
                """, (room_type_id, dates[0], dates[-1])).fetchall()
                
                # Create inventory map
                inventory_map = {inv['stay_date']: dict(inv) for inv in inventory_records}
                
                # Fill in all dates with default values if missing
                for date in dates:
                    if date in inventory_map:
                        inventory_data[room_type_id][date] = inventory_map[date]
                    else:
                        inventory_data[room_type_id][date] = {
                            'available_rooms': room_type['total_rooms'],
                            'current_price': room_type['base_price_per_night']
                        }
            
            return {
                "success": True,
                "hotel_name": hotel['hotel_name'],
                "room_types": [dict(rt) for rt in room_types],
                "inventory_data": inventory_data,
                "dates": dates,
                "start_date": start_date,
                "days": days
            }
        finally:
            conn.close()
    
    def get_bookings_calendar(self, property_id: str, start_date: str, days: int = 30) -> Dict:
        """Get bookings calendar data optimized for timeline display"""
        conn = self.get_db_connection()
        try:
            # Get hotel info
            hotel = conn.execute("""
                SELECT hotel_name FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Get room types
            room_types = conn.execute("""
                SELECT * FROM room_types WHERE property_id = ?
            """, (property_id,)).fetchall()
            
            # Calculate date range
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = start + timedelta(days=days)
            dates = [(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
            
            # Get all bookings that overlap with our date range using property_id and join with room_types
            bookings = conn.execute("""
                SELECT b.*, rt.room_name
                FROM bookings b
                LEFT JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE b.property_id = ? 
                AND b.check_in_date < ? 
                AND b.check_out_date > ?
                AND b.booking_status NOT IN ('CANCELLED', 'NO_SHOW')
                ORDER BY b.check_in_date
            """, (property_id, end.strftime('%Y-%m-%d'), start_date)).fetchall()
            
            # Organize bookings by room type and date
            bookings_by_room_and_date = {}
            
            # Initialize structure
            for room_type in room_types:
                room_name = room_type['room_name']
                bookings_by_room_and_date[room_name] = {}
                for date in dates:
                    bookings_by_room_and_date[room_name][date] = []
            
            # Fill in bookings
            for booking in bookings:
                room_name = booking['room_name']
                if room_name and room_name in bookings_by_room_and_date:
                    check_in = datetime.strptime(booking['check_in_date'], '%Y-%m-%d')
                    check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
                    
                    # Add booking to all dates it spans within our range
                    current_date = max(start, check_in)
                    end_date = min(end, check_out)
                    
                    while current_date < end_date:
                        date_str = current_date.strftime('%Y-%m-%d')
                        if date_str in dates:
                            bookings_by_room_and_date[room_name][date_str].append(dict(booking))
                        current_date += timedelta(days=1)
            
            return {
                "success": True,
                "hotel_name": hotel['hotel_name'],
                "room_types": [dict(rt) for rt in room_types],
                "bookings_by_room_and_date": bookings_by_room_and_date,
                "dates": dates,
                "start_date": start_date,
                "days": days
            }
        finally:
            conn.close()
    
    def calculate_analytics(self, property_id: str, start_date: str, end_date: str, conn) -> Dict:
        """Calculate analytics for the dashboard using property_id"""
        # Total bookings
        total_bookings = conn.execute("""
            SELECT COUNT(*) as count FROM bookings 
            WHERE property_id = ? AND booked_at BETWEEN ? AND ?
        """, (property_id, start_date, end_date)).fetchone()['count']
        
        # Revenue calculation
        revenue_data = conn.execute("""
            SELECT 
                SUM(total_price) as total_revenue,
                COUNT(*) as booking_count,
                AVG(total_price) as avg_per_booking
            FROM bookings 
            WHERE property_id = ? 
            AND booking_status NOT IN ('CANCELLED', 'NO_SHOW')
            AND booked_at BETWEEN ? AND ?
        """, (property_id, start_date, end_date)).fetchone()
        
        # Occupancy calculation (simplified - could be more sophisticated)
        total_room_nights = conn.execute("""
            SELECT COALESCE(SUM(rt.total_rooms), 0) as total_rooms
            FROM hotels h
            LEFT JOIN room_types rt ON h.property_id = rt.property_id
            WHERE h.property_id = ?
        """, (property_id,)).fetchone()['total_rooms']
        
        booked_room_nights = conn.execute("""
            SELECT COALESCE(SUM(nights * rooms_booked), 0) as booked_nights
            FROM bookings 
            WHERE property_id = ? 
            AND booking_status NOT IN ('CANCELLED', 'NO_SHOW')
            AND check_in_date BETWEEN ? AND ?
        """, (property_id, start_date, end_date)).fetchone()['booked_nights']
        
        days_in_period = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        total_available_nights = total_room_nights * days_in_period if total_room_nights and days_in_period > 0 else 1
        
        occupancy_rate = booked_room_nights / total_available_nights if total_available_nights > 0 else 0
        
        # Room status counts for today
        room_status_counts = conn.execute("""
            SELECT room_status, COUNT(*) as count
            FROM rooms 
            WHERE property_id = ? AND is_active = 1
            GROUP BY room_status
        """, (property_id,)).fetchall()
        
        # Convert to dictionary
        status_counts = {status['room_status']: status['count'] for status in room_status_counts}
        
        # Calculate available rooms (clean_vacant + dirty_vacant)
        available_rooms = status_counts.get('CLEAN_VACANT', 0) + status_counts.get('DIRTY_VACANT', 0)
        occupied_rooms = status_counts.get('OCCUPIED', 0)
        reserved_rooms = status_counts.get('RESERVED', 0)
        out_of_order_rooms = status_counts.get('OUT_OF_ORDER', 0)
        
        # Today's check-ins and check-outs
        today = datetime.now().strftime('%Y-%m-%d')
        
        todays_checkins = conn.execute("""
            SELECT COUNT(*) as count FROM bookings 
            WHERE property_id = ? AND check_in_date = ? 
            AND booking_status = 'CONFIRMED'
        """, (property_id, today)).fetchone()['count']
        
        todays_checkouts = conn.execute("""
            SELECT COUNT(*) as count FROM bookings 
            WHERE property_id = ? AND check_out_date = ? 
            AND booking_status = 'CHECKED_IN'
        """, (property_id, today)).fetchone()['count']

        return {
            "bookings": {
                "total": total_bookings
            },
            "revenue": {
                "total": revenue_data['total_revenue'] or 0,
                "average_per_booking": revenue_data['avg_per_booking'] or 0
            },
            "occupancy": {
                "rate": min(occupancy_rate, 1.0),  # Cap at 100%
                "booked_nights": booked_room_nights,
                "total_nights": total_available_nights
            },
            "rooms": {
                "available_rooms": available_rooms,
                "occupied_rooms": occupied_rooms,
                "reserved_rooms": reserved_rooms,
                "out_of_order_rooms": out_of_order_rooms,
                "total_rooms": sum(status_counts.values())
            },
            "daily": {
                "todays_checkins": todays_checkins,
                "todays_checkouts": todays_checkouts
            }
        }

# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🏨 Dashboard API starting up...")
    # Only initialize if tables don't exist
    check_and_initialize_tables()
    yield
    # Shutdown
    print("🏨 Dashboard API shutting down...")

def check_and_initialize_tables():
    """Check if tables exist and initialize only if needed"""
    conn = sqlite3.connect("ella.db")
    cursor = conn.cursor()
    
    # Check if rooms table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
    rooms_table_exists = cursor.fetchone() is not None
    
    # Check if room_assignments table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='room_assignments'")
    assignments_table_exists = cursor.fetchone() is not None
    
    if not rooms_table_exists or not assignments_table_exists:
        print("🏨 Creating missing tables...")
        create_tables(cursor)
        conn.commit()
        
        # Only populate if rooms table was just created
        if not rooms_table_exists:
            print("🏨 Populating rooms table with individual room numbers...")
            populate_rooms_for_hotels(conn, cursor)
    else:
        # Add cleanliness_status column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE rooms ADD COLUMN cleanliness_status VARCHAR(20) DEFAULT 'CLEAN'")
            # Convert existing room_status to cleanliness_status
            cursor.execute("""
                UPDATE rooms SET cleanliness_status = CASE 
                    WHEN room_status = 'CLEAN_VACANT' THEN 'CLEAN'
                    WHEN room_status = 'DIRTY_VACANT' THEN 'DIRTY'
                    WHEN room_status = 'MAINTENANCE' THEN 'MAINTENANCE'
                    WHEN room_status = 'OUT_OF_ORDER' THEN 'OUT_OF_ORDER'
                    ELSE 'CLEAN'
                END
            """)
            conn.commit()
            print("✅ Added cleanliness_status column and migrated data!")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        # Tables exist, just check if rooms need population (only if completely empty)
        cursor.execute("SELECT COUNT(*) FROM rooms")
        room_count = cursor.fetchone()[0]
        
        if room_count == 0:
            print("🏨 Rooms table is empty, populating with room numbers...")
            populate_rooms_for_hotels(conn, cursor)
    
    conn.close()

def create_tables(cursor):
    """Create the rooms and room_assignments tables"""
    # Create rooms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id VARCHAR(20) PRIMARY KEY,
            property_id VARCHAR(200) NOT NULL,
            room_type_id VARCHAR(200) NOT NULL,
            room_number VARCHAR(10) NOT NULL,
            floor INTEGER NOT NULL,
            room_status VARCHAR(20) DEFAULT 'CLEAN_VACANT',
            is_active BOOLEAN DEFAULT 1,
            maintenance_notes TEXT,
            last_cleaned DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES hotels(property_id),
            FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id)
        )
    """)
    
    # Create room_assignments table for tracking guest assignments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id VARCHAR(200) NOT NULL,
            room_id VARCHAR(20) NOT NULL,
            property_id VARCHAR(200) NOT NULL,
            guest_name VARCHAR(200),
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            assignment_status VARCHAR(20) DEFAULT 'ASSIGNED',
            checked_in_at DATETIME,
            checked_out_at DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id),
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
            FOREIGN KEY (property_id) REFERENCES hotels(property_id)
        )
    """)

def populate_rooms_for_hotels(conn, cursor):
    """Populate individual rooms based on room types"""
    
    # Get all room types
    cursor.execute("SELECT * FROM room_types WHERE is_active = 1")
    room_types = cursor.fetchall()
    
    for room_type in room_types:
        property_id = room_type[1]  # property_id
        room_type_id = room_type[0]  # room_type_id
        room_name = room_type[2]     # room_name
        total_rooms = room_type[11]  # total_rooms
        
        print(f"  Creating {total_rooms} rooms for {room_name} at {property_id}")
        
        # Generate room numbers based on room type
        if "deluxe" in room_name.lower() and "king" in room_name.lower():
            # Deluxe King rooms: floors 10-15, rooms 01-10 per floor
            start_room = 1001
        elif "twin" in room_name.lower():
            # Twin rooms: floors 8-9, rooms 01-15 per floor  
            start_room = 801
        else:
            # Standard rooms: floors 2-7, rooms 01-20 per floor
            start_room = 201
            
        # Create individual rooms
        for i in range(total_rooms):
            room_number = str(start_room + i)
            floor = int(room_number[0:2]) if len(room_number) >= 3 else int(room_number[0])
            
            room_id = f"{property_id}_{room_number}"
            
            cursor.execute("""
                INSERT INTO rooms (room_id, property_id, room_type_id, room_number, floor, room_status)
                VALUES (?, ?, ?, ?, ?, 'CLEAN_VACANT')
            """, (room_id, property_id, room_type_id, room_number, floor))
    
    conn.commit()
    print("✅ Rooms populated successfully!")

app = FastAPI(
    title="LEON Dashboard API",
    description="Unified API service for hotel dashboard interface",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
dashboard_service = DashboardService()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "LEON Dashboard API", "status": "running", "version": "1.0.0"}

@app.get("/api/dashboard/hotels")
async def get_hotels():
    """Get all hotels with summary statistics"""
    try:
        hotels = dashboard_service.get_hotels_summary()
        return {"success": True, "hotels": hotels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}")
async def get_hotel_dashboard(property_id: str):
    """Get complete dashboard data for a specific hotel"""
    try:
        data = dashboard_service.get_hotel_dashboard_data(property_id)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/inventory-calendar")
async def get_inventory_calendar(
    property_id: str, 
    start_date: str,
    days: int = 30
):
    """Get inventory calendar data for timeline display"""
    try:
        # Validate date format
        datetime.strptime(start_date, '%Y-%m-%d')
        data = dashboard_service.get_inventory_calendar(property_id, start_date, days)
        return data
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/bookings-calendar")
async def get_bookings_calendar(
    property_id: str, 
    start_date: str,
    days: int = 30
):
    """Get bookings calendar data for timeline display"""
    try:
        # Validate date format
        datetime.strptime(start_date, '%Y-%m-%d')
        data = dashboard_service.get_bookings_calendar(property_id, start_date, days)
        return data
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/analytics")
async def get_analytics(
    property_id: str,
    days: int = 30
):
    """Get analytics data for a hotel"""
    try:
        conn = dashboard_service.get_db_connection()
        try:
            hotel = conn.execute("""
                SELECT hotel_name FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            analytics = dashboard_service.calculate_analytics(
                property_id, start_date, end_date, conn
            )
            
            return {"success": True, "analytics": analytics}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Check-in Management Endpoints

@app.get("/api/dashboard/hotels/{property_id}/rooms")
async def get_hotel_rooms(property_id: str, room_status: str = None):
    """Get all rooms for a hotel with optional status filter"""
    try:
        conn = dashboard_service.get_db_connection()
        try:
            hotel = conn.execute("""
                SELECT hotel_name FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Build query with optional status filter
            query = """
                SELECT r.*, rt.room_name, rt.bed_type, rt.max_occupancy,
                       ra.guest_name, ra.check_in_date, ra.check_out_date, ra.assignment_status,
                       ra.checked_in_at, b.booking_id, b.booking_status
                FROM rooms r
                LEFT JOIN room_types rt ON r.room_type_id = rt.room_type_id
                LEFT JOIN room_assignments ra ON r.room_id = ra.room_id 
                    AND ra.assignment_status IN ('ASSIGNED', 'CHECKED_IN')
                    AND ra.check_in_date <= date('now') 
                    AND ra.check_out_date > date('now')
                LEFT JOIN bookings b ON ra.booking_id = b.booking_id
                WHERE r.property_id = ?
            """
            params = [property_id]
            
            if room_status:
                query += " AND r.room_status = ?"
                params.append(room_status)
                
            query += " ORDER BY r.floor, r.room_number"
            
            rooms = conn.execute(query, params).fetchall()
            
            # Organize rooms by floor for better display
            rooms_by_floor = {}
            for room in rooms:
                floor = room['floor']
                if floor not in rooms_by_floor:
                    rooms_by_floor[floor] = []
                rooms_by_floor[floor].append(dict(room))
            
            return {
                "success": True,
                "rooms": [dict(room) for room in rooms],
                "rooms_by_floor": rooms_by_floor
            }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/pending-checkins")
async def get_pending_check_ins(property_id: str, date: str = None):
    """Get bookings that need room assignment or check-in for a specific date"""
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
            
        conn = dashboard_service.get_db_connection()
        try:
            # Get bookings scheduled for check-in that need attention
            pending_checkins = conn.execute("""
                SELECT b.*, rt.room_name, ra.room_id, r.room_number, ra.assignment_status, ra.checked_in_at
                FROM bookings b
                LEFT JOIN room_types rt ON b.room_type_id = rt.room_type_id
                LEFT JOIN room_assignments ra ON b.booking_id = ra.booking_id
                LEFT JOIN rooms r ON ra.room_id = r.room_id
                WHERE b.property_id = ?
                AND b.check_in_date = ?
                AND b.booking_status = 'CONFIRMED'
                ORDER BY 
                    CASE 
                        WHEN ra.assignment_status IS NULL THEN 1  -- Need room assignment
                        WHEN ra.assignment_status = 'ASSIGNED' THEN 2  -- Need check-in
                        ELSE 3  -- Already checked in
                    END,
                    b.guest_name
            """, (property_id, date)).fetchall()
            
            return {
                "success": True,
                "date": date,
                "pending_checkins": [dict(check_in) for check_in in pending_checkins]
            }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/hotels/{property_id}/assign-room")
async def assign_room(property_id: str, assignment_data: Dict):
    """Assign a specific room to a booking with comprehensive validation"""
    try:
        booking_id = assignment_data.get('booking_id')
        room_id = assignment_data.get('room_id')
        notes = assignment_data.get('notes', '')
        
        if not booking_id or not room_id:
            raise HTTPException(status_code=400, detail="booking_id and room_id are required")
        
        conn = dashboard_service.get_db_connection()
        try:
            # Start transaction
            conn.execute("BEGIN")
            
            # Verify booking exists and is in correct status
            booking = conn.execute("""
                SELECT * FROM bookings 
                WHERE booking_id = ? AND property_id = ? 
                AND booking_status = ?
            """, (booking_id, property_id, BookingStatus.CONFIRMED)).fetchone()
            
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found or not in confirmed status")
            
            # Note: We skip date validation for room assignments since we're working with existing bookings
            # The booking dates were already validated when the booking was created
            
            # Verify room exists and get details
            room = conn.execute("""
                SELECT r.*, rt.max_occupancy, rt.room_name
                FROM rooms r
                JOIN room_types rt ON r.room_type_id = rt.room_type_id
                WHERE r.room_id = ? AND r.property_id = ? AND r.is_active = 1
            """, (room_id, property_id)).fetchone()
            
            if not room:
                raise HTTPException(status_code=404, detail="Room not found or inactive")
            
            # Validate room can accommodate the booking
            num_guests = booking['rooms_booked'] if booking['rooms_booked'] is not None else 1
            if num_guests > room['max_occupancy']:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Room {room['room_number']} can only accommodate {room['max_occupancy']} guests, but booking is for {num_guests} guests"
                )
            
            # Check room availability for the dates (this is the only check we need)
            # Room status at the room level is less important than actual date conflicts
            is_available, availability_message = dashboard_service.check_room_availability(
                room_id, booking['check_in_date'], booking['check_out_date']
            )
            if not is_available:
                raise HTTPException(status_code=409, detail=availability_message)
            
            # Check if booking already has a room assignment
            existing_assignment = conn.execute("""
                SELECT * FROM room_assignments 
                WHERE booking_id = ? AND assignment_status IN (?, ?)
            """, (booking_id, AssignmentStatus.ASSIGNED, AssignmentStatus.CHECKED_IN)).fetchone()
            
            # If booking is already assigned to the SAME room, reject
            if existing_assignment and existing_assignment['room_id'] == room_id:
                raise HTTPException(status_code=400, detail="Booking is already assigned to this room")
            
            # If booking is assigned to a DIFFERENT room, handle reassignment
            if existing_assignment:
                old_room_id = existing_assignment['room_id']
                
                # Get old room info
                old_room = conn.execute("""
                    SELECT room_number, room_status FROM rooms WHERE room_id = ?
                """, (old_room_id,)).fetchone()
                
                # Cancel existing assignment
                conn.execute("""
                    UPDATE room_assignments 
                    SET assignment_status = ?, notes = ?
                    WHERE booking_id = ? AND assignment_status IN (?, ?)
                """, (
                    AssignmentStatus.CANCELLED, 
                    f"Reassigned from Room {old_room['room_number']} to Room {room['room_number']}", 
                    booking_id, 
                    AssignmentStatus.ASSIGNED, 
                    AssignmentStatus.CHECKED_IN
                ))
                
                # Don't change room status during reassignment - room status is independent of bookings
            
            # Create room assignment with proper audit trail
            assignment_id = conn.execute("""
                INSERT INTO room_assignments 
                (booking_id, room_id, property_id, guest_name, check_in_date, check_out_date, assignment_status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING assignment_id
            """, (
                booking_id, room_id, property_id, booking['guest_name'], 
                booking['check_in_date'], booking['check_out_date'], 
                AssignmentStatus.ASSIGNED, notes
            )).fetchone()[0]
            
            # Keep the room's base status unchanged - room assignments are tracked separately
            # The room status should only change for housekeeping/maintenance reasons, not bookings
            
            # Update booking status if needed
            conn.execute("""
                UPDATE bookings 
                SET booking_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE booking_id = ?
            """, (BookingStatus.CONFIRMED, booking_id))
            
            conn.commit()
            
            # Determine if this was a reassignment or new assignment
            action_type = "reassigned to" if existing_assignment else "assigned to"
            old_room_info = f" (moved from Room {old_room['room_number']})" if existing_assignment else ""
            
            return {
                "success": True, 
                "message": f"{booking['guest_name']} successfully {action_type} Room {room['room_number']}{old_room_info}",
                "assignment_id": assignment_id,
                "room_number": room['room_number'],
                "guest_name": booking['guest_name'],
                "is_reassignment": bool(existing_assignment),
                "old_room_number": old_room['room_number'] if existing_assignment else None
            }
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/dashboard/hotels/{property_id}/room-assignments")
async def get_room_assignments(property_id: str, status: str = None):
    """Get all room assignments for the property"""
    try:
        conn = dashboard_service.get_db_connection()
        try:
            # Build query with optional status filter
            query = """
                SELECT ra.*, b.guest_name, b.guest_email, b.guest_phone, 
                       b.check_in_date, b.check_out_date, b.rooms_booked,
                       r.room_number, r.room_status, r.floor, 
                       rt.room_name, rt.bed_type, rt.max_occupancy
                FROM room_assignments ra
                JOIN bookings b ON ra.booking_id = b.booking_id
                JOIN rooms r ON ra.room_id = r.room_id
                JOIN room_types rt ON r.room_type_id = rt.room_type_id
                WHERE ra.property_id = ?
            """
            params = [property_id]
            
            if status:
                query += " AND ra.assignment_status = ?"
                params.append(status)
            
            query += " ORDER BY ra.check_in_date ASC, r.room_number ASC"
            
            assignments = conn.execute(query, params).fetchall()
            
            assignments_list = []
            for assignment in assignments:
                assignments_list.append({
                    "assignment_id": assignment['assignment_id'],
                    "booking_id": assignment['booking_id'],
                    "room_id": assignment['room_id'],
                    "room_number": assignment['room_number'],
                    "room_name": assignment['room_name'],
                    "floor": assignment['floor'],
                    "bed_type": assignment['bed_type'],
                    "max_occupancy": assignment['max_occupancy'],
                    "room_status": assignment['room_status'],
                    "guest_name": assignment['guest_name'],
                    "guest_email": assignment['guest_email'],
                    "guest_phone": assignment['guest_phone'],
                    "check_in_date": assignment['check_in_date'],
                    "check_out_date": assignment['check_out_date'],
                    "rooms_booked": assignment['rooms_booked'],
                    "assignment_status": assignment['assignment_status'],
                    "checked_in_at": assignment['checked_in_at'],
                    "checked_out_at": assignment['checked_out_at'],
                    "notes": assignment['notes']
                })
            
            return {
                "success": True,
                "assignments": assignments_list,
                "total": len(assignments_list)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/dashboard/hotels/{property_id}/check-in")
async def check_in_guest(property_id: str, checkin_data: Dict):
    """Check in a guest to their assigned room with comprehensive validation"""
    try:
        booking_id = checkin_data.get('booking_id')
        checkin_notes = checkin_data.get('notes', '')
        early_checkin = checkin_data.get('early_checkin', False)
        
        if not booking_id:
            raise HTTPException(status_code=400, detail="booking_id is required")
        
        conn = dashboard_service.get_db_connection()
        try:
            # Start transaction
            conn.execute("BEGIN")
            
            # Get the room assignment with full details
            assignment = conn.execute("""
                SELECT ra.*, b.guest_name, b.check_in_date, b.check_out_date, b.rooms_booked,
                       r.room_number, r.room_status, r.floor, rt.room_name
                FROM room_assignments ra
                JOIN bookings b ON ra.booking_id = b.booking_id
                JOIN rooms r ON ra.room_id = r.room_id
                JOIN room_types rt ON r.room_type_id = rt.room_type_id
                WHERE ra.booking_id = ? AND ra.property_id = ?
                AND ra.assignment_status = ?
            """, (booking_id, property_id, AssignmentStatus.ASSIGNED)).fetchone()
            
            if not assignment:
                raise HTTPException(status_code=404, detail="No room assignment found for this booking or guest already checked in")
            
            # Validate check-in date
            today = datetime.now().date()
            checkin_date = datetime.strptime(assignment['check_in_date'], '%Y-%m-%d').date()
            
            if checkin_date > today and not early_checkin:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Check-in date is {checkin_date}. To check in early, set early_checkin=true"
                )
            
            if checkin_date < today - timedelta(days=1):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Check-in date {checkin_date} is too far in the past"
                )
            
            # Validate room status
            if assignment['room_status'] != RoomStatus.RESERVED:
                if assignment['room_status'] == RoomStatus.DIRTY_VACANT:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Room {assignment['room_number']} is dirty and needs housekeeping before check-in"
                    )
                elif assignment['room_status'] == RoomStatus.OUT_OF_ORDER:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Room {assignment['room_number']} is out of order and cannot be used"
                    )
                else:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Room {assignment['room_number']} status is {assignment['room_status']}, cannot check in"
                    )
            
            # Validate room status transition
            old_status = assignment['room_status']
            new_status = RoomStatus.OCCUPIED
            
            if not dashboard_service.validate_room_status_transition(old_status, new_status):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot change room status from {old_status} to {new_status}"
                )
            
            # Update assignment as checked in
            conn.execute("""
                UPDATE room_assignments 
                SET assignment_status = ?, checked_in_at = CURRENT_TIMESTAMP, notes = ?
                WHERE booking_id = ? AND property_id = ?
            """, (AssignmentStatus.CHECKED_IN, checkin_notes, booking_id, property_id))
            
            # Update room status to occupied
            conn.execute("""
                UPDATE rooms 
                SET room_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE room_id = ?
            """, (new_status, assignment['room_id']))
            
            # Update booking status
            conn.execute("""
                UPDATE bookings 
                SET booking_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE booking_id = ?
            """, (BookingStatus.CHECKED_IN, booking_id))
            
            conn.commit()
            
            # Prepare check-in confirmation details
            guest_count = assignment['rooms_booked'] if assignment['rooms_booked'] is not None else 1
            
            return {
                "success": True, 
                "message": f"Guest {assignment['guest_name']} successfully checked in",
                "details": {
                    "guest_name": assignment['guest_name'],
                    "room_number": assignment['room_number'],
                    "floor": assignment['floor'],
                    "room_type": assignment['room_name'],
                    "guest_count": guest_count,
                    "check_in_date": assignment['check_in_date'],
                    "check_out_date": assignment['check_out_date'],
                    "checked_in_at": datetime.now().isoformat(),
                    "early_checkin": early_checkin if checkin_date > today else False
                }
            }
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/dashboard/hotels/{property_id}/check-out")
async def check_out_guest(property_id: str, checkout_data: Dict):
    """Check out a guest and mark room as vacant"""
    try:
        room_id = checkout_data.get('room_id')
        booking_id = checkout_data.get('booking_id')
        
        if not room_id:
            raise HTTPException(status_code=400, detail="room_id is required")
        
        conn = dashboard_service.get_db_connection()
        try:
            # Update assignment as checked out
            conn.execute("""
                UPDATE room_assignments 
                SET assignment_status = 'CHECKED_OUT', checked_out_at = CURRENT_TIMESTAMP
                WHERE room_id = ? AND property_id = ? AND assignment_status = 'CHECKED_IN'
            """, (room_id, property_id))
            
            # Update room cleanliness to dirty (needs cleaning after checkout)
            conn.execute("""
                UPDATE rooms 
                SET cleanliness_status = ?, room_status = 'DIRTY_VACANT', updated_at = CURRENT_TIMESTAMP
                WHERE room_id = ?
            """, (CleanlinessStatus.DIRTY, room_id))
            
            # Update booking status if booking_id provided
            if booking_id:
                conn.execute("""
                    UPDATE bookings 
                    SET booking_status = 'CHECKED_OUT'
                    WHERE booking_id = ?
                """, (booking_id,))
            
            conn.commit()
            
            return {"success": True, "message": "Guest checked out successfully"}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/hotels/{property_id}/update-room-status")
async def update_room_status(property_id: str, room_data: Dict):
    """Update room status with proper validation and business rules"""
    try:
        room_id = room_data.get('room_id')
        new_status = room_data.get('room_status')
        notes = room_data.get('notes', '')
        force_update = room_data.get('force_update', False)
        
        if not room_id or not new_status:
            raise HTTPException(status_code=400, detail="room_id and room_status are required")
        
        # Validate status enum
        try:
            new_status_enum = RoomStatus(new_status)
        except ValueError:
            valid_statuses = [status.value for status in RoomStatus]
            raise HTTPException(status_code=400, detail=f"Invalid room status. Must be one of: {', '.join(valid_statuses)}")
        
        conn = dashboard_service.get_db_connection()
        try:
            # Start transaction
            conn.execute("BEGIN")
            
            # Initialize message suffix for auto-checkout scenarios
            message_suffix = ""
            
            # Get current room status and details
            room = conn.execute("""
                SELECT r.*, rt.room_name
                FROM rooms r
                JOIN room_types rt ON r.room_type_id = rt.room_type_id
                WHERE r.room_id = ? AND r.property_id = ? AND r.is_active = 1
            """, (room_id, property_id)).fetchone()
            
            if not room:
                raise HTTPException(status_code=404, detail="Room not found or inactive")
            
            current_status = room['room_status']
            
            # Skip if status is already the same
            if current_status == new_status:
                return {"success": True, "message": f"Room {room['room_number']} is already {new_status}"}
            
            # Validate status transition unless forced
            if not force_update and not dashboard_service.validate_room_status_transition(current_status, new_status):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot change room status from {current_status} to {new_status}. Use force_update=true to override."
                )
            
            # Special business rule validations
            if new_status == RoomStatus.OCCUPIED:
                # Check if room has an active assignment
                active_assignment = conn.execute("""
                    SELECT * FROM room_assignments 
                    WHERE room_id = ? AND assignment_status = ?
                """, (room_id, AssignmentStatus.CHECKED_IN)).fetchone()
                
                if not active_assignment and not force_update:
                    raise HTTPException(
                        status_code=400, 
                        detail="Cannot set room to OCCUPIED without an active guest assignment. Use force_update=true to override."
                    )
            
            elif new_status in [RoomStatus.CLEAN_VACANT, RoomStatus.DIRTY_VACANT]:
                # Check if there's an active guest
                active_assignment = conn.execute("""
                    SELECT * FROM room_assignments 
                    WHERE room_id = ? AND assignment_status IN (?, ?)
                """, (room_id, AssignmentStatus.ASSIGNED, AssignmentStatus.CHECKED_IN)).fetchone()
                
                if active_assignment:
                    if current_status == RoomStatus.OCCUPIED and not force_update:
                        # Auto-checkout guest when changing OCCUPIED room to VACANT
                        conn.execute("""
                            UPDATE room_assignments 
                            SET assignment_status = ?, checked_out_at = CURRENT_TIMESTAMP,
                                notes = COALESCE(notes || '; ', '') || 'Auto-checkout via room status change'
                            WHERE assignment_id = ?
                        """, (AssignmentStatus.CHECKED_OUT, active_assignment['assignment_id']))
                        
                        # Also update the booking status
                        if active_assignment['booking_id']:
                            conn.execute("""
                                UPDATE bookings 
                                SET booking_status = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE booking_id = ?
                            """, (BookingStatus.CHECKED_OUT, active_assignment['booking_id']))
                        
                        message_suffix = f" (guest {active_assignment['guest_name']} automatically checked out)"
                    elif not force_update:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Cannot change room status to {new_status} - guest {active_assignment['guest_name']} is assigned. Complete check-out first or use force_update=true."
                        )
            
            # Update room status
            conn.execute("""
                UPDATE rooms 
                SET room_status = ?, maintenance_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE room_id = ?
            """, (new_status, notes, room_id))
            
            # Special actions for certain status changes
            if new_status == RoomStatus.CLEAN_VACANT:
                # Update last_cleaned timestamp
                conn.execute("""
                    UPDATE rooms 
                    SET last_cleaned = CURRENT_TIMESTAMP
                    WHERE room_id = ?
                """, (room_id,))
                
            elif new_status in [RoomStatus.OUT_OF_ORDER, RoomStatus.MAINTENANCE]:
                # Cancel any future assignments if forcing status change
                if force_update:
                    future_assignments = conn.execute("""
                        SELECT * FROM room_assignments 
                        WHERE room_id = ? AND assignment_status = ? 
                        AND check_in_date > date('now')
                    """, (room_id, AssignmentStatus.ASSIGNED)).fetchall()
                    
                    for assignment in future_assignments:
                        conn.execute("""
                            UPDATE room_assignments 
                            SET assignment_status = ?, notes = ?
                            WHERE assignment_id = ?
                        """, (AssignmentStatus.CANCELLED, f"Room taken out of service: {notes}", assignment['assignment_id']))
            
            conn.commit()
            
            # Prepare response message
            status_messages = {
                RoomStatus.CLEAN_VACANT: "ready for new guests",
                RoomStatus.DIRTY_VACANT: "marked for housekeeping",
                RoomStatus.OUT_OF_ORDER: "taken out of service",
                RoomStatus.MAINTENANCE: "scheduled for maintenance",
                RoomStatus.BLOCKED: "administratively blocked",
                RoomStatus.OCCUPIED: "marked as occupied",
                RoomStatus.RESERVED: "reserved for incoming guest"
            }
            
            base_message = f"Room {room['room_number']} status updated to {new_status} - {status_messages.get(new_status, new_status)}"
            message = base_message + message_suffix
            
            return {
                "success": True, 
                "message": message,
                "room_number": room['room_number'],
                "old_status": current_status,
                "new_status": new_status,
                "forced": force_update
            }
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.put("/api/dashboard/hotels/{property_id}/bookings/{booking_id}")
async def update_booking(property_id: str, booking_id: str, booking_data: Dict):
    """Update an existing booking with validation"""

    try:
        conn = dashboard_service.get_db_connection()
        try:
            # Start transaction
            conn.execute("BEGIN")
            
            # Verify booking exists and belongs to this property
            existing_booking = conn.execute("""
                SELECT * FROM bookings 
                WHERE booking_id = ? AND property_id = ?
            """, (booking_id, property_id)).fetchone()
            
            if not existing_booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            
            # Validate booking status - only allow updates for certain statuses
            if existing_booking['booking_status'] in ['CHECKED_OUT', 'CANCELLED']:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot update booking with status {existing_booking['booking_status']}"
                )
            
            # Extract update fields
            guest_name = booking_data.get('guestName')
            guest_email = booking_data.get('guestEmail', '')
            guest_phone = booking_data.get('guestPhone', '')
            check_in_date = booking_data.get('checkinDate')
            check_out_date = booking_data.get('checkoutDate')
            room_type = booking_data.get('roomType', '')
            rooms_booked = int(booking_data.get('guests', 1))  # Map guests to rooms_booked
            total_amount = float(booking_data.get('totalAmount', 0)) if booking_data.get('totalAmount') else existing_booking['total_price']
            special_requests = booking_data.get('notes', '')  # Map notes to special_requests
            
            # Validate required fields
            if not guest_name or not check_in_date or not check_out_date:
                raise HTTPException(status_code=400, detail="Guest name, check-in date, and check-out date are required")
            
            # Validate dates if they changed (allow past dates for existing bookings)
            if check_in_date != existing_booking['check_in_date'] or check_out_date != existing_booking['check_out_date']:
                # For updates, we use a more lenient validation that allows past dates
                try:
                    check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
                    check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
                    
                    # Check-out must be after check-in
                    if check_out <= check_in:
                        raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")
                    
                    # Maximum stay length (e.g., 90 days for updates)
                    max_stay_days = 90
                    if (check_out - check_in).days > max_stay_days:
                        raise HTTPException(status_code=400, detail=f"Maximum stay is {max_stay_days} days")
                        
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format")
                
                # Calculate nights if dates changed
                checkin = datetime.strptime(check_in_date, '%Y-%m-%d')
                checkout = datetime.strptime(check_out_date, '%Y-%m-%d')
                nights = (checkout - checkin).days
            else:
                nights = existing_booking['nights']
            
            # Check if this booking has any room assignments that need updating
            existing_assignments = conn.execute("""
                SELECT assignment_id, room_id, check_in_date, check_out_date, assignment_status
                FROM room_assignments 
                WHERE booking_id = ? AND assignment_status IN (?, ?)
            """, (booking_id, AssignmentStatus.ASSIGNED, AssignmentStatus.CHECKED_IN)).fetchall()
            
            # If dates changed and booking has room assignments, validate and update them
            dates_changed = (check_in_date != existing_booking['check_in_date'] or 
                           check_out_date != existing_booking['check_out_date'])
            
            if dates_changed and existing_assignments:
                # Check for conflicts with new dates for each assigned room
                for assignment in existing_assignments:
                    room_id = assignment['room_id']
                    
                    # Check if the new dates conflict with other bookings for this room
                    is_available, conflict_message = dashboard_service.check_room_availability(
                        room_id, check_in_date, check_out_date, exclude_booking_id=booking_id
                    )
                    
                    if not is_available:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Cannot update dates: {conflict_message}"
                        )
                
                # All rooms are available for new dates, proceed with updates
                # Update all room assignments for this booking
                for assignment in existing_assignments:
                    conn.execute("""
                        UPDATE room_assignments 
                        SET check_in_date = ?, check_out_date = ?, guest_name = ?,
                            notes = COALESCE(notes, '') || ?, updated_at = CURRENT_TIMESTAMP
                        WHERE assignment_id = ?
                    """, (check_in_date, check_out_date, guest_name, 
                          f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Dates updated via booking edit: {special_requests}",
                          assignment['assignment_id']))
            
            # Update the booking
            conn.execute("""
                UPDATE bookings 
                SET guest_name = ?, guest_email = ?, guest_phone = ?,
                    check_in_date = ?, check_out_date = ?, nights = ?,
                    total_price = ?, special_requests = ?, rooms_booked = ?
                WHERE booking_id = ? AND property_id = ?
            """, (guest_name, guest_email, guest_phone, check_in_date, check_out_date, nights,
                  total_amount, special_requests, rooms_booked, booking_id, property_id))
            
            # Commit all changes atomically
            conn.commit()
            
            # Prepare detailed response message
            base_message = f"Booking {booking_id} updated successfully"
            if dates_changed and existing_assignments:
                assignment_count = len(existing_assignments)
                base_message += f" along with {assignment_count} room assignment{'' if assignment_count == 1 else 's'}"
            
            return {
                "success": True,
                "message": base_message,
                "booking_id": booking_id,
                "dates_changed": dates_changed,
                "assignments_updated": len(existing_assignments) if dates_changed else 0
            }
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/dashboard/hotels/{property_id}/available-rooms")
async def get_available_rooms(property_id: str, room_type_id: str, check_in_date: str, check_out_date: str, num_guests: int = 1):
    """Get available rooms for a specific room type and date range with comprehensive validation"""
    try:
        # Validate dates
        dates_valid, date_message = dashboard_service.validate_booking_dates(check_in_date, check_out_date)
        if not dates_valid:
            raise HTTPException(status_code=400, detail=f"Invalid dates: {date_message}")
        
        # Validate guest count
        if num_guests < 1 or num_guests > 10:  # Reasonable limits
            raise HTTPException(status_code=400, detail="Number of guests must be between 1 and 10")
        
        # Get suitable and available rooms
        available_rooms = dashboard_service.get_suitable_rooms(
            property_id, room_type_id, check_in_date, check_out_date, num_guests
        )
        
        # Categorize rooms by status for better selection
        clean_rooms = [room for room in available_rooms if room['room_status'] == RoomStatus.CLEAN_VACANT]
        dirty_rooms = [room for room in available_rooms if room['room_status'] == RoomStatus.DIRTY_VACANT]
        
        return {
            "success": True,
            "total_available": len(available_rooms),
            "available_rooms": available_rooms,
            "clean_rooms": clean_rooms,
            "dirty_rooms": dirty_rooms,
            "recommendations": {
                "preferred": clean_rooms[:3] if clean_rooms else dirty_rooms[:3],  # Top 3 recommendations
                "message": "Clean rooms are ready for immediate check-in" if clean_rooms else "Dirty rooms require housekeeping before check-in"
            },
            "search_criteria": {
                "room_type_id": room_type_id,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "num_guests": num_guests
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "dashboard_api:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    ) 
# 🗄️ Railway PostgreSQL Setup for ELLA Hotel System

## 📋 **Prerequisites**

1. **Railway Account** with active project
2. **Redis service** already added (for memory/sessions)
3. **WhatsApp Business API** configured (optional)

## 🚀 **Step-by-Step Setup**

### **1. Add PostgreSQL Service to Railway**

1. Go to your Railway project dashboard
2. Click **"+ New Service"**
3. Select **"Database"** → **"PostgreSQL"**
4. Railway will automatically provision PostgreSQL and set environment variables

### **2. Verify Environment Variables**

Railway automatically creates these variables:
```
DATABASE_URL=postgresql://user:password@host:port/database
PGHOST=your-postgres-host
PGPORT=5432
PGDATABASE=railway
PGUSER=postgres
PGPASSWORD=your-password
```

### **3. Deploy with Database Setup**

The deployment script (`railway_deploy.py`) will automatically:
- ✅ Detect PostgreSQL environment
- ✅ Create database schema (hotels, rooms, bookings, etc.)
- ✅ Seed sample data (Grand Hyatt KL, Sam Hotel, Marina Court)
- ✅ Start the application

### **4. Test Database Connection**

After deployment, test the database:
```bash
curl https://your-app.up.railway.app/test/database
```

Expected response:
```json
{
  "status": "success",
  "message": "Database connection successful",
  "database_type": "PostgreSQL",
  "environment": "production",
  "test_results": {
    "hotels_found": 3,
    "sample_hotel": "Grand Hyatt Kuala Lumpur",
    "availability_check": true,
    "available_rooms": 2
  }
}
```

## 🏨 **Database Schema**

### **Core Tables:**
- `hotels` - Hotel information (name, location, star rating)
- `hotel_rooms` - Room types and pricing
- `room_availability` - Daily availability and pricing
- `hotel_bookings` - Guest reservations
- `hotel_amenities` - Hotel facilities
- `room_amenities` - Room-specific amenities

### **Media & Analytics:**
- `production_media_files` - Hotel/room photos
- `booking_analytics` - Booking events tracking
- `media_analytics` - Photo view analytics

## 🔧 **Sample Data Included**

### **Hotels:**
1. **Grand Hyatt Kuala Lumpur** (5⭐)
   - Deluxe King Room: RM 450/night
   - Deluxe Twin Room: RM 450/night

2. **Sam Hotel KL** (3⭐)
   - Standard Double Room: RM 120/night

3. **Marina Court Resort Condominium** (4⭐)
   - Ocean View Suite: RM 280/night

### **Availability:**
- ✅ 30 days of availability data
- ✅ Realistic room inventory
- ✅ Dynamic pricing support

## 🧪 **Testing Availability System**

### **Test Hotel Search:**
```bash
curl "https://your-app.up.railway.app/test/whatsapp-message" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a hotel in Kuala Lumpur", "phone": "test_user"}'
```

### **Test Availability Check:**
```bash
curl "https://your-app.up.railway.app/test/whatsapp-message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Check availability for Grand Hyatt on 2024-01-15", "phone": "test_user"}'
```

## 🔄 **Local vs Production**

### **Local Development (SQLite):**
- Uses `ella.db` file
- Automatic fallback when no PostgreSQL detected
- Same schema and functionality

### **Production (PostgreSQL):**
- Uses Railway PostgreSQL service
- Automatic detection via `DATABASE_URL` environment variable
- Better performance and scalability

## 🛠️ **Manual Database Operations**

### **Reset Database:**
```python
python database/postgresql_setup.py
```

### **Check Connection:**
```python
from database.connection import db_manager
print(f"Database type: {'PostgreSQL' if db_manager.is_production else 'SQLite'}")
```

### **Query Hotels:**
```python
from database.connection import search_hotels, check_availability

# Search hotels
hotels = search_hotels("Kuala Lumpur", budget_max=300)

# Check availability
availability = check_availability("Grand Hyatt", "2024-01-15")
```

## 🚨 **Troubleshooting**

### **Database Connection Failed:**
1. Verify PostgreSQL service is added to Railway project
2. Check environment variables are set
3. Ensure Railway PostgreSQL service is running

### **Schema Creation Failed:**
1. Check PostgreSQL permissions
2. Verify database exists
3. Review Railway logs for detailed errors

### **No Sample Data:**
1. Run setup script manually: `python database/postgresql_setup.py`
2. Check for constraint violations
3. Verify table creation succeeded

## 📊 **Monitoring**

### **Health Checks:**
- `/health` - Application health
- `/test/database` - Database connectivity
- `/test/redis` - Redis connectivity

### **Railway Logs:**
Monitor deployment logs for:
- ✅ Database setup completed successfully
- ✅ PostgreSQL connection successful
- ✅ Sample data inserted successfully

## 🎯 **Next Steps**

1. **Add PostgreSQL service** to Railway project
2. **Deploy application** (automatic database setup)
3. **Test endpoints** to verify functionality
4. **Configure WhatsApp** for full integration

Your ELLA hotel assistant will now have a robust PostgreSQL database supporting:
- 🏨 Hotel search and filtering
- 📅 Real-time availability checking
- 💰 Dynamic pricing
- 📊 Booking analytics
- 📱 WhatsApp integration

## 🔗 **Related Documentation**

- [Railway Redis Setup](RAILWAY_REDIS_SETUP.md)
- [WhatsApp Integration Guide](WHATSAPP_SETUP_STATUS.md)
- [ELLA Tools Documentation](ELLA_TOOLS.md) 
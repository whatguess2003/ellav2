# 🐘 ELLA PostgreSQL Database Setup

> **Complete PostgreSQL database setup for ELLA Hotel System**

## 🎯 **What This Provides**

PostgreSQL database setup with:
- ✅ **Complete hotel schema** (8 tables with relationships)
- ✅ **Sample hotel data** (3 hotels with room types)
- ✅ **30 days availability** data with weekend pricing
- ✅ **Sample guests and bookings**

## 🚀 **Setup Options**

### **Option A: Google Cloud SQL PostgreSQL (Recommended)**
1. Create PostgreSQL instance in Google Cloud SQL
2. Run SQL scripts in order:
   - `database_schema_postgresql.sql`
   - `sample_data_postgresql.sql`
   - `test_database_postgresql.sql`
3. Get connection URL: `postgresql://user:password@host:port/database`

### **Option B: Railway PostgreSQL**
1. Add PostgreSQL service in Railway
2. Use Railway console to run SQL scripts
3. Railway automatically provides `DATABASE_URL`

### **Option C: Local Development**
- Uses SQLite automatically (`ella.db`)
- No setup needed for development

## 📊 **What Gets Created**

### **Hotels:**
- **Grand Hyatt Kuala Lumpur** (5⭐) - RM 420-450/night
- **Sam Hotel KL** (3⭐) - RM 120-150/night  
- **Marina Court Resort** (4⭐) - RM 220-280/night

### **Database Tables:**
- `hotels` - Hotel information with PostgreSQL arrays for amenities
- `room_types` - Room categories and pricing
- `availability` - Date-specific inventory (30 days with weekend pricing)
- `guests` - Customer information
- `bookings` - Reservation records with self-describing references
- `check_ins` - Check-in tracking
- `payments` - Payment records
- `reviews` - Guest feedback

## 🔄 **For Your Main ELLA App**

The main ELLA application automatically detects the database:
- **No `DATABASE_URL`** → Uses SQLite (development)
- **`DATABASE_URL=postgresql://...`** → Uses PostgreSQL (production)

```python
# Your code works unchanged:
from database.postgresql_connection import execute_query
hotels = execute_query("SELECT * FROM hotels")
```

## 🛠️ **Files Available**

### **SQL Scripts:**
- `database_schema_postgresql.sql` - Creates all tables
- `sample_data_postgresql.sql` - Inserts sample data
- `test_database_postgresql.sql` - Verifies setup

### **Python Connection:**
- `database/postgresql_connection.py` - Universal connection manager
- `test_postgresql_connection.py` - Test script

### **Documentation:**
- `POSTGRESQL_SETUP_COMPLETE.md` - Complete setup guide

## 🎯 **Key Features**

- ✅ **Automatic Detection** - SQLite for dev, PostgreSQL for production
- ✅ **Query Conversion** - Automatic SQLite → PostgreSQL translation
- ✅ **Connection Pooling** - Optimized for production
- ✅ **Native Arrays** - PostgreSQL TEXT[] for amenities
- ✅ **Weekend Pricing** - Realistic availability patterns

## 🧪 **Testing**

```bash
python test_postgresql_connection.py
```

Expected output:
```
🏨 Hotels: 4 (Grand Hyatt Kuala Lumpur 5⭐)
🛏️ Room types: 3
📋 Bookings: 4
✅ Connection manager: Ready!
```

---

**🐘 PostgreSQL-ready ELLA Hotel System with automatic SQLite fallback for development!**
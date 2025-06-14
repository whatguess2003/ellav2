# 🗄️ Local PostgreSQL Setup for ELLA Hotel System

## 📋 **Overview**

Set up PostgreSQL locally using pgAdmin4, then connect your ELLA system to both local development and Railway production databases.

## 🚀 **Step 1: Install PostgreSQL & pgAdmin4**

### **Windows Installation:**
1. **Download PostgreSQL:** https://www.postgresql.org/download/windows/
2. **Run installer** - Include pgAdmin4 and Stack Builder
3. **Set password** for `postgres` user (remember this!)
4. **Default port:** 5432
5. **Default database:** postgres

### **Verify Installation:**
```bash
# Check PostgreSQL is running
psql --version

# Connect to default database
psql -U postgres -h localhost
```

## 🔧 **Step 2: Create ELLA Database**

### **Option A: Using pgAdmin4 (GUI)**
1. **Open pgAdmin4** from Start Menu
2. **Connect to PostgreSQL** (enter your postgres password)
3. **Right-click "Databases"** → Create → Database
4. **Database name:** `ella_hotel`
5. **Owner:** postgres
6. **Click "Save"**

### **Option B: Using Command Line**
```bash
# Connect to PostgreSQL
psql -U postgres -h localhost

# Create database
CREATE DATABASE ella_hotel;

# Connect to the new database
\c ella_hotel

# Exit
\q
```

## 📊 **Step 3: Run Database Setup Script**

### **Local Setup Script:**
```bash
# In your ellav2 directory
cd C:\LEON\ellav2

# Set local database URL
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ella_hotel

# Run setup (we'll create this script)
python setup_local_database.py
```

## 🌐 **Step 4: Railway Production Database**

### **Get Railway Database URL:**
1. **Railway Dashboard** → Your Project → PostgreSQL Service
2. **Connect tab** → Copy **Database URL**
3. **Format:** `postgresql://user:password@host:port/database`

### **Production Setup:**
```bash
# Set Railway database URL
set DATABASE_URL=postgresql://user:password@railway-host:port/database

# Run same setup script
python setup_local_database.py
```

## 🔄 **Step 5: Environment Configuration**

### **Create .env file:**
```env
# Local Development
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ella_hotel

# Railway Production (comment out local, uncomment this)
# DATABASE_URL=postgresql://user:password@railway-host:port/database

# Other settings
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_openai_key
```

## 🧪 **Step 6: Test Database Connection**

### **Test Script:**
```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ Connected to PostgreSQL: {version[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM hotels;")
    count = cursor.fetchone()
    print(f"✅ Hotels in database: {count[0]}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## 📋 **Database Schema Overview**

After setup, your database will have:

### **Tables:**
- `hotels` - Hotel information
- `room_types` - Room categories and pricing  
- `availability` - Date-specific inventory
- `bookings` - Reservation records
- `guests` - Customer information
- `check_ins` - Check-in records
- `payments` - Payment tracking
- `reviews` - Guest feedback

### **Sample Data:**
- **3 Hotels** with complete information
- **6 Room Types** across different categories
- **30 Days** of availability data
- **Multiple price points** and amenities

## 🔧 **pgAdmin4 Management**

### **Useful pgAdmin4 Features:**
- **Query Tool** - Run SQL commands
- **Table Viewer** - Browse data visually
- **Backup/Restore** - Database management
- **User Management** - Create additional users
- **Performance Dashboard** - Monitor database

### **Common Queries:**
```sql
-- View all hotels
SELECT * FROM hotels;

-- Check availability for specific dates
SELECT * FROM availability WHERE date BETWEEN '2025-06-15' AND '2025-06-20';

-- View bookings
SELECT * FROM bookings ORDER BY created_at DESC;
```

## 🚀 **Deployment Workflow**

### **Development:**
1. **Local PostgreSQL** - Development and testing
2. **pgAdmin4** - Database management and queries
3. **Local ELLA app** - Connect to local database

### **Production:**
1. **Railway PostgreSQL** - Production database
2. **Same setup script** - Initialize production database
3. **Railway ELLA app** - Connect to Railway database

## 💡 **Benefits of This Approach**

- ✅ **Full control** - Complete database access via pgAdmin4
- ✅ **Visual management** - GUI for database operations
- ✅ **Local development** - Fast local testing
- ✅ **Production ready** - Same scripts work for Railway
- ✅ **Backup/restore** - Easy database management
- ✅ **SQL queries** - Direct database access for debugging

## 🛠️ **Troubleshooting**

### **Connection Issues:**
```bash
# Check PostgreSQL service is running
services.msc → PostgreSQL

# Test connection
psql -U postgres -h localhost -p 5432
```

### **Permission Issues:**
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ella_hotel TO postgres;
```

### **Port Conflicts:**
- Default PostgreSQL port: 5432
- Check if port is in use: `netstat -an | findstr 5432`

---

**🎯 This approach gives you full control over your database with professional tools!** 
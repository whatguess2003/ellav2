# 🗄️ ELLA Hotel Database Setup Service

> **🎯 Railway Service: Database initialization and setup**

## 📋 **Purpose**

This Railway service initializes the PostgreSQL database for the ELLA Hotel Assistant system. It runs once to set up the complete database schema and sample data, then completes.

## 🏗️ **Railway Project Structure**

This service is part of a dedicated Railway project with:
- **PostgreSQL Service** - The actual database
- **Setup Service** (this repo) - Initializes the database once

## 🚀 **How It Works**

1. **Deploy to Railway** - This service runs automatically
2. **Database Setup** - Connects to PostgreSQL service and creates schema
3. **Sample Data** - Adds hotels, rooms, and availability data
4. **Completion** - Service completes after successful setup

## 🗄️ **What Gets Created**

After this service runs, your PostgreSQL database will have:

### **Tables Created:**
- `hotels` - Hotel information and details
- `room_types` - Room categories and pricing
- `availability` - Date-specific inventory
- `bookings` - Reservation records
- `guests` - Customer information
- `check_ins` - Check-in records
- `payments` - Payment tracking
- `reviews` - Guest feedback

### **Sample Data:**
- **Grand Hyatt Kuala Lumpur** (5⭐) - RM 450/night
- **Sam Hotel KL** (3⭐) - RM 120/night  
- **Marina Court Resort** (4⭐) - RM 280/night
- **30 days** of availability data
- **Multiple room types** per hotel

## 🔧 **Railway Configuration**

### **Environment Variables (Auto-configured):**
- `DATABASE_URL` - Automatically set by Railway PostgreSQL service
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection details

### **Service Dependencies:**
This service requires the PostgreSQL service to be running first.

## 📊 **Verification**

After this service completes, you can verify the setup:

```sql
-- Connect to your PostgreSQL service and run:
SELECT COUNT(*) FROM hotels;          -- Should return 3
SELECT COUNT(*) FROM room_types;      -- Should return 6  
SELECT COUNT(*) FROM availability;    -- Should return 180 (30 days × 6 rooms)
```

## 🔗 **Related Services**

- **Main Application:** https://github.com/whatguess2003/ellav2
- **This Setup Service:** https://github.com/whatguess2003/ella-database-setup

## 🎯 **Workflow**

1. **Deploy Database Setup** (this service) - Runs once to initialize
2. **Deploy Main Application** (ellav2) - Connects to initialized database
3. **ELLA System Ready** - Hotel booking system operational

## ⚠️ **Important Notes**

- **One-time service** - Only needs to run once per database
- **Idempotent** - Safe to run multiple times (checks for existing data)
- **Automatic connection** - Uses Railway's PostgreSQL service variables
- **Completes after setup** - Service will finish after successful initialization

## 🛠️ **Troubleshooting**

### **Service Fails to Start**
- Check PostgreSQL service is running
- Verify DATABASE_URL is set
- Check service logs for connection errors

### **Database Already Exists**
- Service will detect existing tables and skip creation
- Safe to redeploy if needed

### **Connection Issues**
```bash
# Service will automatically retry connections
# Check Railway PostgreSQL service status
```

## 📞 **Support**

For issues with:
- **Database setup** - Check this service's logs in Railway
- **Main application** - Check ellav2 repository

---

**🎯 This service initializes your ELLA Hotel database once, then completes successfully.**
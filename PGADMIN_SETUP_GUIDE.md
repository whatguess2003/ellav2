# 🗄️ pgAdmin4 Database Setup Guide

## 📋 **Simple SQL Script Approach**

No Python dependencies needed! Just run SQL scripts directly in pgAdmin4.

## 🚀 **Step-by-Step Setup**

### **Step 1: Install PostgreSQL & pgAdmin4**
1. **Download:** https://www.postgresql.org/download/windows/
2. **Install** - Include pgAdmin4 in installation
3. **Remember your postgres password!**

### **Step 2: Create Database**
1. **Open pgAdmin4**
2. **Connect to PostgreSQL** (enter your password)
3. **Right-click "Databases"** → Create → Database
4. **Database name:** `ella_hotel`
5. **Click "Save"**

### **Step 3: Run SQL Scripts**

#### **3.1 Create Schema**
1. **Right-click `ella_hotel` database** → Query Tool
2. **Open file:** `database_schema.sql`
3. **Click Execute (F5)**
4. **Verify:** Should see "ELLA Hotel Database Schema Created Successfully!"

#### **3.2 Insert Sample Data**
1. **In same Query Tool** (or open new one)
2. **Open file:** `sample_data.sql`  
3. **Click Execute (F5)**
4. **Verify:** Should see hotel summary with 3 hotels, 6 room types, etc.

## ✅ **Verification**

After running both scripts, you should see:

```
Hotels: 3
Room Types: 6  
Availability Records: 180
Guests: 3
Bookings: 1

Hotel Summary:
- Grand Hyatt Kuala Lumpur (Kuala Lumpur) 5⭐ - 2 room types - 420 - 450 MYR
- Marina Court Resort (Kota Kinabalu) 4⭐ - 2 room types - 220 - 280 MYR  
- Sam Hotel KL (Kuala Lumpur) 3⭐ - 2 room types - 120 - 150 MYR
```

## 🔍 **Browse Your Data**

In pgAdmin4, expand your database to see:
- **Tables** - All 8 tables created
- **hotels** - 3 sample hotels
- **room_types** - 6 different room categories
- **availability** - 30 days of pricing data
- **guests** - Sample guest records

## 🧪 **Test Queries**

Try these queries in pgAdmin4 Query Tool:

```sql
-- View all hotels
SELECT * FROM hotels;

-- Check room availability for next week
SELECT 
    h.name as hotel,
    rt.name as room_type,
    a.date,
    a.available_rooms,
    a.price
FROM availability a
JOIN room_types rt ON a.room_type_id = rt.id
JOIN hotels h ON rt.hotel_id = h.id
WHERE a.date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7
ORDER BY h.name, a.date;

-- View bookings
SELECT 
    b.reference,
    g.name as guest_name,
    h.name as hotel_name,
    rt.name as room_type,
    b.check_in_date,
    b.check_out_date,
    b.total_amount
FROM bookings b
JOIN guests g ON b.guest_id = g.id
JOIN hotels h ON b.hotel_id = h.id
JOIN room_types rt ON b.room_type_id = rt.id;
```

## 🔄 **For Railway Production**

To use the same data on Railway:
1. **Get Railway PostgreSQL connection details**
2. **Connect to Railway database in pgAdmin4:**
   - Host: your-railway-host
   - Port: your-railway-port  
   - Database: your-railway-database
   - Username: postgres
   - Password: your-railway-password
3. **Run the same SQL scripts** on Railway database

## 💡 **Benefits**

- ✅ **No Python dependencies** - Pure SQL approach
- ✅ **Visual database management** - pgAdmin4 GUI
- ✅ **Professional tools** - Industry standard
- ✅ **Easy debugging** - Direct SQL queries
- ✅ **Backup/Restore** - Built-in pgAdmin4 features
- ✅ **Works everywhere** - Local, Railway, any PostgreSQL

## 🛠️ **Troubleshooting**

### **Script Errors?**
- Make sure you created the `ella_hotel` database first
- Run `database_schema.sql` before `sample_data.sql`
- Check for typos in database name

### **Connection Issues?**
- Verify PostgreSQL service is running
- Check your postgres password
- Ensure port 5432 is available

### **Permission Issues?**
```sql
-- Run this if you get permission errors
GRANT ALL PRIVILEGES ON DATABASE ella_hotel TO postgres;
```

---

**🎉 Your ELLA database is ready! No Python dependencies required.** 
# 🚀 Quick Start: PostgreSQL Setup for ELLA

## 📋 **5-Minute Setup Guide**

### **Step 1: Install PostgreSQL**
1. **Download:** https://www.postgresql.org/download/windows/
2. **Install** with pgAdmin4 included
3. **Remember your postgres password!**

### **Step 2: Create Database**
```sql
-- Open pgAdmin4 or use command line
CREATE DATABASE ella_hotel;
```

### **Step 3: Configure Environment**
```bash
# Copy template and edit
copy env_template.txt .env

# Edit .env file - replace 'your_password' with your postgres password
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ella_hotel
```

### **Step 4: Run Setup**
```bash
# Install dependencies (if not already done)
pip install psycopg2-binary python-dotenv

# Run database setup
python setup_local_database.py
```

### **Step 5: Test Connection**
```bash
# Verify everything works
python test_database_connection.py
```

## ✅ **Expected Output**

```
🚀 Starting ELLA Hotel Database Setup...
✅ Connected to PostgreSQL database
✅ Created all database tables
✅ Inserted sample data:
   - 3 hotels
   - 6 room types
   - 30 days of availability data

🎉 Database Setup Complete!
📊 Summary:
   - Hotels: 3
   - Room Types: 6
   - Availability Records: 180

🏨 Hotels in Database:
   - Grand Hyatt Kuala Lumpur (Kuala Lumpur) - 5⭐ - 2 room types
   - Marina Court Resort (Kota Kinabalu) - 4⭐ - 2 room types
   - Sam Hotel KL (Kuala Lumpur) - 3⭐ - 2 room types
```

## 🎯 **What You Get**

- **Complete hotel database** with 3 sample hotels
- **Room types and pricing** for each hotel
- **30 days of availability** data
- **Professional schema** ready for production
- **pgAdmin4 access** for database management

## 🔄 **For Railway Production**

Same script works for Railway:
```bash
# Get your Railway PostgreSQL URL from dashboard
# Update .env with Railway URL
DATABASE_URL=postgresql://user:pass@railway-host:port/database

# Run same setup script
python setup_local_database.py
```

## 🛠️ **Troubleshooting**

### **Connection Failed?**
- Check PostgreSQL service is running
- Verify password in .env file
- Ensure database 'ella_hotel' exists

### **Permission Issues?**
```sql
-- In pgAdmin4 or psql
GRANT ALL PRIVILEGES ON DATABASE ella_hotel TO postgres;
```

### **Port Issues?**
- Default PostgreSQL port: 5432
- Check if port is available: `netstat -an | findstr 5432`

---

**🎉 You're ready to run ELLA with PostgreSQL!** 
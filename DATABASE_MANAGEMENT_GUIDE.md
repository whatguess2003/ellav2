# 🛠️ ELLA Database Management Guide

## 🎯 **Database Manager Script**

The `manage_database.py` script handles all PostgreSQL database operations for your ELLA system on Railway.

## 🚀 **Quick Start**

### **Basic Commands:**
```bash
# Check database health and status
python manage_database.py --health

# Complete database reset (drops all tables, recreates schema, inserts sample data)
python manage_database.py --reset

# Insert sample hotel data only
python manage_database.py --seed

# Create backup before changes
python manage_database.py --backup

# Run database tests
python manage_database.py --test

# Force operations without confirmations
python manage_database.py --reset --force
```

## 🔄 **Common Workflows**

### **1. Initial Database Setup (New Railway PostgreSQL)**
```bash
# After creating Railway PostgreSQL service
python manage_database.py --reset --force
```
**Result**: Complete database with schema + sample hotels

### **2. Add New Hotels/Update Data**
```bash
# Backup first
python manage_database.py --backup

# Reset with new data
python manage_database.py --reset
```
**Result**: Fresh database with updated hotel data

### **3. Schema Changes**
```bash
# Backup existing data
python manage_database.py --backup

# Update your SQL files, then reset
python manage_database.py --reset
```
**Result**: New schema with updated structure

### **4. Regular Health Check**
```bash
python manage_database.py --health
```
**Result**: Database status and record counts

## 📊 **What Each Operation Does**

### **`--health` (Health Check)**
- ✅ Tests database connection
- ✅ Shows table record counts
- ✅ Displays sample hotel data
- ✅ Safe to run anytime

### **`--reset` (Complete Reset)**
- ⚠️ **DESTRUCTIVE**: Drops all tables
- ✅ Recreates schema from `database_schema_postgresql.sql`
- ✅ Inserts sample data from `sample_data_postgresql.sql`
- ✅ Complete fresh start

### **`--seed` (Sample Data Only)**
- ✅ Inserts sample hotels/rooms/availability
- ✅ Preserves existing schema
- ⚠️ May cause duplicates if data already exists

### **`--backup` (Create Backup)**
- ✅ Exports current data structure
- ✅ Creates timestamped backup file
- ✅ Safe to run before any changes

### **`--test` (Run Tests)**
- ✅ Executes queries from `test_database_postgresql.sql`
- ✅ Verifies database integrity
- ✅ Shows sample data

## 🚄 **Railway Integration**

### **Environment Detection:**
- **Local Development**: Uses SQLite (`ella.db`)
- **Railway Deployment**: Uses PostgreSQL (automatic via `DATABASE_URL`)

### **Railway Workflow:**
1. **Create PostgreSQL service** in Railway
2. **Deploy your ELLA app** (gets `DATABASE_URL` automatically)
3. **Run database manager** to initialize:
   ```bash
   python manage_database.py --reset --force
   ```

### **Railway Console Alternative:**
You can also run SQL scripts directly in Railway PostgreSQL console:
1. Go to Railway PostgreSQL service
2. Open "Query" tab
3. Copy/paste SQL files in order:
   - `database_schema_postgresql.sql`
   - `sample_data_postgresql.sql`

## 🔧 **Customizing Hotel Data**

### **Method 1: Edit SQL Files**
1. Edit `sample_data_postgresql.sql`
2. Add your hotels in the INSERT statements
3. Run `python manage_database.py --reset`

### **Method 2: Programmatic (Future Enhancement)**
```python
# Example of adding hotel via script
hotel_data = {
    'name': 'New Hotel KL',
    'slug': 'new-hotel-kl',
    'city': 'Kuala Lumpur',
    'state': 'Kuala Lumpur',
    'star_rating': 4,
    'description': 'Modern hotel in city center'
}

manager = DatabaseManager()
manager.add_hotel(hotel_data)
```

## 📋 **Files Required**

### **SQL Files (must exist):**
- `database_schema_postgresql.sql` - Table definitions
- `sample_data_postgresql.sql` - Sample hotel data
- `test_database_postgresql.sql` - Test queries

### **Python Files:**
- `manage_database.py` - Main management script
- `database/postgresql_connection.py` - Connection manager

## ⚠️ **Safety Notes**

### **Destructive Operations:**
- `--reset` deletes ALL data (bookings, guests, everything)
- Always `--backup` before major changes
- Use `--force` carefully (skips confirmations)

### **Production Safety:**
- Test on development database first
- Backup before schema changes
- Consider maintenance windows for resets

## 🎯 **Example Scenarios**

### **Scenario 1: New Hotel Chain**
```bash
# 1. Backup current data
python manage_database.py --backup

# 2. Edit sample_data_postgresql.sql with new hotels
# 3. Reset database
python manage_database.py --reset

# 4. Verify
python manage_database.py --health
```

### **Scenario 2: Schema Update**
```bash
# 1. Backup
python manage_database.py --backup

# 2. Edit database_schema_postgresql.sql
# 3. Reset with new schema
python manage_database.py --reset --force

# 4. Test
python manage_database.py --test
```

### **Scenario 3: Quick Health Check**
```bash
python manage_database.py
# (defaults to --health)
```

## 🚀 **Ready to Use!**

Your database management system is now ready for Railway PostgreSQL deployment. The script automatically detects your environment and works seamlessly with both local SQLite and Railway PostgreSQL.

**Push to Git and you're ready to manage your ELLA database!** 🎉 
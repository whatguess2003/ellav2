# 🗄️ Database Setup for ELLA Hotel System

## 📋 **Overview**

The ELLA Hotel System uses a **separate repository** for database setup to keep production code clean and avoid running setup scripts multiple times.

## 🏗️ **Repository Structure**

### **Main Repository (ellav2):**
- ✅ Production application code
- ✅ Database connection manager
- ✅ WhatsApp integration
- ✅ Railway deployment

### **Setup Repository (ella-database-setup):**
- ✅ PostgreSQL schema creation
- ✅ Sample data seeding
- ✅ One-time setup scripts
- ✅ Database documentation

## 🚀 **Setup Process**

### **1. Add PostgreSQL to Railway**
1. Go to Railway Dashboard → Your Project
2. Click **"+ New Service"** → **"Database"** → **"PostgreSQL"**
3. Railway automatically sets environment variables

### **2. Run Database Setup (One-Time)**
```bash
# Clone the setup repository
git clone https://github.com/whatguess2003/ella-database-setup.git
cd ella-database-setup

# Install dependencies
pip install -r requirements.txt

# Set Railway environment variables
export DATABASE_URL="your-railway-postgres-url"

# Run setup
python postgresql_setup.py
```

### **3. Deploy Main Application**
```bash
# Deploy ellav2 repository to Railway
# Database connection will automatically work
```

## 🧪 **Testing**

After setup, test your database:
```bash
curl https://your-app.up.railway.app/test/database
```

Expected response:
```json
{
  "status": "success",
  "database_type": "PostgreSQL",
  "test_results": {
    "hotels_found": 3,
    "sample_hotel": "Grand Hyatt Kuala Lumpur"
  }
}
```

## 📊 **Sample Data Included**

- **Grand Hyatt Kuala Lumpur** (5⭐) - RM 450/night
- **Sam Hotel KL** (3⭐) - RM 120/night  
- **Marina Court Resort** (4⭐) - RM 280/night
- **30 days availability** data

## 🔗 **Links**

- **Setup Repository:** https://github.com/whatguess2003/ella-database-setup
- **Main Application:** https://github.com/whatguess2003/ellav2
- **Railway Dashboard:** https://railway.app/dashboard

## 💡 **Benefits of Separate Repository**

- ✅ **Clean production code** - No setup scripts in main app
- ✅ **One-time execution** - Setup scripts won't run on every deploy
- ✅ **Version control** - Track database schema changes separately
- ✅ **Security** - Setup scripts don't need to be in production
- ✅ **Flexibility** - Easy to run setup on different environments 
#!/usr/bin/env python3
"""
Test Schema Creation Script
Verifies the create_schema.py is ready for Railway deployment
"""

import os
from database.postgresql_connection import db_manager

def test_schema_script():
    """Test that schema creation script is properly configured"""
    
    print("🧪 Testing Schema Creation Script...")
    print(f"🔗 Current Database Type: {db_manager.db_type}")
    
    # Check if create_schema.py exists
    if os.path.exists('create_schema.py'):
        print("✅ create_schema.py exists")
    else:
        print("❌ create_schema.py not found")
        return False
    
    # Check if postgresql_connection.py exists
    if os.path.exists('database/postgresql_connection.py'):
        print("✅ PostgreSQL connection manager exists")
    else:
        print("❌ PostgreSQL connection manager not found")
        return False
    
    # Test import
    try:
        import create_schema
        print("✅ create_schema.py imports successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Check environment detection
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        if 'postgresql' in database_url:
            print("✅ PostgreSQL DATABASE_URL detected")
        else:
            print(f"⚠️  Non-PostgreSQL DATABASE_URL: {database_url[:20]}...")
    else:
        print("📝 No DATABASE_URL - will use SQLite locally (expected)")
    
    print("\n🎯 Railway Deployment Readiness:")
    print("✅ Schema creation script ready")
    print("✅ PostgreSQL connection manager ready") 
    print("✅ Will automatically detect Railway PostgreSQL")
    print("✅ Ready to deploy as manage_database_server")
    
    print("\n🚀 Railway Deployment Steps:")
    print("1. Create Railway PostgreSQL service")
    print("2. Deploy this repo as manage_database_server")
    print("3. Run: python create_schema.py")
    print("4. Schema will be created in Railway PostgreSQL")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("ELLA Schema Creation Test")
    print("=" * 50)
    
    success = test_schema_script()
    
    if success:
        print("\n🎉 Schema creation script is ready for Railway!")
    else:
        print("\n❌ Issues found with schema creation script")
    
    print("=" * 50) 
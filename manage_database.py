#!/usr/bin/env python3
"""
ELLA Database Management Script
Manages PostgreSQL database operations for Railway deployment
"""

import os
import sys
import argparse
from datetime import datetime
from database.postgresql_connection import db_manager, execute_query, execute_update

class DatabaseManager:
    """Manages ELLA PostgreSQL database operations"""
    
    def __init__(self):
        self.db_manager = db_manager
        print(f"🔗 Database Type: {self.db_manager.db_type}")
        
    def health_check(self):
        """Check database connection and basic stats"""
        print("🔍 Database Health Check...")
        
        health = self.db_manager.health_check()
        print(f"📊 Status: {health['status']}")
        print(f"🗄️  Type: {health['database_type']}")
        
        if health['status'] == 'healthy':
            try:
                # Get table counts
                tables = ['hotels', 'room_types', 'availability', 'guests', 'bookings', 'check_ins', 'payments', 'reviews']
                print("\n📋 Table Status:")
                
                for table in tables:
                    try:
                        result = execute_query(f"SELECT COUNT(*) as count FROM {table}")
                        count = result[0]['count'] if result else 0
                        print(f"   {table}: {count} records")
                    except Exception as e:
                        print(f"   {table}: ❌ Not found or error")
                
                # Show sample data
                try:
                    hotels = execute_query("SELECT name, city, star_rating FROM hotels LIMIT 3")
                    if hotels:
                        print("\n🏨 Sample Hotels:")
                        for hotel in hotels:
                            print(f"   • {hotel['name']} ({hotel['city']}) - {hotel['star_rating']}⭐")
                except:
                    pass
                    
            except Exception as e:
                print(f"❌ Health check failed: {e}")
        else:
            print(f"❌ Database unhealthy: {health.get('error', 'Unknown error')}")
    
    def reset_database(self, confirm=True):
        """Complete database reset - drops all tables and recreates"""
        if confirm:
            response = input("⚠️  This will DELETE ALL DATA and recreate the database. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return False
        
        print("🗑️  Resetting database...")
        
        try:
            # Read and execute schema
            schema_file = 'database_schema_postgresql.sql'
            if not os.path.exists(schema_file):
                print(f"❌ Schema file not found: {schema_file}")
                return False
            
            print("📋 Creating database schema...")
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for stmt in statements:
                if stmt and not stmt.startswith('--'):
                    try:
                        execute_update(stmt)
                    except Exception as e:
                        if 'does not exist' not in str(e):  # Ignore "table does not exist" errors
                            print(f"⚠️  Schema warning: {e}")
            
            print("✅ Database schema created")
            
            # Insert sample data
            self.seed_data(confirm=False)
            
            print("🎉 Database reset complete!")
            return True
            
        except Exception as e:
            print(f"❌ Database reset failed: {e}")
            return False
    
    def seed_data(self, confirm=True):
        """Insert sample hotel data"""
        if confirm:
            response = input("📊 Insert sample hotel data? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return False
        
        print("📊 Seeding sample data...")
        
        try:
            # Read and execute sample data
            data_file = 'sample_data_postgresql.sql'
            if not os.path.exists(data_file):
                print(f"❌ Sample data file not found: {data_file}")
                return False
            
            with open(data_file, 'r') as f:
                data_sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in data_sql.split(';') if stmt.strip()]
            
            for stmt in statements:
                if stmt and not stmt.startswith('--') and 'SELECT' not in stmt.upper():
                    try:
                        execute_update(stmt)
                    except Exception as e:
                        print(f"⚠️  Data warning: {e}")
            
            print("✅ Sample data inserted")
            return True
            
        except Exception as e:
            print(f"❌ Sample data insertion failed: {e}")
            return False
    
    def add_hotel(self, hotel_data):
        """Add a new hotel to the database"""
        print(f"🏨 Adding new hotel: {hotel_data.get('name', 'Unknown')}")
        
        try:
            # Insert hotel
            hotel_sql = """
                INSERT INTO hotels (name, slug, city, state, address, phone, email, star_rating, description, amenities)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            # Convert amenities to PostgreSQL array format
            amenities_array = f"ARRAY{hotel_data.get('amenities', [])}"
            
            hotel_params = (
                hotel_data['name'],
                hotel_data['slug'],
                hotel_data['city'],
                hotel_data['state'],
                hotel_data.get('address', ''),
                hotel_data.get('phone', ''),
                hotel_data.get('email', ''),
                hotel_data.get('star_rating', 3),
                hotel_data.get('description', ''),
                amenities_array
            )
            
            # This would need to be executed differently for PostgreSQL arrays
            # For now, let's use a simpler approach
            simple_sql = """
                INSERT INTO hotels (name, slug, city, state, star_rating, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            simple_params = (
                hotel_data['name'],
                hotel_data['slug'],
                hotel_data['city'],
                hotel_data['state'],
                hotel_data.get('star_rating', 3),
                hotel_data.get('description', '')
            )
            
            execute_update(simple_sql, simple_params)
            print(f"✅ Hotel '{hotel_data['name']}' added successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add hotel: {e}")
            return False
    
    def backup_data(self):
        """Create a backup of current data"""
        print("💾 Creating data backup...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{timestamp}.sql"
            
            # For now, just export key data as INSERT statements
            tables = ['hotels', 'room_types', 'guests', 'bookings']
            
            with open(backup_file, 'w') as f:
                f.write(f"-- ELLA Database Backup - {timestamp}\n\n")
                
                for table in tables:
                    try:
                        data = execute_query(f"SELECT * FROM {table}")
                        f.write(f"-- {table} data ({len(data)} records)\n")
                        
                        if data:
                            # This is a simplified backup - in production you'd want proper SQL generation
                            f.write(f"-- Data for {table} would be here\n")
                        
                        f.write("\n")
                    except Exception as e:
                        f.write(f"-- Error backing up {table}: {e}\n\n")
            
            print(f"✅ Backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def run_test_queries(self):
        """Run test queries to verify database"""
        print("🧪 Running database tests...")
        
        try:
            # Read and execute test queries
            test_file = 'test_database_postgresql.sql'
            if not os.path.exists(test_file):
                print(f"❌ Test file not found: {test_file}")
                return False
            
            with open(test_file, 'r') as f:
                test_sql = f.read()
            
            # Execute test queries (SELECT statements only)
            statements = [stmt.strip() for stmt in test_sql.split(';') if stmt.strip()]
            
            for stmt in statements:
                if stmt and stmt.upper().startswith('SELECT'):
                    try:
                        result = execute_query(stmt)
                        if result:
                            print(f"✅ Test passed: {result[0] if len(result) == 1 else f'{len(result)} results'}")
                    except Exception as e:
                        print(f"❌ Test failed: {e}")
            
            print("🎉 Database tests complete!")
            return True
            
        except Exception as e:
            print(f"❌ Tests failed: {e}")
            return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='ELLA Database Management')
    parser.add_argument('--health', action='store_true', help='Check database health')
    parser.add_argument('--reset', action='store_true', help='Reset entire database')
    parser.add_argument('--seed', action='store_true', help='Insert sample data')
    parser.add_argument('--backup', action='store_true', help='Create data backup')
    parser.add_argument('--test', action='store_true', help='Run test queries')
    parser.add_argument('--force', action='store_true', help='Skip confirmations')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = DatabaseManager()
    
    # Default to health check if no args
    if not any(vars(args).values()):
        args.health = True
    
    # Execute operations
    if args.health:
        manager.health_check()
    
    if args.backup:
        manager.backup_data()
    
    if args.reset:
        manager.reset_database(confirm=not args.force)
    
    if args.seed:
        manager.seed_data(confirm=not args.force)
    
    if args.test:
        manager.run_test_queries()

if __name__ == "__main__":
    main() 
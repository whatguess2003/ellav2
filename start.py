#!/usr/bin/env python3
"""
Railway Database Setup Service
Runs database initialization and then keeps service alive briefly
"""

import subprocess
import sys
import time

def main():
    print("🚀 Starting ELLA Database Setup Service...")
    
    try:
        # Run the database setup
        print("📋 Running PostgreSQL database setup...")
        result = subprocess.run([sys.executable, 'postgresql_setup.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database setup completed successfully!")
            print(result.stdout)
        else:
            print("❌ Database setup failed:")
            print(result.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running database setup: {e}")
        sys.exit(1)
    
    # Keep service alive briefly to show completion
    print("🎉 Database initialization complete!")
    print("💤 Service will complete in 30 seconds...")
    time.sleep(30)
    print("✅ Database setup service completed successfully!")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Reset Ella Database - Drop all tables for clean setup
"""

import sqlite3

def reset_database():
    """Drop all tables to reset database."""
    
    try:
        conn = sqlite3.connect('ella.db')
        cursor = conn.cursor()
        
        # Get all table names (exclude sqlite_sequence)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
        tables = cursor.fetchall()
        
        print(f"📋 Found {len(tables)} tables to drop:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Drop all tables
        dropped_count = 0
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{table[0]}"')
                print(f"   ✅ Dropped: {table[0]}")
                dropped_count += 1
            except Exception as e:
                print(f"   ❌ Failed to drop {table[0]}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎯 Database reset complete!")
        print(f"✅ {dropped_count} tables dropped")
        print("🔄 Ready for clean schema setup")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_database() 
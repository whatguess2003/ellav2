"""
PostgreSQL Database Connection Manager for ELLA
Supports both SQLite (local) and PostgreSQL (cloud) databases
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional, Any, Generator
import json

# Optional PostgreSQL imports
try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    print("📍 psycopg2 not available - PostgreSQL support disabled")
    POSTGRES_AVAILABLE = False
    psycopg2 = None

class PostgreSQLDatabaseManager:
    """Universal database manager for SQLite and PostgreSQL"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.is_postgres = (
            self.database_url and 
            'postgresql' in self.database_url and 
            POSTGRES_AVAILABLE
        )
        
        if self.is_postgres:
            self._init_postgres()
        else:
            self._init_sqlite()
    
    def _init_postgres(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.connection_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=self.database_url
            )
            print("✅ Connected to PostgreSQL cloud database")
            self.db_type = 'postgresql'
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print("🔄 Falling back to SQLite...")
            self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        self.db_path = os.getenv('DATABASE_PATH', 'ella.db')
        print(f"✅ Using SQLite database: {self.db_path}")
        self.db_type = 'sqlite'
        self.connection_pool = None
        self.is_postgres = False
    
    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get database connection with automatic cleanup"""
        if self.is_postgres and self.connection_pool:
            conn = self.connection_pool.getconn()
            try:
                yield conn
            finally:
                self.connection_pool.putconn(conn)
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            try:
                yield conn
            finally:
                conn.close()
    
    @contextmanager
    def get_cursor(self) -> Generator[Any, None, None]:
        """Get database cursor with automatic transaction handling"""
        with self.get_connection() as conn:
            if self.is_postgres:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute SELECT query and return results"""
        # Convert SQLite query to PostgreSQL if needed
        if self.is_postgres:
            query = self.convert_sqlite_to_postgres_query(query)
            # PostgreSQL uses %s placeholders like SQLite uses ?
            if params and '?' in query:
                query = query.replace('?', '%s')
        
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            # Convert to consistent format
            if self.is_postgres:
                return [dict(row) for row in results] if results else []
            else:
                return [dict(row) for row in results] if results else []
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[Any]:
        """Execute INSERT query and return last row ID"""
        # Convert SQLite query to PostgreSQL if needed
        if self.is_postgres:
            query = self.convert_sqlite_to_postgres_query(query)
            # Add RETURNING clause for PostgreSQL to get the ID
            if 'INSERT INTO' in query.upper() and 'RETURNING' not in query.upper():
                # Find the table name to determine the ID column
                table_name = query.split('INSERT INTO')[1].split('(')[0].strip()
                if 'hotels' in table_name:
                    query += ' RETURNING id'
                elif 'bookings' in table_name:
                    query += ' RETURNING id'
                else:
                    query += ' RETURNING id'
            
            # Convert ? placeholders to %s for PostgreSQL
            if params and '?' in query:
                query = query.replace('?', '%s')
        
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if self.is_postgres:
                result = cursor.fetchone()
                return result['id'] if result else None
            else:
                return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute UPDATE query and return affected rows"""
        # Convert SQLite query to PostgreSQL if needed
        if self.is_postgres:
            query = self.convert_sqlite_to_postgres_query(query)
            # Convert ? placeholders to %s for PostgreSQL
            if params and '?' in query:
                query = query.replace('?', '%s')
        
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    
    def convert_sqlite_to_postgres_query(self, sqlite_query: str) -> str:
        """Convert SQLite query to PostgreSQL compatible query"""
        if not self.is_postgres:
            return sqlite_query
        
        postgres_query = sqlite_query
        
        # Common conversions
        postgres_query = postgres_query.replace('AUTOINCREMENT', 'SERIAL')
        postgres_query = postgres_query.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
        postgres_query = postgres_query.replace('CURRENT_TIMESTAMP', 'NOW()')
        postgres_query = postgres_query.replace('datetime(', 'TO_TIMESTAMP(')
        postgres_query = postgres_query.replace("strftime('%Y-%m-%d', ", 'DATE(')
        
        # String concatenation (|| works in both SQLite and PostgreSQL)
        # No change needed for ||
        
        # LIMIT/OFFSET syntax is the same in both
        # No change needed
        
        # Boolean values
        postgres_query = postgres_query.replace('1', 'TRUE').replace('0', 'FALSE') if 'BOOLEAN' in postgres_query else postgres_query
        
        return postgres_query
    
    def health_check(self) -> dict:
        """Check database connection health"""
        try:
            test_query = "SELECT 1 as test"
            result = self.execute_query(test_query)
            
            return {
                'status': 'healthy',
                'database_type': self.db_type,
                'connection_pool': bool(self.connection_pool),
                'test_query_result': bool(result)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'database_type': self.db_type,
                'error': str(e)
            }

# Global instance
db_manager = PostgreSQLDatabaseManager()

# Convenience functions for easy migration
def get_db_connection():
    """Get database connection - replaces sqlite3.connect('ella.db')"""
    return db_manager.get_connection()

def execute_query(query: str, params: tuple = None) -> list:
    """Execute SELECT query - direct replacement for cursor.fetchall()"""
    return db_manager.execute_query(query, params)

def execute_insert(query: str, params: tuple = None) -> Optional[Any]:
    """Execute INSERT query - direct replacement"""
    return db_manager.execute_insert(query, params)

def execute_update(query: str, params: tuple = None) -> int:
    """Execute UPDATE query - direct replacement"""
    return db_manager.execute_update(query, params) 
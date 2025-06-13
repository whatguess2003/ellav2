"""
Cloud Database Connection Manager for Ella
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
    SimpleConnectionPool = None
    RealDictCursor = None

class CloudDatabaseManager:
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
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[Any]:
        """Execute INSERT query and return last row ID"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if self.is_postgres:
                return cursor.fetchone()  # For RETURNING clause
            else:
                return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute UPDATE query and return affected rows"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    
    def get_compatible_sql(self, sqlite_sql: str, postgres_sql: str = None) -> str:
        """Get database-specific SQL"""
        if self.is_postgres and postgres_sql:
            return postgres_sql
        return sqlite_sql
    
    def format_timestamp(self, timestamp_value: str = "CURRENT_TIMESTAMP") -> str:
        """Get database-specific timestamp format"""
        if self.is_postgres:
            return f"NOW()" if timestamp_value == "CURRENT_TIMESTAMP" else timestamp_value
        return timestamp_value
    
    def get_like_operator(self, case_sensitive: bool = False) -> str:
        """Get database-specific LIKE operator"""
        if self.is_postgres and not case_sensitive:
            return "ILIKE"
        return "LIKE"
    
    def json_encode(self, data: Any) -> str:
        """Encode data as JSON string for storage"""
        return json.dumps(data) if data else None
    
    def json_decode(self, json_str: str) -> Any:
        """Decode JSON string from storage"""
        try:
            return json.loads(json_str) if json_str else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    def create_table_if_not_exists(self, table_name: str, columns: dict, indexes: list = None):
        """Create table with database-specific syntax"""
        
        # Convert column definitions
        column_defs = []
        for col_name, col_def in columns.items():
            if self.is_postgres:
                # Convert SQLite types to PostgreSQL
                col_def = col_def.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
                col_def = col_def.replace('TEXT', 'VARCHAR(500)')
                col_def = col_def.replace('REAL', 'DECIMAL')
                col_def = col_def.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
                col_def = col_def.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
                col_def = col_def.replace('CURRENT_TIMESTAMP', 'NOW()')
            
            column_defs.append(f"{col_name} {col_def}")
        
        # Create table
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
        
        with self.get_cursor() as cursor:
            cursor.execute(create_sql)
            
            # Create indexes
            if indexes:
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                    except Exception as e:
                        print(f"⚠️ Index creation warning for {table_name}: {e}")
    
    def health_check(self) -> dict:
        """Check database connection health"""
        try:
            test_query = "SELECT 1" + (" as test" if self.is_postgres else "")
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

# Initialize global database manager
cloud_db = CloudDatabaseManager()

# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection (legacy support)"""
    return cloud_db.get_connection()

def get_db_cursor():
    """Get database cursor (legacy support)"""
    return cloud_db.get_cursor() 
import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional
import threading

logger = logging.getLogger(__name__)

_local = threading.local()

# Use an environment variable to specify the database path.
# This allows for easy configuration on different environments.
DATABASE_PATH = os.environ.get('DATABASE_URL', 'creative_studio.db')

def get_db_connection() -> Optional[sqlite3.Connection]:
    """Get database connection (thread-safe)."""
    try:
        if not hasattr(_local, 'connection') or _local.connection is None:
            # The check_same_thread=False is needed for Flask's development server,
            # but is not recommended in production with multiple threads.
            # Gunicorn handles this with separate worker processes.
            _local.connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            _local.connection.row_factory = sqlite3.Row  # Enable dict-like access
        return _local.connection
    except Exception as e:
        logger.error(f"Error getting database connection: {e}")
        return None

def close_db_connection():
    """Close database connection for current thread."""
    try:
        if hasattr(_local, 'connection') and _local.connection is not None:
            _local.connection.close()
            _local.connection = None
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

@contextmanager
def get_db_cursor():
    """Context manager for database operations."""
    conn = get_db_connection()
    if conn is None:
        raise Exception("Could not establish database connection")
    
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

def init_db():
    """Initialize database with required tables."""
    try:
        # For local use, ensure directory exists. On Render, this is handled differently
        # depending on if you use a persistent disk or not.
        if os.path.dirname(DATABASE_PATH):
            os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        with get_db_cursor() as cursor:
            # Content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT UNIQUE NOT NULL,
                    prompt TEXT NOT NULL,
                    style TEXT,
                    poem_data TEXT,
                    music_data TEXT,
                    animation_data TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Usage statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    prompt TEXT,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_user_id ON content(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_session_id ON content(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_endpoint ON usage_stats(endpoint)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_created_at ON usage_stats(created_at)')
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e
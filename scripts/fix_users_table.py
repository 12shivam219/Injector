"""
Fix users table schema
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_users_table():
    """Drop and recreate users table with correct schema"""
    try:
# Get database connection string (DATABASE_URL)
        connection_string = os.getenv('DATABASE_URL')
        if not connection_string:
            raise RuntimeError('DATABASE_URL environment variable is not set')
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Drop existing users table
        with engine.connect() as conn:
            logger.info("Dropping existing users table...")
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            conn.commit()
            logger.info("Users table dropped successfully")
        
        # Import models after dropping table to avoid any import-time table creation
        from database.models import Base, User
        
        # Create table with new schema
        logger.info("Creating users table with new schema...")
        Base.metadata.create_all(bind=engine, tables=[User.__table__])
        logger.info("Users table created successfully with new schema")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing users table: {e}")
        return False

if __name__ == "__main__":
    fix_users_table()
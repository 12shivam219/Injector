"""
Fix missing tables in resume_customizer database
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text, MetaData, Column, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.base import Base

# Define User model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime)
    settings = Column(JSON)

def get_connection_string():
    """Get database connection string from environment variables"""
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'admin')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    dbname = os.getenv('DB_NAME', 'resume_customizer')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def fix_database():
    """Add missing tables to the database"""
    try:
        # Get connection string
        connection_string = get_connection_string()
        logger.info(f"Using connection string: postgresql://{os.getenv('DB_USER')}:***@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Test connection
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Connection successful!")
            
            # Check if users table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """))
            users_table_exists = result.scalar()
            
            if not users_table_exists:
                logger.info("Creating missing users table...")
                Base.metadata.create_all(bind=engine)
                logger.info("Users table created successfully!")
            else:
                logger.info("Users table already exists.")
            
        return True
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        return False

if __name__ == "__main__":
    fix_database()
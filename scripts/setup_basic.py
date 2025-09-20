"""
Simple database setup script
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text, MetaData, Column, String, Boolean, DateTime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.base import Base

# Define User model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False)

def get_connection_string():
    """Get database connection string from environment (DATABASE_URL)"""
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL environment variable is not set')
    return url

def setup_database():
    """Setup database tables"""
    try:
        # Get connection string
        connection_string = get_connection_string()
        logger.info("Using DATABASE_URL from environment (masked)")
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Test connection
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Connection successful!")
        
        # Create tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    setup_database()
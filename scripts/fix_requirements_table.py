"""
Fix requirements table schema
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text, Column, String, Boolean, DateTime
from sqlalchemy.sql import func

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, Requirement

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_requirements_table():
    """Fix the requirements table schema"""
    try:
        # Get database connection string from environment variables
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'admin')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        dbname = os.getenv('DB_NAME', 'resume_customizer')
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Add missing columns if they don't exist
        with engine.connect() as conn:
            # Check if next_step column exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'requirements' 
                    AND column_name = 'next_step'
                );
            """))
            column_exists = result.scalar()
            
            if not column_exists:
                logger.info("Adding missing next_step column...")
                conn.execute(text("ALTER TABLE requirements ADD COLUMN next_step VARCHAR(255);"))
                conn.commit()
                logger.info("Added next_step column successfully")
            else:
                logger.info("next_step column already exists")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing requirements table: {e}")
        return False

if __name__ == "__main__":
    fix_requirements_table()
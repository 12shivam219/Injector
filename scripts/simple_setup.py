"""
Simple database setup script that just creates the needed tables
"""
import logging
from sqlalchemy import create_engine, text
from database.simple_config import get_simple_connection_string
from database.models import Base
from database.format_models import ResumeFormat, ResumeFormatMatch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_database():
    """Setup database tables without advanced features"""
    try:
        # Get simple connection string
        connection_string = get_simple_connection_string()
        print(f"Using connection string: {connection_string}")
        
        # Create engine without extra parameters
        engine = create_engine(connection_string)
        
        # Try connecting
        print("Testing database connection...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Connection successful!")
        
        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    setup_database()
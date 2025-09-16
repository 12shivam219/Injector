"""
Test script to verify connection to Neon PostgreSQL
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Test connection to Neon PostgreSQL"""
    logger.info("Testing connection to Neon PostgreSQL...")
    
    # Initialize connection manager
    db_manager = DatabaseConnectionManager()
    
    # Initialize connection
    if db_manager.initialize():
        logger.info("✅ Successfully connected to Neon PostgreSQL!")
        
        # Test a simple query
        with db_manager.get_session() as session:
            try:
                # Execute a simple query
                from sqlalchemy import text
                result = session.execute(text("SELECT 1 as test")).fetchone()
                logger.info(f"Query result: {result.test}")
                logger.info("✅ Query executed successfully!")
                return True
            except Exception as e:
                logger.error(f"❌ Query execution failed: {e}")
                return False
    else:
        logger.error("❌ Failed to connect to Neon PostgreSQL")
        return False

if __name__ == "__main__":
    test_connection()
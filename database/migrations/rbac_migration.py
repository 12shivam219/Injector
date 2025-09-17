"""
Migration script for Role-Based Access Control tables
"""

from sqlalchemy import create_engine, text
import logging
from database.connection import DatabaseConnection
from database.rbac import create_rbac_tables

logger = logging.getLogger(__name__)

def migrate_rbac():
    """Create RBAC tables and initial roles"""
    # Get database connection
    db_connection = DatabaseConnection()
    engine = db_connection.engine
    
    # Create RBAC tables
    create_rbac_tables(engine)
    
    # Create initial admin user if it doesn't exist
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        # Check if admin user exists (parameterized)
        result = conn.execute(text("SELECT COUNT(*) FROM db_users WHERE username = :u"), {'u': 'admin'})
        count = result.scalar()

        if count == 0:
            # Create admin user
            conn.execute(text("INSERT INTO db_users (username, role, is_active) VALUES (:u, :r, TRUE)"), {'u': 'admin', 'r': 'admin'})
            logger.info("Created initial admin user")
        else:
            logger.info("Admin user already exists")

    logger.info("RBAC migration completed successfully")

if __name__ == "__main__":
    migrate_rbac()
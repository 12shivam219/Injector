"""
Migration script for Role-Based Access Control tables
"""

from sqlalchemy import create_engine, text
from database.connection import DatabaseConnection
from database.rbac import create_rbac_tables

def migrate_rbac():
    """Create RBAC tables and initial roles"""
    # Get database connection
    db_connection = DatabaseConnection()
    engine = db_connection.engine
    
    # Create RBAC tables
    create_rbac_tables(engine)
    
    # Create initial admin user if it doesn't exist
    with engine.connect() as conn:
        # Check if admin user exists
        result = conn.execute(text("SELECT COUNT(*) FROM db_users WHERE username = 'admin'"))
        count = result.scalar()
        
        if count == 0:
            # Create admin user
            conn.execute(text("INSERT INTO db_users (username, role, is_active) VALUES ('admin', 'admin', TRUE)"))
            conn.commit()
            print("Created initial admin user")
        else:
            print("Admin user already exists")
    
    print("RBAC migration completed successfully")

if __name__ == "__main__":
    migrate_rbac()
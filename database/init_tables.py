"""Initialize database tables"""
import os
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Read DB connection from environment; do not hard-code credentials
DB_URL = os.getenv('DB_URL') or os.getenv('DATABASE_URL')
if not DB_URL:
    raise RuntimeError('Database URL not provided. Set DB_URL or DATABASE_URL in environment.')

engine = create_engine(DB_URL)

def init_tables():
    """Initialize the database tables"""
    try:
        with engine.connect() as connection:
            # Drop existing tables
            # Run DROP and CREATE statements; use autocommit where appropriate
            connection = connection.execution_options(isolation_level='AUTOCOMMIT')
            connection.execute(text("""
                DROP TABLE IF EXISTS requirement_comments CASCADE;
                DROP TABLE IF EXISTS requirement_consultants CASCADE;
                DROP TABLE IF EXISTS requirements CASCADE;
            """))

            # Create requirements table
            connection.execute(text("""
                CREATE TABLE requirements (
                    id SERIAL PRIMARY KEY,
                    job_title VARCHAR(255) NOT NULL,
                    client_company VARCHAR(255) NOT NULL,
                    applied_for VARCHAR(50) NOT NULL,
                    primary_tech_stack VARCHAR(100) NOT NULL,
                    tech_stack TEXT[] NOT NULL,
                    req_status VARCHAR(50) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """))
            # commits handled by autocommit

            # Create requirement_comments table
            connection.execute(text("""
                CREATE TABLE requirement_comments (
                    id SERIAL PRIMARY KEY,
                    requirement_id INTEGER NOT NULL,
                    comment_text TEXT NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    comment_type VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY(requirement_id) REFERENCES requirements(id) ON DELETE CASCADE
                );
            """))
            connection.commit()

            # Create requirement_consultants table
            connection.execute(text("""
                CREATE TABLE requirement_consultants (
                    id SERIAL PRIMARY KEY,
                    requirement_id INTEGER NOT NULL,
                    consultant_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY(requirement_id) REFERENCES requirements(id) ON DELETE CASCADE
                );
            """))
            connection.commit()

            logger.info("Database tables created successfully")

    except Exception as e:
        logger.exception("Error creating tables: %s", e)

if __name__ == "__main__":
    init_tables()
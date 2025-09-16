"""Initialize database tables"""
from sqlalchemy import create_engine, text

# Database connection parameters
params = {
    'host': 'localhost',
    'port': '5432',
    'database': 'resume_customizer',
    'user': 'postgres',
    'password': 'Amit@8982'
}

# Create database URL
url = f"postgresql://{params['user']}:{params['password'].replace('@', '%40')}@{params['host']}:{params['port']}/{params['database']}"
engine = create_engine(url)

def init_tables():
    """Initialize the database tables"""
    try:
        with engine.connect() as connection:
            # Drop existing tables
            connection.execute(text("""
                DROP TABLE IF EXISTS requirement_comments CASCADE;
                DROP TABLE IF EXISTS requirement_consultants CASCADE;
                DROP TABLE IF EXISTS requirements CASCADE;
            """))
            connection.commit()

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
            connection.commit()

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

            print("✅ Database tables created successfully!")

    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")

if __name__ == "__main__":
    init_tables()
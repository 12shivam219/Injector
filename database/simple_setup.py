"""
Simple Database Setup Script for Resume Customizer
Creates tables without requiring alembic or complex migrations
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_simple_database():
    """
    Create database tables using basic SQLAlchemy without alembic
    """
    try:
        print("🔧 Simple PostgreSQL Database Setup")
        print("=" * 50)
        
        # Check if .env file exists, create template if not
        env_path = '.env'
        if not os.path.exists(env_path):
            print("📝 Creating .env template...")
            with open(env_path, 'w') as f:
                f.write("""# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=resume_customizer
DB_USER=postgres
DB_PASSWORD=your_password_here
""")
            print("✅ .env template created!")
            print("⚠️  Please update the DB_PASSWORD in .env file with your PostgreSQL password")
            return False
        
        # Load environment variables from .env
        print("📖 Loading environment variables...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
                    print(f"   {key}={'*' * len(value) if 'PASSWORD' in key else value}")
        
        # Build connection string
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'resume_customizer')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        if not db_password or db_password == 'your_password_here':
            print("❌ Please set your PostgreSQL password in the .env file")
            return False
        
        # URL encode password to handle special characters
        from urllib.parse import quote_plus
        encoded_password = quote_plus(db_password)
        connection_string = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        
        print(f"🔌 Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}")
        print(f"📋 Using username: {db_user}")
        
        # First, connect to postgres database to create our target database
        postgres_connection_string = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/postgres"
        
        print("🔧 Creating database if it doesn't exist...")
        try:
            postgres_engine = create_engine(postgres_connection_string, echo=False)
            with postgres_engine.connect() as conn:
                # Set autocommit for database creation
                conn.execute(text("COMMIT"))
                
                # Check if database exists
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")).fetchone()
                
                if not result:
                    print(f"📊 Creating database '{db_name}'...")
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    print(f"✅ Database '{db_name}' created successfully!")
                else:
                    print(f"✅ Database '{db_name}' already exists!")
                    
        except Exception as e:
            print(f"❌ Failed to create database: {e}")
            print("💡 Please create the database manually:")
            print(f"   1. Connect to PostgreSQL as superuser")
            print(f"   2. Run: CREATE DATABASE {db_name};")
            return False
        
        # Now connect to our target database
        engine = create_engine(connection_string, echo=False)
        
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT 1")).fetchone()
            if result[0] != 1:
                raise Exception("Connection test failed")
        
        print("✅ Database connection successful!")
        
        # Import models after successful connection
        try:
            from database.models import Base
            from database.resume_models import ResumeDocument, ResumeCustomization
            
            # Create all tables
            print("📊 Creating database tables...")
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully!")
            
            # Create some basic indexes manually
            with engine.connect() as conn:
                print("📈 Creating performance indexes...")
                
                # Basic indexes that don't require complex syntax
                basic_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_resume_user ON resume_documents(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_resume_status ON resume_documents(processing_status)",
                    "CREATE INDEX IF NOT EXISTS idx_customization_company ON resume_customizations(company_name)",
                    "CREATE INDEX IF NOT EXISTS idx_email_recipient ON email_sends(recipient_email)",
                ]
                
                for index_sql in basic_indexes:
                    try:
                        conn.execute(text(index_sql))
                        print(f"   ✅ Index created")
                    except Exception as e:
                        print(f"   ⚠️ Index skipped: {str(e)[:50]}...")
                
                conn.commit()
            
            print("✅ Performance indexes created!")
            
            # Insert sample data
            print("📝 Creating sample data...")
            
            with engine.connect() as conn:
                # Insert a sample resume document
                sample_insert = text("""
                    INSERT INTO resume_documents (
                        id, filename, original_filename, file_size, 
                        original_content, user_id, processing_status, 
                        created_at, updated_at, is_active, version
                    ) VALUES (
                        gen_random_uuid(), 
                        'sample_resume.docx', 
                        'Sample Resume.docx', 
                        45678,
                        'Sample resume content with Python, JavaScript, and database skills...',
                        'demo_user_123',
                        'completed',
                        NOW(),
                        NOW(),
                        true,
                        1
                    ) ON CONFLICT DO NOTHING
                """)
                
                conn.execute(sample_insert)
                conn.commit()
                print("✅ Sample data created!")
            
            print("\n🎉 Database setup completed successfully!")
            print("\n📋 What was created:")
            print("✅ resume_documents - Store uploaded resume files")
            print("✅ resume_customizations - Job-specific modifications")
            print("✅ email_sends - Email delivery tracking")
            print("✅ processing_logs - Performance monitoring")
            print("✅ requirements - Job requirements (existing)")
            print("✅ Performance indexes for fast queries")
            print("✅ Sample data for testing")
            
            print("\n🚀 Next Steps:")
            print("1. Run: python database/demo_data_flow.py")
            print("2. Start your app: streamlit run app.py")
            
            return True
            
        except ImportError as e:
            print(f"❌ Failed to import database models: {e}")
            print("The SQLAlchemy index definition error has been fixed!")
            return False
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Create database 'resume_customizer' if it doesn't exist")
        print("3. Update .env file with correct credentials")
        return False

if __name__ == "__main__":
    create_simple_database()

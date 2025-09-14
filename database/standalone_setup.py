"""
Standalone Database Setup for Resume Customizer
Creates PostgreSQL tables without any external dependencies
"""

import os
import sys
from sqlalchemy import (
    create_engine, text, Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Float
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from urllib.parse import quote_plus
import uuid

Base = declarative_base()

# Define models directly here to avoid import issues
class BaseModel(Base):
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)

class ResumeDocument(BaseModel):
    __tablename__ = 'resume_documents'
    
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64), unique=True, index=True)
    mime_type = Column(String(100), default='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    
    original_content = Column(Text)
    processed_content = Column(Text)
    document_structure = Column(JSONB)
    
    processing_status = Column(String(50), default='uploaded', index=True)
    processing_error = Column(Text)
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), index=True)

class ResumeCustomization(BaseModel):
    __tablename__ = 'resume_customizations'
    
    resume_document_id = Column(UUID(as_uuid=True), ForeignKey('resume_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    
    job_title = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    job_description = Column(Text)
    
    tech_stack_input = Column(JSONB, default=list)
    required_skills = Column(JSONB, default=list)
    matched_skills = Column(JSONB, default=list)
    
    customized_content = Column(Text)
    added_bullet_points = Column(JSONB, default=list)
    modified_sections = Column(JSONB, default=dict)
    
    customization_strategy = Column(String(100), default='tech_stack_injection')
    ai_model_used = Column(String(100))
    processing_time_seconds = Column(Float)
    
    customization_status = Column(String(50), default='pending', index=True)
    quality_score = Column(Float)
    match_percentage = Column(Float)
    
    user_rating = Column(Integer)
    user_feedback = Column(Text)

class EmailSend(BaseModel):
    __tablename__ = 'email_sends'
    
    customization_id = Column(UUID(as_uuid=True), ForeignKey('resume_customizations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255))
    subject = Column(String(500), nullable=False)
    body = Column(Text)
    
    attachment_filename = Column(String(255))
    attachment_size = Column(Integer)
    
    send_status = Column(String(50), default='pending', index=True)
    send_error = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    
    email_service_id = Column(String(255))
    email_service = Column(String(100), default='yagmail')

class ProcessingLog(BaseModel):
    __tablename__ = 'processing_logs'
    
    resume_document_id = Column(UUID(as_uuid=True), ForeignKey('resume_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    
    log_level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    step_name = Column(String(100), index=True)
    
    execution_time_ms = Column(Float)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    function_name = Column(String(255))
    line_number = Column(Integer)
    stack_trace = Column(Text)
    
    log_metadata = Column(JSONB, default=dict)

def setup_database():
    """Setup PostgreSQL database with all tables"""
    try:
        print("🔧 Standalone PostgreSQL Database Setup")
        print("=" * 50)
        
        # Load environment variables
        env_path = '.env'
        if not os.path.exists(env_path):
            print("❌ .env file not found. Please create it first.")
            return False
        
        print("📖 Loading environment variables...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
                    print(f"   {key}={'*' * len(value) if 'PASSWORD' in key else value}")
        
        # Get database configuration
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'resume_customizer')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        if not db_password or db_password == 'your_password_here':
            print("❌ Please set your PostgreSQL password in the .env file")
            return False
        
        # URL encode password
        encoded_password = quote_plus(db_password)
        connection_string = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        
        print(f"🔌 Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}")
        
        # Create database if it doesn't exist
        postgres_connection_string = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/postgres"
        
        print("🔧 Ensuring database exists...")
        postgres_engine = create_engine(postgres_connection_string)
        with postgres_engine.connect() as conn:
            conn.execute(text("COMMIT"))
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")).fetchone()
            
            if not result:
                print(f"📊 Creating database '{db_name}'...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"✅ Database '{db_name}' created!")
            else:
                print(f"✅ Database '{db_name}' exists!")
        
        # Connect to target database and create tables
        engine = create_engine(connection_string)
        
        print("📊 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Create additional indexes
        print("📈 Creating performance indexes...")
        with engine.connect() as conn:
            indexes = [
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resume_user_created ON resume_documents(user_id, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customization_company_job ON resume_customizations(company_name, job_title)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_recipient_status ON email_sends(recipient_email, send_status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_log_level ON processing_logs(log_level, created_at DESC)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    print("   ✅ Index created")
                except Exception as e:
                    print(f"   ⚠️ Index skipped: {str(e)[:50]}...")
            
            conn.commit()
        
        # Insert sample data
        print("📝 Creating sample data...")
        with engine.connect() as conn:
            sample_data = text("""
                INSERT INTO resume_documents (
                    id, filename, original_filename, file_size, 
                    original_content, user_id, processing_status, 
                    created_at, updated_at, is_active, version
                ) VALUES (
                    gen_random_uuid(), 
                    'sample_resume.docx', 
                    'Sample Software Engineer Resume.docx', 
                    45678,
                    'John Doe - Senior Software Engineer with 5+ years experience in Python, JavaScript, React, Django, PostgreSQL, AWS, Docker...',
                    'demo_user_123',
                    'completed',
                    NOW(),
                    NOW(),
                    true,
                    1
                ) ON CONFLICT DO NOTHING
            """)
            
            conn.execute(sample_data)
            conn.commit()
            print("✅ Sample data created!")
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📋 Tables Created:")
        print("✅ resume_documents - Store uploaded resume files")
        print("✅ resume_customizations - Job-specific modifications")
        print("✅ email_sends - Email delivery tracking")
        print("✅ processing_logs - Performance monitoring")
        print("✅ Performance indexes for fast queries")
        print("✅ Sample data for testing")
        
        print("\n🚀 Next Steps:")
        print("1. Test the connection: python -c \"from database.standalone_setup import test_connection; test_connection()\"")
        print("2. Run data flow demo: python database/demo_data_flow.py")
        print("3. Start your app: streamlit run app.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        return False

def test_connection():
    """Test database connection and show sample data"""
    try:
        print("🔍 Testing Database Connection...")
        
        # Load environment variables
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'resume_customizer')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        encoded_password = quote_plus(db_password)
        connection_string = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✅ Database connection successful!")
            
            # Show table counts
            tables = ['resume_documents', 'resume_customizations', 'email_sends', 'processing_logs']
            for table in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
                    print(f"📊 {table}: {count} records")
                except:
                    print(f"⚠️ {table}: table not found")
            
            # Show sample resume data
            sample = conn.execute(text("SELECT filename, user_id, processing_status FROM resume_documents LIMIT 1")).fetchone()
            if sample:
                print(f"📄 Sample resume: {sample[0]} (User: {sample[1]}, Status: {sample[2]})")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    setup_database()

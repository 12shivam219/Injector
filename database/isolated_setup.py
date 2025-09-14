"""
Completely Isolated PostgreSQL Setup for Resume Customizer
No dependencies on other database modules that require alembic
"""

import os
import sys
from sqlalchemy import (
    create_engine, text, Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, Float, MetaData
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from urllib.parse import quote_plus
import uuid

# Create isolated base and metadata
metadata = MetaData()
Base = declarative_base(metadata=metadata)

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

# Global engine and session variables
engine = None
SessionLocal = None

def load_env_variables():
    """Load environment variables from .env file"""
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
    return True

def create_database_connection():
    """Create database connection and engine"""
    global engine, SessionLocal
    
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
    
    try:
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
        
        # Connect to target database
        engine = create_engine(connection_string, pool_size=10, max_overflow=20)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if result[0] != 1:
                raise Exception("Connection test failed")
        
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables():
    """Create all database tables"""
    global engine
    
    try:
        print("📊 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Create basic indexes
        print("📈 Creating performance indexes...")
        with engine.connect() as conn:
            basic_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_resume_user_status ON resume_documents(user_id, processing_status)",
                "CREATE INDEX IF NOT EXISTS idx_customization_company ON resume_customizations(company_name)",
                "CREATE INDEX IF NOT EXISTS idx_email_status ON email_sends(send_status)",
                "CREATE INDEX IF NOT EXISTS idx_processing_level ON processing_logs(log_level)",
            ]
            
            for index_sql in basic_indexes:
                try:
                    conn.execute(text(index_sql))
                    print("   ✅ Index created")
                except Exception as e:
                    print(f"   ⚠️ Index skipped: {str(e)[:50]}...")
            
            conn.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def insert_sample_data():
    """Insert sample data for testing"""
    global engine
    
    try:
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
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to insert sample data: {e}")
        return False

def test_database():
    """Test database connection and show data"""
    global engine
    
    try:
        print("🔍 Testing database functionality...")
        
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✅ Database connection test passed!")
            
            # Show table counts
            tables = ['resume_documents', 'resume_customizations', 'email_sends', 'processing_logs']
            for table in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
                    print(f"📊 {table}: {count} records")
                except Exception as e:
                    print(f"⚠️ {table}: {str(e)[:50]}...")
            
            # Show sample data
            try:
                sample = conn.execute(text("SELECT filename, user_id, processing_status FROM resume_documents LIMIT 1")).fetchone()
                if sample:
                    print(f"📄 Sample resume: {sample[0]} (User: {sample[1]}, Status: {sample[2]})")
                else:
                    print("📄 No sample data found")
            except Exception as e:
                print(f"⚠️ Sample data query failed: {str(e)[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def get_session():
    """Get database session for CRUD operations"""
    global SessionLocal
    if SessionLocal is None:
        raise Exception("Database not initialized. Call setup_database() first.")
    return SessionLocal()

def setup_database():
    """Complete database setup process"""
    print("🔧 Isolated PostgreSQL Database Setup")
    print("=" * 50)
    
    try:
        # Step 1: Load environment variables
        if not load_env_variables():
            return False
        
        # Step 2: Create database connection
        if not create_database_connection():
            return False
        
        # Step 3: Create tables
        if not create_tables():
            return False
        
        # Step 4: Insert sample data
        if not insert_sample_data():
            print("⚠️ Sample data insertion failed, but continuing...")
        
        # Step 5: Test database
        if not test_database():
            print("⚠️ Database test failed, but setup completed...")
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📋 What was created:")
        print("✅ resume_documents - Store uploaded resume files")
        print("✅ resume_customizations - Job-specific modifications")
        print("✅ email_sends - Email delivery tracking")
        print("✅ processing_logs - Performance monitoring")
        print("✅ Performance indexes for fast queries")
        print("✅ Sample data for testing")
        
        print("\n🚀 Next Steps:")
        print("1. Test CRUD operations: python -c \"import database.isolated_setup as db; db.setup_database(); db.demo_crud()\"")
        print("2. Start your Streamlit app: streamlit run app.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def demo_crud():
    """Demonstrate CRUD operations"""
    global engine
    
    print("\n🔄 Demonstrating CRUD Operations")
    print("-" * 40)
    
    try:
        session = get_session()
        
        # CREATE - Insert a new resume document
        print("📝 CREATE: Adding new resume document...")
        new_resume = ResumeDocument(
            filename='demo_resume.docx',
            original_filename='Demo Resume.docx',
            file_size=12345,
            file_hash='demo123456789abcdef',
            original_content='Demo resume content with Python, React, PostgreSQL skills...',
            user_id='demo_user_456',
            processing_status='uploaded'
        )
        session.add(new_resume)
        session.commit()
        print(f"   ✅ Created resume with ID: {new_resume.id}")
        
        # READ - Query resume documents
        print("\n📖 READ: Querying resume documents...")
        resumes = session.query(ResumeDocument).filter(
            ResumeDocument.user_id.like('demo_user_%')
        ).all()
        print(f"   📊 Found {len(resumes)} demo resumes")
        for resume in resumes:
            print(f"   📄 {resume.filename} - Status: {resume.processing_status}")
        
        # UPDATE - Update processing status
        print("\n✏️ UPDATE: Updating processing status...")
        resume_to_update = session.query(ResumeDocument).filter(
            ResumeDocument.filename == 'demo_resume.docx'
        ).first()
        
        if resume_to_update:
            resume_to_update.processing_status = 'completed'
            resume_to_update.processing_completed_at = func.now()
            session.commit()
            print(f"   ✅ Updated resume status to: {resume_to_update.processing_status}")
        
        # CREATE - Add customization
        print("\n🎯 CREATE: Adding resume customization...")
        customization = ResumeCustomization(
            resume_document_id=new_resume.id,
            job_title='Senior Python Developer',
            company_name='Tech Company Inc.',
            tech_stack_input=['Python', 'Django', 'PostgreSQL', 'AWS'],
            customization_status='completed',
            quality_score=0.85,
            match_percentage=78.5
        )
        session.add(customization)
        session.commit()
        print(f"   ✅ Created customization with ID: {customization.id}")
        
        # READ - Query with JOIN
        print("\n🔗 READ: Querying with JOIN...")
        results = session.query(ResumeDocument, ResumeCustomization).join(
            ResumeCustomization
        ).filter(
            ResumeDocument.user_id == 'demo_user_456'
        ).all()
        
        for resume, custom in results:
            print(f"   📄 Resume: {resume.filename}")
            print(f"   🎯 Customization: {custom.company_name} - {custom.job_title}")
            print(f"   📊 Quality Score: {custom.quality_score}")
        
        session.close()
        print("\n✅ CRUD operations completed successfully!")
        
    except Exception as e:
        print(f"❌ CRUD demo failed: {e}")

if __name__ == "__main__":
    if setup_database():
        demo_crud()

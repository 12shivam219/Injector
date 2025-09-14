"""
Database Setup and Migration Script for Resume Customizer
Creates all tables, indexes, and initial data for PostgreSQL database
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_connection_string, setup_database_environment
from database.connection import initialize_database
from database.models import Base, Requirement, RequirementComment, RequirementConsultant
from database.resume_models import (
    ResumeDocument, ResumeCustomization, EmailSend, 
    ProcessingLog, UserSession
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_tables():
    """
    Create all database tables and indexes
    """
    try:
        print("🔧 Creating database tables...")
        
        # Setup environment
        setup_result = setup_database_environment()
        if not setup_result['success']:
            print("❌ Database environment setup failed!")
            return False
        
        # Get connection string and create engine
        connection_string = get_connection_string()
        engine = create_engine(connection_string)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create materialized views
        with engine.connect() as conn:
            # Create requirement summary materialized view
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS requirement_summary_view AS
                SELECT 
                    r.id,
                    r.req_status,
                    r.applied_for,
                    r.client_company,
                    r.job_title,
                    r.primary_tech_stack,
                    COALESCE(array_length(r.tech_stack, 1), 0) as tech_stack_count,
                    COALESCE(comment_counts.comment_count, 0) as comment_count,
                    COALESCE(consultant_counts.consultant_count, 0) as consultant_count,
                    r.created_at,
                    r.updated_at,
                    EXTRACT(days FROM (NOW() - r.created_at))::integer as days_since_created,
                    CASE r.req_status
                        WHEN 'New' THEN 1
                        WHEN 'Working' THEN 2
                        WHEN 'Applied' THEN 3
                        WHEN 'Submitted' THEN 4
                        WHEN 'Interviewed' THEN 5
                        WHEN 'On Hold' THEN 6
                        WHEN 'Cancelled' THEN 7
                        ELSE 0
                    END as status_priority
                FROM requirements r
                LEFT JOIN (
                    SELECT requirement_id, COUNT(*) as comment_count
                    FROM requirement_comments
                    WHERE is_active = true
                    GROUP BY requirement_id
                ) comment_counts ON r.id = comment_counts.requirement_id
                LEFT JOIN (
                    SELECT requirement_id, COUNT(*) as consultant_count
                    FROM requirement_consultants
                    WHERE is_active = true
                    GROUP BY requirement_id
                ) consultant_counts ON r.id = consultant_counts.requirement_id
                WHERE r.is_active = true;
            """))
            
            # Create resume analytics materialized view
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS resume_analytics_view AS
                SELECT 
                    gen_random_uuid() as id,
                    DATE(rd.created_at) as date,
                    COUNT(DISTINCT rd.id) as total_resumes,
                    COUNT(DISTINCT rc.id) as total_customizations,
                    COUNT(DISTINCT es.id) as total_emails_sent,
                    AVG(rc.processing_time_seconds) as avg_processing_time,
                    AVG(rc.quality_score) as avg_quality_score,
                    (COUNT(DISTINCT CASE WHEN rc.customization_status = 'completed' THEN rc.id END)::float / 
                     NULLIF(COUNT(DISTINCT rc.id), 0) * 100) as success_rate,
                    jsonb_agg(DISTINCT rc.tech_stack_input) FILTER (WHERE rc.tech_stack_input IS NOT NULL) as popular_tech_stacks,
                    jsonb_agg(DISTINCT rc.company_name) FILTER (WHERE rc.company_name IS NOT NULL) as top_companies
                FROM resume_documents rd
                LEFT JOIN resume_customizations rc ON rd.id = rc.resume_document_id
                LEFT JOIN email_sends es ON rc.id = es.customization_id
                WHERE rd.is_active = true
                GROUP BY DATE(rd.created_at);
            """))
            
            conn.commit()
        
        print("✅ Database tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False

def create_indexes():
    """
    Create additional performance indexes
    """
    try:
        print("📊 Creating performance indexes...")
        
        connection_string = get_connection_string()
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Additional indexes for better performance
            indexes = [
                # Resume document indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resume_user_created ON resume_documents(user_id, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resume_status_created ON resume_documents(processing_status, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resume_hash ON resume_documents(file_hash)",
                
                # Customization indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customization_company_job ON resume_customizations(company_name, job_title)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customization_quality ON resume_customizations(quality_score DESC) WHERE quality_score IS NOT NULL",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customization_tech_stack ON resume_customizations USING GIN(tech_stack_input)",
                
                # Email indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_recipient_status ON email_sends(recipient_email, send_status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_sent_date ON email_sends(sent_at DESC) WHERE sent_at IS NOT NULL",
                
                # Processing log indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_log_level_time ON processing_logs(log_level, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_log_step ON processing_logs(step_name, created_at DESC)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    print(f"   ✅ Created index")
                except Exception as e:
                    print(f"   ⚠️ Index creation skipped (may already exist): {str(e)[:50]}...")
            
            conn.commit()
        
        print("✅ Performance indexes created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        return False

def insert_sample_data():
    """
    Insert sample data for testing
    """
    try:
        print("📝 Inserting sample data...")
        
        from database.crud_operations import ResumeCRUDOperations
        crud_ops = ResumeCRUDOperations()
        
        # Sample resume data
        sample_resume = {
            'filename': 'sample_resume.docx',
            'original_filename': 'Sample Software Engineer Resume.docx',
            'file_size': 52341,
            'file_hash': 'sample123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
            'original_content': '''
            Sample User
            Senior Software Engineer
            
            EXPERIENCE:
            • 7+ years of full-stack development experience
            • Expert in Python, JavaScript, and cloud technologies
            • Led teams of 5+ developers on enterprise projects
            • Designed and implemented microservices architecture
            
            TECHNICAL SKILLS:
            • Languages: Python, JavaScript, Java, Go
            • Frameworks: Django, React, Node.js, Spring Boot
            • Databases: PostgreSQL, MongoDB, Redis
            • Cloud: AWS, Docker, Kubernetes, Terraform
            • Tools: Git, Jenkins, Jira, Confluence
            ''',
            'user_id': 'sample_user_001',
            'session_id': 'sample_session_001'
        }
        
        resume_id = crud_ops.create_resume_document(sample_resume)
        if resume_id:
            print(f"   ✅ Sample resume created: {resume_id}")
            
            # Update to completed status
            crud_ops.update_resume_processing_status(resume_id, 'completed')
            
            # Create sample customizations
            customizations = [
                {
                    'resume_document_id': resume_id,
                    'job_title': 'Senior Backend Developer',
                    'company_name': 'Tech Giants Inc.',
                    'tech_stack_input': ['Python', 'Django', 'PostgreSQL', 'AWS'],
                    'processing_time_seconds': 3.2
                },
                {
                    'resume_document_id': resume_id,
                    'job_title': 'Full Stack Engineer',
                    'company_name': 'Innovation Labs',
                    'tech_stack_input': ['JavaScript', 'React', 'Node.js', 'MongoDB'],
                    'processing_time_seconds': 2.8
                }
            ]
            
            for custom_data in customizations:
                custom_id = crud_ops.create_customization(custom_data)
                if custom_id:
                    print(f"   ✅ Sample customization created: {custom_id}")
                    crud_ops.update_customization_quality(custom_id, 0.87, 82.5)
        
        print("✅ Sample data inserted successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to insert sample data: {e}")
        return False

def main():
    """
    Main setup function
    """
    print("🚀 PostgreSQL Database Setup for Resume Customizer")
    print("=" * 60)
    
    try:
        # Step 1: Create tables
        if not create_database_tables():
            print("❌ Database setup failed at table creation")
            return False
        
        # Step 2: Create indexes
        if not create_indexes():
            print("⚠️ Database setup completed but some indexes failed")
        
        # Step 3: Insert sample data
        if not insert_sample_data():
            print("⚠️ Database setup completed but sample data insertion failed")
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📋 What was created:")
        print("✅ All database tables with proper relationships")
        print("✅ Performance indexes for fast queries")
        print("✅ Materialized views for analytics")
        print("✅ Sample data for testing")
        
        print("\n🔗 Next steps:")
        print("1. Run the demo script: python database/demo_data_flow.py")
        print("2. Start your Streamlit application")
        print("3. Upload resumes and test the functionality")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    main()

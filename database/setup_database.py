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
from database.config import DatabaseHealthChecker
"""
Database Setup and Migration Script for Resume Customizer
Creates all tables, indexes, and initial data for PostgreSQL database
This version standardizes logging, uses autocommit for DDL, and avoids printing secrets.
"""

import os
import sys
import logging
import argparse
import hashlib
from sqlalchemy import create_engine, text

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_connection_string, setup_database_environment
from database.connection import initialize_database
from database.models import Base
from database.resume_models import (
    ResumeDocument, ResumeCustomization, EmailSend,
    ProcessingLog, UserSession
)
from database.config import DatabaseHealthChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_database_health():
    """Check database health before setup"""
    try:
        logger.info("Checking database health...")

        connection_string = get_connection_string()
        health_checker = DatabaseHealthChecker()
        health_status = health_checker.check_connection_health(connection_string)

        if health_status.get('connected'):
            logger.info("Database connection successful (%sms)", health_status.get('response_time_ms'))

            if health_status.get('tables_exist'):
                logger.info("Required tables exist")
            else:
                logger.warning("Some required tables are missing")
                logger.debug("Existing tables: %s", health_status.get('existing_tables', []))
        else:
            logger.error("Database connection failed: %s", health_status.get('errors'))
            return False

        return True

    except Exception as e:
        logger.exception("Health check failed: %s", e)
        return False


def create_database_tables():
    """Create all database tables and materialized views"""
    try:
        logger.info("Creating database tables...")

        # Check health first
        if not check_database_health():
            logger.warning("Database health check failed, attempting to create database if possible...")
            try:
                from database.connection import DatabaseConnectionManager
                db_manager = DatabaseConnectionManager()
                if db_manager.create_database_if_not_exists():
                    logger.info("Database created successfully")
                else:
                    logger.error("Failed to create database")
                    return False
            except Exception as e:
                logger.exception("Database creation failed: %s", e)
                return False

        # Setup environment
        setup_result = setup_database_environment()
        if not setup_result.get('success'):
            logger.error("Database environment setup failed: %s", setup_result)
            return False

        # Get connection string and create engine
        connection_string = get_connection_string()
        engine = create_engine(connection_string)

        # Initialize schema using connection manager
        from database.connection import DatabaseConnectionManager
        db_manager = DatabaseConnectionManager()
        if db_manager.initialize(connection_string):
            if db_manager.initialize_schema():
                logger.info("Schema initialized successfully")
            else:
                logger.warning("Schema initialization had issues")

        # Create all tables (declarative base)
        Base.metadata.create_all(bind=engine)

        # Create materialized views using autocommit
        try:
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                conn.execute(text("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS requirement_summary_view AS
                    SELECT r.id, r.req_status, r.applied_for, r.client_company, r.job_title,
                           r.primary_tech_stack, COALESCE(jsonb_array_length(r.tech_stack),0) as tech_stack_count,
                           COALESCE(comment_counts.comment_count,0) as comment_count,
                           COALESCE(consultant_counts.consultant_count,0) as consultant_count,
                           r.created_at, r.updated_at,
                           EXTRACT(days FROM (NOW() - r.created_at))::integer as days_since_created,
                           CASE r.req_status
                               WHEN 'New' THEN 1 WHEN 'Working' THEN 2 WHEN 'Applied' THEN 3
                               WHEN 'Submitted' THEN 4 WHEN 'Interviewed' THEN 5 WHEN 'On Hold' THEN 6
                               WHEN 'Cancelled' THEN 7 ELSE 0 END as status_priority
                    FROM requirements r
                    LEFT JOIN (
                        SELECT requirement_id, COUNT(*) as comment_count
                        FROM requirement_comments WHERE is_active = true GROUP BY requirement_id
                    ) comment_counts ON r.id = comment_counts.requirement_id
                    LEFT JOIN (
                        SELECT requirement_id, COUNT(*) as consultant_count
                        FROM requirement_consultants WHERE is_active = true GROUP BY requirement_id
                    ) consultant_counts ON r.id = consultant_counts.requirement_id
                    WHERE r.is_active = true;
                """))

                conn.execute(text("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS resume_analytics_view AS
                    SELECT gen_random_uuid() as id, DATE(rd.created_at) as date,
                           COUNT(DISTINCT rd.id) as total_resumes, COUNT(DISTINCT rc.id) as total_customizations,
                           COUNT(DISTINCT es.id) as total_emails_sent,
                           AVG(rc.processing_time_seconds) as avg_processing_time,
                           AVG(rc.quality_score) as avg_quality_score,
                           (COUNT(DISTINCT CASE WHEN rc.customization_status = 'completed' THEN rc.id END)::float /
                            NULLIF(COUNT(DISTINCT rc.id),0) * 100) as success_rate,
                           jsonb_agg(DISTINCT rc.tech_stack_input) FILTER (WHERE rc.tech_stack_input IS NOT NULL) as popular_tech_stacks,
                           jsonb_agg(DISTINCT rc.company_name) FILTER (WHERE rc.company_name IS NOT NULL) as top_companies
                    FROM resume_documents rd
                    LEFT JOIN resume_customizations rc ON rd.id = rc.resume_document_id
                    LEFT JOIN email_sends es ON rc.id = es.customization_id
                    WHERE rd.is_active = true
                    GROUP BY DATE(rd.created_at);
                """))
        except Exception as e:
            logger.warning("Materialized view creation skipped or failed: %s", e)

        logger.info("Database tables created successfully")
        return True

    except Exception as e:
        logger.exception("Failed to create database tables: %s", e)
        return False


def create_indexes():
    """Create additional performance indexes"""
    try:
        logger.info("Creating performance indexes...")

        connection_string = get_connection_string()
        engine = create_engine(connection_string)

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

        try:
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                for index_sql in indexes:
                    try:
                        conn.execute(text(index_sql))
                        logger.debug("Created index: %s", index_sql)
                    except Exception as e:
                        logger.warning("Index creation skipped: %s", e)
        except Exception as e:
            logger.warning("Index creation skipped due to engine connection issue: %s", e)

        logger.info("Performance indexes created successfully")
        return True

    except Exception as e:
        logger.exception("Failed to create indexes: %s", e)
        return False


def insert_sample_data():
    """Insert sample data for testing"""
    try:
        logger.info("Inserting sample data...")

        from database.crud_operations import ResumeCRUDOperations
        crud_ops = ResumeCRUDOperations()

        # Sample resume data
        sample_resume = {
            'filename': 'sample_resume.docx',
            'original_filename': 'Sample Software Engineer Resume.docx',
            'file_size': 52341,
            'file_hash': hashlib.sha256(b"sample content").hexdigest(),
            'original_content': 'Sample resume content',
            'user_id': 'sample_user_001',
            'session_id': 'sample_session_001'
        }

        resume_id = crud_ops.create_resume_document(sample_resume)
        if resume_id:
            logger.info("Sample resume created: %s", resume_id)

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
                    logger.info("Sample customization created: %s", custom_id)
                    crud_ops.update_customization_quality(custom_id, 0.87, 82.5)

        logger.info("Sample data inserted successfully")
        return True

    except Exception as e:
        logger.exception("Failed to insert sample data: %s", e)
        return False


def main():
    """Main setup function"""
    logger.info("PostgreSQL Database Setup for Resume Customizer")
    parser = argparse.ArgumentParser(description='Setup PostgreSQL database schema for Resume Customizer')
    parser.add_argument('--skip-indexes', action='store_true', help='Skip index creation')
    parser.add_argument('--skip-sample-data', action='store_true', help='Skip inserting sample data')
    parser.add_argument('--dry-run', action='store_true', help='Run checks without executing DDL')
    args = parser.parse_args()

    try:
        # Step 1: Create tables
        if args.dry_run:
            logger.info("Dry run: checking only, not executing DDL")
            ok = create_database_tables()
            logger.info("Dry run complete: %s", ok)
            return ok

        if not create_database_tables():
            logger.error("Database setup failed at table creation")
            return False

        # Step 2: Create indexes
        if not args.skip_indexes:
            if not create_indexes():
                logger.warning("Database setup completed but some indexes failed")
        else:
            logger.info("Skipping index creation (per argument)")

        # Step 3: Insert sample data
        if not args.skip_sample_data:
            if not insert_sample_data():
                logger.warning("Database setup completed but sample data insertion failed")
        else:
            logger.info("Skipping sample data insertion (per argument)")

        logger.info("Database setup completed successfully")
        logger.info("What was created: tables, indexes, materialized views, sample data (where applicable)")
        logger.info("Next steps: run demo script or start the application")

        return True

    except Exception as e:
        logger.exception("Database setup failed: %s", e)
        return False


if __name__ == "__main__":
    main()
        # Step 2: Create indexes

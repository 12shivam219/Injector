"""
Database Migration System for Resume Customizer
Handles database schema creation, updates, and data migrations
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import text, inspect, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext

from .models import Base, Requirement, RequirementComment, RequirementConsultant, DatabaseStats, AuditLog
from .connection import get_db_session, db_manager

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """
    Advanced database migration system with schema management
    """
    
    def __init__(self):
        self.metadata = Base.metadata
        
    def create_all_tables(self) -> bool:
        """
        Create all database tables with optimizations
        """
        try:
            with get_db_session() as session:
                # Create tables
                Base.metadata.create_all(bind=session.bind)
                
                # Create enhanced tables if they don't exist
                self._create_enhanced_tables(session)
                
                # Create materialized view for performance
                self._create_materialized_view(session)
                
                # Create additional indexes
                self._create_additional_indexes(session)
                
                # Create triggers for audit logging
                self._create_audit_triggers(session)
                
                # Initialize database statistics
                self._initialize_stats(session)
                
                session.commit()
                
            logger.info("✅ All database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    def _create_enhanced_tables(self, session):
        """Create enhanced tables and columns"""
        try:
            # Add new columns to existing requirements table if they don't exist
            enhanced_columns = [
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS required_skills JSONB DEFAULT '[]'::jsonb",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS nice_to_have_skills JSONB DEFAULT '[]'::jsonb",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS job_location VARCHAR(255)",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS remote_option BOOLEAN DEFAULT FALSE",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS salary_range_min BIGINT",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS salary_range_max BIGINT",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD'",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS application_deadline TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS application_status VARCHAR(50) DEFAULT 'Not Applied'",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS application_date TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS follow_up_date TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS priority_score INTEGER DEFAULT 5",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS match_score FLOAT",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS source_url TEXT",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS referral_source VARCHAR(255)",
                "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb"
            ]
            
            for column_sql in enhanced_columns:
                try:
                    session.execute(text(column_sql))
                except Exception as e:
                    logger.debug(f"Column addition skipped (may already exist): {e}")
            
            # Create indexes for new columns
            enhanced_indexes = [
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_priority_status ON requirements (priority_score, req_status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_location_remote ON requirements (job_location, remote_option)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_salary_range ON requirements (salary_range_min, salary_range_max)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_application_tracking ON requirements (application_status, application_date)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_tags_gin ON requirements USING gin(tags)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_req_required_skills_gin ON requirements USING gin(required_skills)"
            ]
            
            for index_sql in enhanced_indexes:
                try:
                    session.execute(text(index_sql))
                except Exception as e:
                    logger.debug(f"Index creation skipped: {e}")
            
            logger.info("✅ Enhanced database schema applied")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create enhanced tables: {e}")
    
    def _create_materialized_view(self, session):
        """Create materialized view for high-performance queries"""
        
        materialized_view_sql = '''
        CREATE MATERIALIZED VIEW IF NOT EXISTS requirement_summary_view AS
        SELECT 
            r.id,
            r.req_status,
            r.applied_for,
            r.client_company,
            r.job_title,
            r.primary_tech_stack,
            jsonb_array_length(COALESCE(r.tech_stack, '[]'::jsonb)) as tech_stack_count,
            COALESCE(comment_counts.count, 0) as comment_count,
            COALESCE(consultant_counts.count, 0) as consultant_count,
            r.created_at,
            r.updated_at,
            EXTRACT(DAY FROM (NOW() - r.created_at)) as days_since_created,
            CASE r.req_status
                WHEN 'New' THEN 1
                WHEN 'Working' THEN 2
                WHEN 'Applied' THEN 3
                WHEN 'Submitted' THEN 4
                WHEN 'Interviewed' THEN 5
                WHEN 'On Hold' THEN 6
                WHEN 'Cancelled' THEN 7
                ELSE 8
            END as status_priority
        FROM requirements r
        LEFT JOIN (
            SELECT requirement_id, COUNT(*) as count 
            FROM requirement_comments 
            WHERE is_active = true
            GROUP BY requirement_id
        ) comment_counts ON r.id = comment_counts.requirement_id
        LEFT JOIN (
            SELECT requirement_id, COUNT(*) as count 
            FROM requirement_consultants 
            WHERE is_active = true
            GROUP BY requirement_id
        ) consultant_counts ON r.id = consultant_counts.requirement_id
        WHERE r.is_active = true;
        '''
        
        # Create unique index on materialized view
        index_sql = '''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_req_summary_view_id 
        ON requirement_summary_view (id);
        '''
        
        # Create additional indexes for common queries
        additional_indexes_sql = [
            'CREATE INDEX IF NOT EXISTS idx_req_summary_status ON requirement_summary_view (req_status);',
            'CREATE INDEX IF NOT EXISTS idx_req_summary_applied_for ON requirement_summary_view (applied_for);',
            'CREATE INDEX IF NOT EXISTS idx_req_summary_client ON requirement_summary_view (client_company);',
            'CREATE INDEX IF NOT EXISTS idx_req_summary_created ON requirement_summary_view (created_at DESC);',
            'CREATE INDEX IF NOT EXISTS idx_req_summary_priority ON requirement_summary_view (status_priority, created_at DESC);'
        ]
        
        try:
            session.execute(text(materialized_view_sql))
            session.execute(text(index_sql))
            
            for index_sql in additional_indexes_sql:
                session.execute(text(index_sql))
                
            logger.info("✅ Materialized view created successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create materialized view: {e}")
    
    def _create_additional_indexes(self, session):
        """Create additional performance indexes"""
        
        additional_indexes = [
            # Full-text search index for job descriptions
            '''CREATE INDEX IF NOT EXISTS idx_job_description_fts 
               ON requirements USING gin(to_tsvector('english', complete_job_description))''',
            
            # Composite index for common search patterns
            '''CREATE INDEX IF NOT EXISTS idx_requirements_search_composite 
               ON requirements (req_status, applied_for, client_company, created_at DESC)''',
            
            # Index for tech stack queries
            '''CREATE INDEX IF NOT EXISTS idx_tech_stack_search 
               ON requirements USING gin(tech_stack jsonb_ops)''',
            
            # Index for vendor information
            '''CREATE INDEX IF NOT EXISTS idx_vendor_search 
               ON requirements (vendor_company, vendor_person_name) WHERE vendor_company IS NOT NULL''',
            
            # Partial index for active requirements only
            '''CREATE INDEX IF NOT EXISTS idx_active_requirements 
               ON requirements (created_at DESC) WHERE is_active = true''',
        ]
        
        for index_sql in additional_indexes:
            try:
                session.execute(text(index_sql))
            except Exception as e:
                logger.warning(f"⚠️ Failed to create index: {e}")
        
        logger.info("✅ Additional indexes created")
    
    def _create_audit_triggers(self, session):
        """Create audit triggers for automatic change tracking"""
        
        # Create audit function
        audit_function_sql = '''
        CREATE OR REPLACE FUNCTION audit_trigger_function()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO audit_logs (
                    table_name, record_id, operation, new_values, 
                    user_id, session_id, created_at
                ) VALUES (
                    TG_TABLE_NAME, NEW.id, TG_OP, row_to_json(NEW)::jsonb,
                    current_setting('app.user_id', true), 
                    current_setting('app.session_id', true),
                    NOW()
                );
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO audit_logs (
                    table_name, record_id, operation, old_values, new_values,
                    user_id, session_id, created_at
                ) VALUES (
                    TG_TABLE_NAME, NEW.id, TG_OP, 
                    row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb,
                    current_setting('app.user_id', true), 
                    current_setting('app.session_id', true),
                    NOW()
                );
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                INSERT INTO audit_logs (
                    table_name, record_id, operation, old_values,
                    user_id, session_id, created_at
                ) VALUES (
                    TG_TABLE_NAME, OLD.id, TG_OP, row_to_json(OLD)::jsonb,
                    current_setting('app.user_id', true), 
                    current_setting('app.session_id', true),
                    NOW()
                );
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        '''
        
        # Create triggers for each table
        trigger_sqls = [
            '''CREATE OR REPLACE TRIGGER requirements_audit_trigger
               AFTER INSERT OR UPDATE OR DELETE ON requirements
               FOR EACH ROW EXECUTE FUNCTION audit_trigger_function()''',
               
            '''CREATE OR REPLACE TRIGGER requirement_comments_audit_trigger
               AFTER INSERT OR UPDATE OR DELETE ON requirement_comments
               FOR EACH ROW EXECUTE FUNCTION audit_trigger_function()''',
               
            '''CREATE OR REPLACE TRIGGER requirement_consultants_audit_trigger
               AFTER INSERT OR UPDATE OR DELETE ON requirement_consultants
               FOR EACH ROW EXECUTE FUNCTION audit_trigger_function()'''
        ]
        
        try:
            session.execute(text(audit_function_sql))
            for trigger_sql in trigger_sqls:
                session.execute(text(trigger_sql))
            logger.info("✅ Audit triggers created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create audit triggers: {e}")
    
    def _initialize_stats(self, session):
        """Initialize database statistics tracking"""
        
        initial_stats = [
            {
                'stat_name': 'total_requirements',
                'stat_value': {'count': 0, 'last_updated': datetime.now().isoformat()},
                'category': 'counts',
                'description': 'Total number of requirements in the system'
            },
            {
                'stat_name': 'database_version',
                'stat_value': {'version': '1.0.0', 'created_at': datetime.now().isoformat()},
                'category': 'system',
                'description': 'Database schema version'
            },
            {
                'stat_name': 'performance_metrics',
                'stat_value': {
                    'query_performance': {},
                    'connection_stats': {},
                    'last_optimization': None
                },
                'category': 'performance',
                'description': 'Database performance tracking'
            }
        ]
        
        try:
            for stat in initial_stats:
                # Check if stat already exists
                existing = session.query(DatabaseStats).filter_by(
                    stat_name=stat['stat_name']
                ).first()
                
                if not existing:
                    db_stat = DatabaseStats(**stat)
                    session.add(db_stat)
            
            logger.info("✅ Database statistics initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize stats: {e}")
    
    def refresh_materialized_view(self) -> bool:
        """Refresh materialized view for updated statistics"""
        try:
            with get_db_session() as session:
                session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY requirement_summary_view"))
                session.commit()
            
            logger.info("✅ Materialized view refreshed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh materialized view: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information"""
        info = {
            'tables': [],
            'indexes': [],
            'views': [],
            'statistics': {}
        }
        
        try:
            with get_db_session() as session:
                # Get table information
                inspector = inspect(session.bind)
                
                for table_name in inspector.get_table_names():
                    table_info = {
                        'name': table_name,
                        'columns': len(inspector.get_columns(table_name)),
                        'indexes': len(inspector.get_indexes(table_name)),
                        'foreign_keys': len(inspector.get_foreign_keys(table_name))
                    }
                    
                    # Get row count
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()
                        table_info['row_count'] = result[0] if result else 0
                    except:
                        table_info['row_count'] = 0
                    
                    info['tables'].append(table_info)
                
                # Get database statistics
                stats_query = '''
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                '''
                
                result = session.execute(text(stats_query)).fetchall()
                for row in result:
                    info['statistics'][row.tablename] = {
                        'inserts': row.inserts,
                        'updates': row.updates,
                        'deletes': row.deletes,
                        'live_tuples': row.live_tuples,
                        'dead_tuples': row.dead_tuples
                    }
                
        except Exception as e:
            logger.error(f"❌ Failed to get database info: {e}")
        
        return info
    
    def vacuum_analyze(self) -> bool:
        """Perform database maintenance"""
        try:
            with get_db_session() as session:
                # Run VACUUM ANALYZE on all tables
                tables = ['requirements', 'requirement_comments', 'requirement_consultants']
                
                for table in tables:
                    session.execute(text(f"VACUUM ANALYZE {table}"))
                
                session.commit()
            
            # Refresh materialized view
            self.refresh_materialized_view()
            
            logger.info("✅ Database maintenance completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database maintenance failed: {e}")
            return False
    
    def backup_schema(self, file_path: str) -> bool:
        """Create a schema backup"""
        try:
            with get_db_session() as session:
                # Get schema definition
                schema_sql = '''
                SELECT 
                    'CREATE TABLE ' || schemaname||'.'||tablename||' (' || 
                    string_agg(column_name||' '||data_type||
                        case when character_maximum_length is not null 
                        then '('||character_maximum_length||')' else '' end ||
                        case when is_nullable = 'NO' then ' NOT NULL' else '' end, ', ') 
                    || ');' as ddl
                FROM information_schema.tables t
                JOIN information_schema.columns c ON c.table_name = t.table_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                GROUP BY schemaname, tablename;
                '''
                
                result = session.execute(text(schema_sql)).fetchall()
                
                with open(file_path, 'w') as f:
                    f.write("-- Database Schema Backup\n")
                    f.write(f"-- Generated at: {datetime.now()}\n\n")
                    
                    for row in result:
                        f.write(row.ddl + "\n\n")
                
            logger.info(f"✅ Schema backup created: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema backup failed: {e}")
            return False

# Global migrator instance
migrator = DatabaseMigrator()

def initialize_database_schema() -> bool:
    """Initialize complete database schema"""
    return migrator.create_all_tables()

def refresh_database_views() -> bool:
    """Refresh materialized views"""
    return migrator.refresh_materialized_view()

def get_database_information() -> Dict[str, Any]:
    """Get comprehensive database information"""
    return migrator.get_database_info()

def perform_database_maintenance() -> bool:
    """Perform routine database maintenance"""
    return migrator.vacuum_analyze()



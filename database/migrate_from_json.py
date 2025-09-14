"""
Data Migration Utility for Resume Customizer
Migrate data from JSON file storage to PostgreSQL database
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .connection import initialize_database, get_db_session
# Optional import - migrations module requires alembic
try:
    from .migrations import initialize_database_schema
    MIGRATIONS_AVAILABLE = True
except ImportError:
    MIGRATIONS_AVAILABLE = False
    def initialize_database_schema():
        return {"success": False, "message": "Migrations module not available"}
# Optional import - requirements_manager_db might have circular dependencies
try:
    from .requirements_manager_db import PostgreSQLRequirementsManager
    REQUIREMENTS_MANAGER_AVAILABLE = True
except ImportError:
    REQUIREMENTS_MANAGER_AVAILABLE = False
    class PostgreSQLRequirementsManager:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class JSONToPostgreSQLMigrator:
    """
    Utility to migrate data from JSON file storage to PostgreSQL database
    """
    
    def __init__(self, json_file_path: str = "requirements.json"):
        self.json_file_path = json_file_path
        self.pg_manager = PostgreSQLRequirementsManager()
        self.migration_stats = {
            'total_found': 0,
            'successfully_migrated': 0,
            'failed_migrations': 0,
            'errors': []
        }
    
    def migrate_all_data(self, backup_json: bool = True) -> Dict[str, Any]:
        """
        Complete migration from JSON to PostgreSQL
        
        Args:
            backup_json: Whether to create a backup of the JSON file
            
        Returns:
            Dict containing migration results
        """
        try:
            logger.info("🚀 Starting complete migration from JSON to PostgreSQL")
            
            # Step 1: Initialize database
            if not self._initialize_database():
                return {
                    'success': False,
                    'error': 'Failed to initialize database',
                    'stats': self.migration_stats
                }
            
            # Step 2: Load JSON data
            json_data = self._load_json_data()
            if not json_data:
                return {
                    'success': False,
                    'error': 'No JSON data found to migrate',
                    'stats': self.migration_stats
                }
            
            # Step 3: Backup JSON file if requested
            if backup_json:
                self._backup_json_file()
            
            # Step 4: Migrate requirements
            requirements_data = json_data.get('requirements', {})
            if isinstance(requirements_data, dict):
                self.migration_stats['total_found'] = len(requirements_data)
                
                for req_id, req_data in requirements_data.items():
                    try:
                        self._migrate_single_requirement(req_data)
                        self.migration_stats['successfully_migrated'] += 1
                        
                        if self.migration_stats['successfully_migrated'] % 10 == 0:
                            logger.info(f"✅ Migrated {self.migration_stats['successfully_migrated']} requirements so far...")
                    
                    except Exception as e:
                        error_msg = f"Failed to migrate requirement {req_id}: {e}"
                        logger.error(error_msg)
                        self.migration_stats['failed_migrations'] += 1
                        self.migration_stats['errors'].append(error_msg)
            
            # Step 5: Verify migration
            verification_result = self._verify_migration()
            
            # Step 6: Final report
            success = (self.migration_stats['successfully_migrated'] > 0 and 
                      self.migration_stats['failed_migrations'] == 0)
            
            result = {
                'success': success,
                'stats': self.migration_stats,
                'verification': verification_result,
                'database_url': self._get_database_info()
            }
            
            if success:
                logger.info(f"🎉 Migration completed successfully! Migrated {self.migration_stats['successfully_migrated']} requirements")
            else:
                logger.warning(f"⚠️ Migration completed with issues. Success: {self.migration_stats['successfully_migrated']}, Failed: {self.migration_stats['failed_migrations']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.migration_stats
            }
    
    def _initialize_database(self) -> bool:
        """Initialize PostgreSQL database and schema"""
        try:
            # Initialize database connection
            if not initialize_database():
                logger.error("❌ Failed to initialize database connection")
                return False
            
            # Create database schema
            if not initialize_database_schema():
                logger.error("❌ Failed to initialize database schema")
                return False
            
            logger.info("✅ Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def _load_json_data(self) -> Optional[Dict[str, Any]]:
        """Load data from JSON file"""
        try:
            json_path = Path(self.json_file_path)
            if not json_path.exists():
                logger.warning(f"⚠️ JSON file not found: {self.json_file_path}")
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✅ Loaded JSON data from {self.json_file_path}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON format: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load JSON data: {e}")
            return None
    
    def _backup_json_file(self) -> bool:
        """Create backup of JSON file"""
        try:
            json_path = Path(self.json_file_path)
            if json_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = json_path.parent / f"requirements_backup_{timestamp}.json"
                
                import shutil
                shutil.copy2(json_path, backup_path)
                
                logger.info(f"✅ JSON backup created: {backup_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to backup JSON file: {e}")
            return False
    
    def _migrate_single_requirement(self, req_data: Dict[str, Any]) -> str:
        """
        Migrate a single requirement from JSON format to PostgreSQL
        
        Args:
            req_data: Requirement data from JSON
            
        Returns:
            str: Created requirement ID
        """
        # Transform JSON data to new format
        transformed_data = self._transform_requirement_data(req_data)
        
        # Create requirement using PostgreSQL manager
        requirement_id = self.pg_manager.create_requirement(
            transformed_data, 
            user_id='system_migration'
        )
        
        return requirement_id
    
    def _transform_requirement_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform JSON requirement data to PostgreSQL format
        
        Args:
            json_data: Original JSON requirement data
            
        Returns:
            Dict: Transformed data for PostgreSQL
        """
        # Handle legacy field mappings
        transformed = {
            # Map old fields to new structure
            'req_status': json_data.get('req_status', json_data.get('status', 'New')),
            'applied_for': json_data.get('applied_for', 'Raju'),
            'next_step': json_data.get('next_step', json_data.get('next_steps', '')),
            'rate': json_data.get('rate', ''),
            'tax_type': json_data.get('tax_type', 'C2C'),
            'client_company': json_data.get('client_company', json_data.get('client', '')),
            'prime_vendor_company': json_data.get('prime_vendor_company', json_data.get('prime_vendor', '')),
            
            # Vendor details
            'vendor_details': {},
            
            # Job requirement info
            'job_requirement_info': {
                'requirement_entered_date': self._parse_date(json_data.get('created_at')),
                'got_requirement_from': 'Got from online resume',
                'tech_stack': [],
                'job_title': json_data.get('job_title', ''),
                'job_portal_link': '',
                'primary_tech_stack': '',
                'complete_job_description': ''
            },
            
            # Comments
            'marketing_comments': [],
            
            # Consultants
            'consultants': json_data.get('consultants', []),
            
            # Interview info
            'interview_id': json_data.get('interview_id'),
            
            # Legacy compatibility
            'job_title': json_data.get('job_title', ''),
            'client': json_data.get('client', ''),
            'prime_vendor': json_data.get('prime_vendor', ''),
            'status': json_data.get('status', 'New'),
            'next_steps': json_data.get('next_steps', ''),
            'vendor_info': json_data.get('vendor_info', {})
        }
        
        # Handle vendor information
        vendor_info = json_data.get('vendor_info', {})
        if vendor_info:
            transformed['vendor_details'] = {
                'vendor_company': vendor_info.get('company', ''),
                'vendor_person_name': vendor_info.get('name', ''),
                'vendor_phone_number': vendor_info.get('phone', ''),
                'vendor_email': vendor_info.get('email', '')
            }
        
        # Handle new structured data if present
        if 'vendor_details' in json_data:
            transformed['vendor_details'].update(json_data['vendor_details'])
        
        if 'job_requirement_info' in json_data:
            transformed['job_requirement_info'].update(json_data['job_requirement_info'])
        
        # Handle marketing comments
        comments = json_data.get('marketing_comments', [])
        if comments:
            transformed['marketing_comments'] = comments
        
        # Ensure consultants is a list
        consultants = json_data.get('consultants', [])
        if not isinstance(consultants, list):
            consultants = []
        transformed['consultants'] = consultants
        
        return transformed
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse date string and return ISO format"""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If no format matches, return current time
            return datetime.now().isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def _verify_migration(self) -> Dict[str, Any]:
        """Verify the migration was successful"""
        try:
            # Get statistics from PostgreSQL
            stats = self.pg_manager.get_statistics()
            
            # Get database health
            health = self.pg_manager.get_database_health()
            
            # Get a sample requirement to verify structure
            sample_requirements = self.pg_manager.list_requirements(limit=1)
            
            verification = {
                'database_health': health,
                'total_requirements_in_db': stats.get('total_requirements', 0),
                'has_sample_data': len(sample_requirements) > 0,
                'sample_requirement_structure': None
            }
            
            if sample_requirements:
                sample = sample_requirements[0]
                verification['sample_requirement_structure'] = {
                    'has_id': 'id' in sample,
                    'has_new_fields': 'req_status' in sample,
                    'has_vendor_details': 'vendor_details' in sample,
                    'has_job_info': 'job_requirement_info' in sample,
                    'has_comments': 'marketing_comments' in sample,
                    'legacy_compatibility': all(field in sample for field in ['job_title', 'client', 'status'])
                }
            
            return verification
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return {'error': str(e)}
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        try:
            health = self.pg_manager.get_database_health()
            return {
                'connected': health.get('connected', False),
                'response_time_ms': health.get('response_time_ms'),
                'connection_info': 'PostgreSQL database with connection pooling'
            }
        except Exception:
            return {'connected': False, 'error': 'Unable to get database info'}
    
    def dry_run(self) -> Dict[str, Any]:
        """
        Perform a dry run to see what would be migrated without actually migrating
        
        Returns:
            Dict containing dry run results
        """
        try:
            logger.info("🔍 Starting dry run analysis...")
            
            # Load JSON data
            json_data = self._load_json_data()
            if not json_data:
                return {
                    'success': False,
                    'error': 'No JSON data found',
                    'analysis': {}
                }
            
            requirements_data = json_data.get('requirements', {})
            if not isinstance(requirements_data, dict):
                return {
                    'success': False,
                    'error': 'Invalid requirements data format',
                    'analysis': {}
                }
            
            analysis = {
                'total_requirements': len(requirements_data),
                'field_analysis': {},
                'data_quality': {
                    'complete_requirements': 0,
                    'missing_critical_fields': 0,
                    'has_comments': 0,
                    'has_consultants': 0,
                    'has_vendor_info': 0
                },
                'transformation_preview': []
            }
            
            # Analyze each requirement
            for req_id, req_data in requirements_data.items():
                # Check completeness
                if req_data.get('job_title') and req_data.get('client', req_data.get('client_company')):
                    analysis['data_quality']['complete_requirements'] += 1
                else:
                    analysis['data_quality']['missing_critical_fields'] += 1
                
                if req_data.get('marketing_comments'):
                    analysis['data_quality']['has_comments'] += 1
                
                if req_data.get('consultants'):
                    analysis['data_quality']['has_consultants'] += 1
                
                if req_data.get('vendor_info') or req_data.get('vendor_details'):
                    analysis['data_quality']['has_vendor_info'] += 1
                
                # Analyze fields
                for field, value in req_data.items():
                    if field not in analysis['field_analysis']:
                        analysis['field_analysis'][field] = {
                            'count': 0,
                            'types': set(),
                            'sample_values': []
                        }
                    
                    analysis['field_analysis'][field]['count'] += 1
                    analysis['field_analysis'][field]['types'].add(type(value).__name__)
                    
                    # Store sample values (limit to 3)
                    if len(analysis['field_analysis'][field]['sample_values']) < 3:
                        if isinstance(value, (str, int, float, bool)):
                            analysis['field_analysis'][field]['sample_values'].append(value)
                        elif isinstance(value, (list, dict)):
                            analysis['field_analysis'][field]['sample_values'].append(f"{type(value).__name__} with {len(value)} items")
                
                # Show transformation preview for first 3 requirements
                if len(analysis['transformation_preview']) < 3:
                    try:
                        transformed = self._transform_requirement_data(req_data)
                        analysis['transformation_preview'].append({
                            'original_id': req_id,
                            'original_sample': {k: v for k, v in list(req_data.items())[:3]},
                            'transformed_sample': {k: v for k, v in list(transformed.items())[:3]},
                            'new_structure': {
                                'has_req_status': 'req_status' in transformed,
                                'has_vendor_details': bool(transformed.get('vendor_details')),
                                'has_job_requirement_info': bool(transformed.get('job_requirement_info')),
                                'comments_count': len(transformed.get('marketing_comments', [])),
                                'consultants_count': len(transformed.get('consultants', []))
                            }
                        })
                    except Exception as e:
                        analysis['transformation_preview'].append({
                            'original_id': req_id,
                            'error': str(e)
                        })
            
            # Convert sets to lists for JSON serialization
            for field_info in analysis['field_analysis'].values():
                field_info['types'] = list(field_info['types'])
            
            logger.info(f"✅ Dry run completed. Found {analysis['total_requirements']} requirements to migrate")
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Dry run failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis': {}
            }

def run_migration(json_file_path: str = "requirements.json", backup: bool = True) -> Dict[str, Any]:
    """
    Convenience function to run the complete migration
    
    Args:
        json_file_path: Path to JSON file
        backup: Whether to backup the JSON file
        
    Returns:
        Dict containing migration results
    """
    migrator = JSONToPostgreSQLMigrator(json_file_path)
    return migrator.migrate_all_data(backup_json=backup)

def run_dry_run(json_file_path: str = "requirements.json") -> Dict[str, Any]:
    """
    Convenience function to run a dry run analysis
    
    Args:
        json_file_path: Path to JSON file
        
    Returns:
        Dict containing dry run analysis
    """
    migrator = JSONToPostgreSQLMigrator(json_file_path)
    return migrator.dry_run()



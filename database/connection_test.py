"""
Database Connection Test and Diagnostics
Tests database connectivity and identifies issues
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnectionManager, get_db_session
from database.config import setup_database_environment, validate_database_config
from database.models import Base, Requirement, RequirementComment, RequirementConsultant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection() -> Dict[str, Any]:
    """
    Comprehensive database connection test
    
    Returns:
        Dict containing test results and diagnostics
    """
    results = {
        'connection_test': False,
        'schema_test': False,
        'crud_test': False,
        'performance_test': False,
        'errors': [],
        'warnings': [],
        'recommendations': []
    }
    
    try:
        # Test 1: Environment Setup
        logger.info("Testing database environment setup...")
        env_result = setup_database_environment()
        
        if not env_result['success']:
            results['errors'].append("Database environment setup failed")
            for error in env_result.get('validation_result', {}).get('errors', []):
                results['errors'].append(f"Config error: {error}")
            return results
        
        # Test 2: Connection Test
        logger.info("Testing database connection...")
        db_manager = DatabaseConnectionManager()
        
        if not db_manager.initialize():
            results['errors'].append("Failed to initialize database connection")
            return results
        
        results['connection_test'] = True
        logger.info("✅ Database connection successful")
        
        # Test 3: Schema Test
        logger.info("Testing database schema...")
        try:
            with get_db_session() as session:
                # Test if tables exist
                from sqlalchemy import inspect
                inspector = inspect(session.bind)
                tables = inspector.get_table_names()
                
                expected_tables = ['requirements', 'requirement_comments', 'requirement_consultants']
                missing_tables = [table for table in expected_tables if table not in tables]
                
                if missing_tables:
                    results['warnings'].append(f"Missing tables: {missing_tables}")
                    results['recommendations'].append("Run database initialization to create missing tables")
                else:
                    results['schema_test'] = True
                    logger.info("✅ Database schema is complete")
        
        except Exception as e:
            results['errors'].append(f"Schema test failed: {str(e)}")
        
        # Test 4: CRUD Operations Test
        logger.info("Testing CRUD operations...")
        try:
            with get_db_session() as session:
                # Test insert
                test_req = Requirement(
                    req_status='New',
                    applied_for='Raju',
                    client_company='Test Company',
                    job_title='Test Position',
                    primary_tech_stack='Python',
                    tech_stack=['Python', 'Django']
                )
                session.add(test_req)
                session.flush()
                
                # Test read
                found_req = session.query(Requirement).filter_by(id=test_req.id).first()
                if not found_req:
                    results['errors'].append("Failed to read inserted record")
                    return results
                
                # Test update
                found_req.req_status = 'Working'
                session.commit()
                
                # Test delete
                session.delete(found_req)
                session.commit()
                
                results['crud_test'] = True
                logger.info("✅ CRUD operations working correctly")
        
        except Exception as e:
            results['errors'].append(f"CRUD test failed: {str(e)}")
        
        # Test 5: Performance Test
        logger.info("Testing database performance...")
        try:
            start_time = datetime.now()
            
            with get_db_session() as session:
                # Test query performance
                count = session.query(Requirement).count()
                
            end_time = datetime.now()
            query_time = (end_time - start_time).total_seconds()
            
            if query_time > 5.0:
                results['warnings'].append(f"Slow query performance: {query_time:.2f}s")
                results['recommendations'].append("Consider adding database indexes for better performance")
            else:
                results['performance_test'] = True
                logger.info(f"✅ Query performance acceptable: {query_time:.2f}s")
        
        except Exception as e:
            results['errors'].append(f"Performance test failed: {str(e)}")
        
        # Generate recommendations
        if results['connection_test'] and results['schema_test'] and results['crud_test']:
            results['recommendations'].append("Database is working correctly")
        
        if not results['performance_test']:
            results['recommendations'].append("Consider optimizing database configuration")
        
        return results
        
    except Exception as e:
        results['errors'].append(f"Database test failed: {str(e)}")
        return results

def diagnose_database_issues() -> Dict[str, Any]:
    """
    Diagnose common database issues and provide solutions
    
    Returns:
        Dict containing diagnosis and solutions
    """
    diagnosis = {
        'issues_found': [],
        'solutions': [],
        'severity': 'low'
    }
    
    try:
        # Check environment variables
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            diagnosis['issues_found'].append(f"Missing environment variables: {missing_vars}")
            diagnosis['solutions'].append("Create .env file with database configuration")
            diagnosis['severity'] = 'high'
        
        # Check database dependencies
        try:
            import psycopg2
            import sqlalchemy
        except ImportError as e:
            diagnosis['issues_found'].append(f"Missing database dependencies: {str(e)}")
            diagnosis['solutions'].append("Install database dependencies: pip install psycopg2-binary sqlalchemy")
            diagnosis['severity'] = 'high'
        
        # Check connection string format
        try:
            from database.config import get_connection_string
            conn_str = get_connection_string()
            if not conn_str or 'postgresql://' not in conn_str:
                diagnosis['issues_found'].append("Invalid connection string format")
                diagnosis['solutions'].append("Check database configuration in .env file")
                diagnosis['severity'] = 'medium'
        except Exception as e:
            diagnosis['issues_found'].append(f"Connection string error: {str(e)}")
            diagnosis['solutions'].append("Fix database configuration")
            diagnosis['severity'] = 'high'
        
        return diagnosis
        
    except Exception as e:
        diagnosis['issues_found'].append(f"Diagnosis failed: {str(e)}")
        diagnosis['severity'] = 'high'
        return diagnosis

def main():
    """Main test function"""
    logger.info("Resume Customizer Database Diagnostics")
    logger.info("%s", "=" * 50)
    
    # Run diagnostics
    logger.info("Running database diagnostics...")
    diagnosis = diagnose_database_issues()

    if diagnosis['issues_found']:
        logger.error("Issues found: %s", diagnosis['issues_found'])
        logger.info("Recommended solutions: %s", diagnosis['solutions'])
        if diagnosis.get('severity') == 'high':
            logger.error("High severity issues found. Please fix these before proceeding.")
            return False
    else:
        logger.info("No configuration issues found")
    
    # Run connection tests
    logger.info("Running database connection tests...")
    test_results = test_database_connection()

    if test_results.get('errors'):
        logger.error("Connection test errors: %s", test_results['errors'])

    if test_results.get('warnings'):
        logger.warning("Warnings: %s", test_results['warnings'])

    if test_results.get('recommendations'):
        logger.info("Recommendations: %s", test_results['recommendations'])

    # Summary
    logger.info("Test Summary: connection=%s, schema=%s, crud=%s, performance=%s",
                test_results.get('connection_test'),
                test_results.get('schema_test'),
                test_results.get('crud_test'),
                test_results.get('performance_test'))
    
    return all([
        test_results['connection_test'],
        test_results['schema_test'],
        test_results['crud_test']
    ])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
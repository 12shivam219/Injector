"""
Database Package for Resume Customizer
PostgreSQL database integration with high performance and scalability
"""

# Import main components
from .connection import (
    DatabaseConnectionManager,
    db_manager,
    get_db_session,
    initialize_database,
    get_database_stats,
    database_health_check
)

# Add get_connection_manager function
def get_connection_manager():
    """Return the database connection manager instance"""
    return db_manager

from .models import (
    Base,
    Requirement,
    RequirementComment,
    RequirementConsultant,
    DatabaseStats,
    AuditLog,
    RequirementSummaryView
)

# Migrations module optional - only import if alembic is available
try:
    from .migrations import (
        DatabaseMigrator,
        migrator,
        initialize_database_schema,
        refresh_database_views,
        get_database_information,
        perform_database_maintenance
    )
    MIGRATIONS_AVAILABLE = True
except ImportError:
    MIGRATIONS_AVAILABLE = False

# Optional import - requirements_manager_db might have dependencies
try:
    from .requirements_manager_db import PostgreSQLRequirementsManager
    REQUIREMENTS_MANAGER_AVAILABLE = True
except ImportError:
    REQUIREMENTS_MANAGER_AVAILABLE = False

# Optional import - migrate_from_json requires migrations which needs alembic
try:
    from .migrate_from_json import (
        JSONToPostgreSQLMigrator,
        run_migration,
        run_dry_run
    )
    MIGRATION_TOOLS_AVAILABLE = True
except ImportError:
    MIGRATION_TOOLS_AVAILABLE = False

from .config import (
    DatabaseConfig,
    db_config,
    get_database_config,
    get_connection_string,
    get_engine_config,
    validate_database_config,
    create_env_file_template,
    load_env_file,
    setup_database_environment
)

__version__ = "1.0.0"
__author__ = "Resume Customizer Team"

# Package metadata
__all__ = [
    # Connection management
    'DatabaseConnectionManager',
    'db_manager',
    'get_db_session',
    'initialize_database',
    'get_database_stats',
    'database_health_check',
    
    # Models
    'Base',
    'Requirement',
    'RequirementComment',
    'RequirementConsultant',
    'DatabaseStats',
    'AuditLog',
    'RequirementSummaryView',
    
    # Migrations
    'DatabaseMigrator',
    'migrator',
    'initialize_database_schema',
    'refresh_database_views',
    'get_database_information',
    'perform_database_maintenance',
    
    # Requirements Manager
    'PostgreSQLRequirementsManager',
    
    # JSON Migration
    'JSONToPostgreSQLMigrator',
    'run_migration',
    'run_dry_run',
    
    # Configuration
    'DatabaseConfig',
    'db_config',
    'get_database_config',
    'get_connection_string',
    'get_engine_config',
    'validate_database_config',
    'create_env_file_template',
    'load_env_file',
    'setup_database_environment'
]



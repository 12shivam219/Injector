"""
Database package initialization.
Exports all database-related components for the Resume Customizer application.
"""

# Core database functionality
from .connection import (
    db_manager,
    get_db_session,
    initialize_database,
    get_database_stats,
    database_health_check
)

# Session management
from .session import (
    get_session,
    get_db_session as get_session_context,
    get_session_factory
)

# Read/write session management (if available)
try:
    from .utils.read_write_manager import (
        get_read_session,
        get_write_session
    )
    READ_WRITE_AVAILABLE = True
except ImportError:
    READ_WRITE_AVAILABLE = False
    get_read_session = None
    get_write_session = None

# All models from the models package
from .models import (
    # Base classes
    Base,
    BaseModel,
    
    # User models
    User,
    
    # Resume models
    ResumeDocument,
    ResumeCustomization,
    EmailSend,
    ProcessingLog,
    UserSession,
    ResumeAnalytics,
    
    # Requirements models
    Requirement,
    RequirementComment,
    RequirementConsultant,
    DatabaseStats,
    AuditLog,
    RequirementSummaryView,
    
    # Format models
    ResumeFormat,
    ResumeFormatMatch,
    FormatElement
)

# Query optimizer (if available)
try:
    from .query_optimizer import (
        get_query_optimizer,
        QueryOptimizer
    )
    QUERY_OPTIMIZER_AVAILABLE = True
except ImportError:
    QUERY_OPTIMIZER_AVAILABLE = False
    get_query_optimizer = None
    QueryOptimizer = None

# Configuration
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

__version__ = "2.0.0"
__author__ = "Resume Customizer Team"

# Clean exports - only include what's actually available and commonly used
__all__ = [
    # Core database functionality
    'db_manager',
    'get_db_session', 
    'initialize_database',
    'get_database_stats',
    'database_health_check',
    
    # Session management
    'get_session',
    'get_session_context',
    'get_session_factory',
    
    # Base classes
    'Base',
    'BaseModel',
    
    # User models
    'User',
    
    # Resume models
    'ResumeDocument',
    'ResumeCustomization',
    'EmailSend',
    'ProcessingLog',
    'UserSession',
    'ResumeAnalytics',
    
    # Requirements models
    'Requirement',
    'RequirementComment',
    'RequirementConsultant',
    'DatabaseStats',
    'AuditLog',
    'RequirementSummaryView',
    
    # Format models
    'ResumeFormat',
    'ResumeFormatMatch',
    'FormatElement',
    
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

# Conditionally add optional components
if READ_WRITE_AVAILABLE:
    __all__.extend(['get_read_session', 'get_write_session'])
    
if QUERY_OPTIMIZER_AVAILABLE:
    __all__.extend(['get_query_optimizer', 'QueryOptimizer'])



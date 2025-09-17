"""
Application Bootstrap Module
Shared initialization and services for all Streamlit pages
"""

import streamlit as st
import uuid
import logging
from typing import Dict, Any, Optional

# Core imports
from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger

# Configuration
APP_CONFIG = {
    "title": "Resume Customizer",
    "layout": "wide", 
    "version": "2.0.0",
    "services_enabled": True,
    "async_enabled": True,
    "monitoring_enabled": True,
    "debug_mode": False,
    "auth_required": True  # Enable authentication requirement
}

def initialize_app():
    """Initialize the Streamlit application with shared configuration."""
    
    # Set page config (only if not already set)
    try:
        st.set_page_config(
            page_title=APP_CONFIG["title"],
            page_icon="📝",
            layout=APP_CONFIG["layout"],
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # Page config already set, skip
        pass
    
    # Initialize session state
    initialize_session_state()
    
    # Cache services
    st.session_state.services = get_cached_services()
    
    # Initialize logging
    logger = get_logger()
    
    # Check authentication if required
    if APP_CONFIG["auth_required"] and not st.session_state.get('authenticated', False):
        # Get current page
        import inspect
        import os
        current_file = inspect.stack()[1].filename
        current_filename = os.path.basename(current_file)
        
        # Skip auth check for login page
        if current_filename != "login.py":
            st.warning("⚠️ Authentication required. Please log in to continue.")
            st.info("Redirecting to login page...")
            st.switch_page("pages/login.py")
            return
    
    # Check bootstrap status
    from infrastructure.utilities.bootstrap_check import check_bootstrap_status
    is_ready, status = check_bootstrap_status()
    
    if is_ready:
        logger.info("Application bootstrap completed successfully")
    else:
        logger.error("Application bootstrap incomplete", extra={"status": status})

def initialize_session_state():
    """Initialize session state variables with defaults."""
    defaults = {
        'initialized': True,
        'resume_text': "",
        'job_description': "",
        'customized_resume': "",
        'uploaded_files': [],
        'processing_status': {},
        'email_sent': False,
        'bulk_results': [],
        'current_tab': "Upload Resume",
        'performance_data': {},
        'error_history': [],
        'async_tasks': {},
        'ui_preferences': {
            'theme': 'light',
            'show_debug': False,
            'auto_save': True
        },
        'authenticated': False,
        'auth_username': None,
        'rate_limits': {},
        'rate_limit_config': {
            'resume_upload': {'limit': 10, 'window': 60},
            'email_send': {'limit': 5, 'window': 60},
            'api_call': {'limit': 20, 'window': 60}
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize resume_inputs if not exists
    if 'resume_inputs' not in st.session_state:
        st.session_state.resume_inputs = {}
    
    # Initialize user_id if not exists
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    # Initialize async services
    if 'async_initialized' not in st.session_state:
        try:
            from infrastructure.async_processing.async_integration import initialize_async_services
            async_success = initialize_async_services()
            st.session_state.async_initialized = async_success
        except ImportError:
            st.session_state.async_initialized = False

@st.cache_resource
def get_cached_services() -> Dict[str, Any]:
    """Get cached instances of all services."""
    services = {}
    
    # Initialize database connection
    try:
        from database.connection import DatabaseConnectionManager
        from database.config import DatabaseConfig, setup_database_environment, get_connection_string

        # Ensure environment file (if present) is loaded and config validated
        env_setup = setup_database_environment()
        if not env_setup.get('config_loaded'):
            logging.warning('Database environment file not loaded; falling back to environment variables')

        # Build connection string (may use DATABASE_URL or individual vars)
        try:
            connection_string = get_connection_string()
        except Exception:
            connection_string = None

        # Initialize connection manager
        db_manager = DatabaseConnectionManager()
        initialized = False
        try:
            if connection_string:
                initialized = db_manager.initialize(database_url=connection_string)
            else:
                initialized = db_manager.initialize()
        except Exception as db_init_exc:
            logging.error(f'Database initialization raised an exception: {db_init_exc}')

        if initialized:
            services['db_session'] = db_manager.SessionLocal
            logging.info("Database connection initialized successfully")
        else:
            services['db_session'] = None
            logging.error(
                "Failed to initialize database connection. Check your .env or DATABASE_URL and ensure the database is reachable."
            )
    except Exception as e:
        services['db_session'] = None
        logging.error(f"Database initialization error: {e}")
    
    # UI Components
    try:
        from ui.components import UIComponents
        services['ui_components'] = UIComponents()
    except ImportError as e:
        services['ui_components'] = None
        logging.warning(f"Could not load UI components: {e}")
    
    # Authentication Manager
    try:
        from infrastructure.security.auth import AuthenticationManager
        services['auth_manager'] = AuthenticationManager()
        logging.info("Authentication manager initialized successfully")
    except ImportError as e:
        services['auth_manager'] = None
        logging.warning(f"Could not load authentication manager: {e}")
    
    # Resume Manager
    try:
        from resume_customizer.processors.resume_processor import ResumeProcessor
        services['resume_processor'] = ResumeProcessor()
    except ImportError as e:
        services['resume_processor'] = None
        logging.warning(f"Could not load resume processor: {e}")
    
    # Requirements Manager - Try database version first, fallback to file-based
    try:
        from database.requirements_manager_db import RequirementsManager
        services['requirements_manager'] = RequirementsManager()
    except (ImportError, Exception) as e:
        # Fallback to file-based requirements manager
        try:
            from resume_customizer.analyzers.requirements_integration import RequirementsManager
            services['requirements_manager'] = RequirementsManager()
            logging.info("Using file-based requirements manager as fallback")
        except Exception as fallback_e:
            services['requirements_manager'] = None
            logging.warning(f"Could not load any requirements manager: {e}, fallback: {fallback_e}")
    
    # Analytics Manager
    try:
        from infrastructure.monitoring.analytics import AnalyticsManager
        services['analytics'] = AnalyticsManager()
    except ImportError as e:
        services['analytics'] = None
        logging.warning(f"Could not load analytics manager: {e}")
    
    # Bulk Processor
    try:
        from ui.bulk_processor import BulkProcessor
        from resume_customizer.processors.resume_processor import get_resume_manager
        resume_manager = get_resume_manager("v2.2")
        if resume_manager:
            services['bulk_processor'] = BulkProcessor(resume_manager=resume_manager)
        else:
            services['bulk_processor'] = None
            logging.warning("Resume manager initialization failed for bulk processor")
    except (ImportError, Exception) as e:
        services['bulk_processor'] = None
        logging.warning(f"Could not load bulk processor: {e}")
    
    # Secure UI Components  
    try:
        from ui.secure_components import get_secure_ui_components
        services['secure_ui_components'] = get_secure_ui_components()
    except ImportError as e:
        services['secure_ui_components'] = None
        logging.warning(f"Could not load secure UI components: {e}")
    
    # Resume Tab Handler
    try:
        from ui.resume_tab_handler import ResumeTabHandler
        from resume_customizer.processors.resume_processor import get_resume_manager
        resume_manager = get_resume_manager("v2.2")
        if resume_manager:
            services['resume_tab_handler'] = ResumeTabHandler(resume_manager=resume_manager)
        else:
            services['resume_tab_handler'] = None
            logging.warning("Resume manager initialization failed")
    except (ImportError, Exception) as e:
        services['resume_tab_handler'] = None
        logging.warning(f"Could not load resume tab handler: {e}")
    
    # Application Guide
    try:
        from ui.application_guide import app_guide
        services['app_guide'] = app_guide
    except ImportError as e:
        services['app_guide'] = None
        logging.warning(f"Could not load application guide: {e}")
    
    return services

@st.cache_resource
def get_cached_logger():
    """Get cached logger instance."""
    return get_logger()

@st.cache_resource
def get_cached_requirements_manager():
    """Get cached requirements manager."""
    try:
        from resume_customizer.analyzers.requirements_integration import RequirementsManager
        return RequirementsManager()
    except ImportError:
        return None

# Feature availability flags
def check_feature_availability() -> Dict[str, bool]:
    """Check which features are available."""
    features = {}
    
    # Async processing
    try:
        import infrastructure.async_processing.async_integration
        features['async_processing'] = True
    except ImportError:
        features['async_processing'] = False
    
    # Error handling
    try:
        import enhancements.error_handling_enhanced
        features['error_handling'] = True
    except ImportError:
        features['error_handling'] = False
    
    # Structured logging
    try:
        import infrastructure.utilities.structured_logger
        features['structured_logging'] = True
    except ImportError:
        features['structured_logging'] = False
    
    return features

# Export key functions
__all__ = [
    'initialize_app',
    'initialize_session_state', 
    'get_cached_services',
    'get_cached_logger',
    'get_cached_requirements_manager',
    'check_feature_availability',
    'APP_CONFIG'
]
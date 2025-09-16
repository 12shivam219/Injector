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
    "debug_mode": False
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
    
    # UI Components
    try:
        from ui.components import UIComponents
        services['ui_components'] = UIComponents()
    except ImportError as e:
        services['ui_components'] = None
        logging.warning(f"Could not load UI components: {e}")
    
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
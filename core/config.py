"""
Core configuration module - central place for all application configuration.
Re-exports configuration from the main config.py for backward compatibility.
"""

# Import all configuration from main config.py
from config import *

# Additional core configuration constants
APP_NAME = "Resume Customizer"
APP_VERSION = "2.0.0"
CORE_MODULE_VERSION = "1.0.0"

# Feature flags
ENABLE_ASYNC_PROCESSING = True
ENABLE_ADVANCED_LOGGING = True
ENABLE_MEMORY_OPTIMIZATION = True
ENABLE_PERFORMANCE_MONITORING = True

# Cache configuration
CACHE_TTL_SECONDS = 3600
DEFAULT_CACHE_SIZE = 100

# Export everything for easy import
__all__ = [
    # From main config.py
    'DOC_CONFIG', 'PARSING_CONFIG', 'EMAIL_CONFIG', 'APP_CONFIG', 'UI_CONFIG',
    'is_production', 'is_debug', 'reload_config', 'create_env_template',
    'get_smtp_servers', 'get_default_email_subject', 'get_default_email_body',
    'get_email_config', 'get_config_summary', 'DATABASE_INTEGRATION_AVAILABLE',
    # Core additions
    'APP_NAME', 'APP_VERSION', 'CORE_MODULE_VERSION',
    'ENABLE_ASYNC_PROCESSING', 'ENABLE_ADVANCED_LOGGING', 
    'ENABLE_MEMORY_OPTIMIZATION', 'ENABLE_PERFORMANCE_MONITORING',
    'CACHE_TTL_SECONDS', 'DEFAULT_CACHE_SIZE'
]
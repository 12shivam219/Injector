"""
Database Configuration for Resume Customizer
PostgreSQL database configuration with environment variables and connection management
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseHealthChecker:
    """Check database health and connectivity"""
    
    @staticmethod
    def check_connection_health(connection_string: str) -> Dict[str, Any]:
        """Check if database connection is healthy"""
        health_status = {
            'connected': False,
            'response_time_ms': None,
            'database_exists': False,
            'tables_exist': False,
            'errors': []
        }
        
        try:
            from sqlalchemy import create_engine, text
            import time
            
            start_time = time.time()
            engine = create_engine(connection_string)
            
            with engine.connect() as conn:
                # Test basic connectivity
                conn.execute(text("SELECT 1"))
                health_status['connected'] = True
                health_status['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
                
                # Check if main tables exist
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name IN ('requirements', 'requirement_comments', 'requirement_consultants')
                """))
                existing_tables = [row[0] for row in result]
                health_status['tables_exist'] = len(existing_tables) >= 3
                health_status['existing_tables'] = existing_tables
                
            engine.dispose()
            
        except Exception as e:
            health_status['errors'].append(str(e))
            
        return health_status

class DatabaseConfig:
    """
    Neon PostgreSQL configuration management (DATABASE_URL only)
    """
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load Neon database configuration from environment"""
        
        # Require the Neon/Postgres connection URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")
        
        # SSL is required for Neon
        sslmode = os.getenv('DB_SSL_MODE', 'require')
        connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '30'))
        statement_timeout_ms = os.getenv('DB_STATEMENT_TIMEOUT_MS') or os.getenv('DB_STATEMENT_TIMEOUT')
        
        connect_args: Dict[str, Any] = {
            'sslmode': sslmode,
            'connect_timeout': connect_timeout,
        }
        # Add statement timeout via server options if provided
        if statement_timeout_ms:
            try:
                # Use -c statement_timeout=... in options when supported
                connect_args['options'] = f"-c statement_timeout={int(statement_timeout_ms)}"
            except Exception:
                pass
        
        config = {
            'url': database_url,  # Full SQLAlchemy URL
            'connect_args': connect_args,
            'pool_pre_ping': True,
            'pool_size': int(os.getenv('DB_POOL_SIZE', os.getenv('DB_MIN_CONNECTIONS', '2'))),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', os.getenv('DB_MAX_CONNECTIONS', '10'))),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', os.getenv('DB_CONNECTION_TIMEOUT', '30'))),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', os.getenv('DB_IDLE_TIMEOUT', '300'))),
        }
        return config
    
    def _parse_database_url(self, database_url: str) -> Optional[Dict[str, Any]]:
        """Parse DATABASE_URL for validation/diagnostics."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            if parsed.scheme not in ['postgresql', 'postgres', 'postgresql+psycopg2']:
                return None
            return {
                'host': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'database': parsed.path[1:] if parsed.path and len(parsed.path) > 1 else None,
            }
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return None
    
    def get_connection_string(self) -> str:
        """Return the full connection URL (DATABASE_URL)."""
        return self.config['url']
    
    def get_engine_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration"""
        return {
            'pool_size': self.config['pool_size'],
            'max_overflow': self.config['max_overflow'],
            'pool_timeout': self.config['pool_timeout'],
            'pool_recycle': self.config['pool_recycle'],
            'pool_pre_ping': True,
            'pool_reset_on_return': 'commit',
            'connect_args': self.config['connect_args'],
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate database configuration (DATABASE_URL-based)"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        url = self.config.get('url')
        if not url:
            result['valid'] = False
            result['errors'].append('DATABASE_URL is missing')
            return result
        
        parsed = self._parse_database_url(url)
        if not parsed:
            result['valid'] = False
            result['errors'].append('DATABASE_URL must use postgres/postgresql scheme')
            return result
        
        # Basic sanity checks
        if not parsed.get('host'):
            result['warnings'].append('Host is empty in DATABASE_URL')
        if not parsed.get('database'):
            result['warnings'].append('Database name is empty in DATABASE_URL')
        try:
            port = int(parsed.get('port') or 5432)
            if port < 1 or port > 65535:
                result['warnings'].append(f'Port {port} looks invalid')
        except Exception:
            result['warnings'].append('Port is not a number')
        
        # Pool checks
        if self.config.get('pool_size', 0) < 1:
            result['warnings'].append('Pool size is < 1; may cause connection issues')
        if self.config.get('max_overflow', 0) < 0:
            result['warnings'].append('Max overflow < 0; setting to 0')
            self.config['max_overflow'] = 0
        
        return result
    
    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary"""
        return self.config.copy()
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        self.config.update(updates)
    
    def get_display_config(self) -> Dict[str, Any]:
        """Get configuration for display (password masked)"""
        display_config = self.config.copy()
        if 'password' in display_config:
            display_config['password'] = '*' * len(display_config['password'])
        return display_config

# Lazy global database configuration instance
_db_config: Optional[DatabaseConfig] = None

def _ensure_db_config() -> DatabaseConfig:
    """Ensure the global DatabaseConfig instance is created lazily."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config

def get_database_config() -> DatabaseConfig:
    """Get global database configuration instance"""
    return _ensure_db_config()

def get_connection_string() -> str:
    """Get database connection string"""
    return _ensure_db_config().get_connection_string()

def safe_get_connection_string() -> Optional[str]:
    """Return connection string or None if not configured instead of raising."""
    try:
        return get_connection_string()
    except Exception:
        return None

def get_engine_config() -> Dict[str, Any]:
    """Get SQLAlchemy engine configuration"""
    return _ensure_db_config().get_engine_config()

def validate_database_config() -> Dict[str, Any]:
    """Validate database configuration"""
    return _ensure_db_config().validate_config()

def create_env_file_template(file_path: str = ".env.template") -> bool:
    """
    Create a template .env file with database configuration variables
    (Neon Postgres via DATABASE_URL only)
    
    Args:
        file_path: Path to create the template file
        
    Returns:
        bool: True if template created successfully
    """
    try:
        template_content = '''# Database Configuration for Resume Customizer (Neon)
# Use a full SQLAlchemy DATABASE_URL. Example formats:
# DATABASE_URL=postgresql://username:password@host:5432/dbname
# DATABASE_URL=postgresql+psycopg2://username:password@host:5432/dbname

# IMPORTANT: For Neon, SSL is required. We enforce sslmode=require in code.
# Just set your Neon connection string below:
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME

# Optional pool and timeout settings
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=300
DB_CONNECT_TIMEOUT=30
# DB_STATEMENT_TIMEOUT_MS=60000

# Streamlit settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
'''
        
        with open(file_path, 'w') as f:
            f.write(template_content)
        
        logger.info(f"✅ Environment template created: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create environment template: {e}")
        return False

def load_env_file(file_path: str = ".env") -> bool:
    """
    Load environment variables from .env file
    
    Args:
        file_path: Path to the .env file
        
    Returns:
        bool: True if loaded successfully
    """
    try:
        env_path = Path(file_path)
        if not env_path.exists():
            logger.warning(f"⚠️ Environment file not found: {file_path}")
            return False
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    os.environ[key] = value
        
        logger.info(f"✅ Environment variables loaded from: {file_path}")

        # Reload database configuration after loading env file
        global _db_config
        _db_config = DatabaseConfig()

        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load environment file: {e}")
        return False

def setup_database_environment() -> Dict[str, Any]:
    """
    Setup database environment with configuration validation
    
    Returns:
        Dict containing setup results
    """
    result = {
        'success': False,
        'config_loaded': False,
        'config_valid': False,
        'env_file_exists': False,
        'validation_result': {}
    }
    
    try:
        # Check if .env file exists and load it
        env_file_path = Path('.env')
        if env_file_path.exists():
            result['env_file_exists'] = True
            result['config_loaded'] = load_env_file()
        else:
            logger.info("No .env file found, using environment variables and defaults")
            result['config_loaded'] = True
        
        # Validate configuration
        validation = validate_database_config()
        result['validation_result'] = validation
        result['config_valid'] = validation['valid']
        
        # Overall success
        result['success'] = result['config_loaded'] and result['config_valid']
        
        if result['success']:
            logger.info("✅ Database environment setup completed successfully")
        else:
            logger.warning("⚠️ Database environment setup completed with issues")
            if validation['errors']:
                for error in validation['errors']:
                    logger.error(f"❌ {error}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Database environment setup failed: {e}")
        result['error'] = str(e)
        return result

# Email configuration functions for UI components
def get_smtp_servers():
    """Get list of available SMTP servers"""
    return [
        "smtp.gmail.com",
        "smtp.outlook.com", 
        "smtp.yahoo.com",
        "smtp.mail.yahoo.com",
        "smtp.aol.com",
        "smtp.zoho.com",
        "smtp.icloud.com",
        "localhost"
    ]

def get_default_email_subject():
    """Get default email subject template"""
    return "Resume Application - {job_title} at {company_name}"

def get_default_email_body():
    """Get default email body template"""
    return """Dear Hiring Manager,

I hope this email finds you well. I am writing to express my interest in the {job_title} position at {company_name}.

Please find my resume attached for your review. I have customized it specifically for this role, highlighting my relevant experience and skills that align with your requirements.

I would welcome the opportunity to discuss how my background and enthusiasm can contribute to your team's success.

Thank you for your time and consideration.

Best regards,
[Your Name]
[Your Contact Information]"""

def get_email_config():
    """Get email configuration settings"""
    return {
        'smtp_timeout': 30,
        'max_attachment_size': 25 * 1024 * 1024,  # 25MB
        'supported_formats': ['.pdf', '.docx', '.doc'],
        'default_port_mapping': {
            'smtp.gmail.com': 587,
            'smtp.outlook.com': 587,
            'smtp.yahoo.com': 587,
            'smtp.mail.yahoo.com': 587,
            'smtp.aol.com': 587,
            'smtp.zoho.com': 587,
            'smtp.icloud.com': 587,
            'localhost': 25
        }
    }



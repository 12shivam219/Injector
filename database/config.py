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
    Database configuration management with environment variables
    """
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from environment variables"""
        
        # Default configuration
        default_config = {
            'host': 'localhost',
            'port': '5432',
            'database': 'resume_customizer',
            'username': 'postgres',
            'password': '',
            'ssl_mode': 'prefer',
            'connect_timeout': 10,
            'statement_timeout': 60000,
            'pool_size': 20,
            'max_overflow': 30,
            'pool_timeout': 30,
            'pool_recycle': 3600
        }
        
        # Environment variable mappings
        env_mappings = {
            'host': ['DATABASE_HOST', 'DB_HOST', 'POSTGRES_HOST'],
            'port': ['DATABASE_PORT', 'DB_PORT', 'POSTGRES_PORT'],
            'database': ['DATABASE_NAME', 'DB_NAME', 'POSTGRES_DB'],
            'username': ['DATABASE_USER', 'DB_USER', 'POSTGRES_USER'],
            'password': ['DATABASE_PASSWORD', 'DB_PASSWORD', 'POSTGRES_PASSWORD'],
            'ssl_mode': ['DATABASE_SSL_MODE', 'DB_SSL_MODE'],
            'connect_timeout': ['DATABASE_CONNECT_TIMEOUT', 'DB_CONNECT_TIMEOUT'],
            'statement_timeout': ['DATABASE_STATEMENT_TIMEOUT', 'DB_STATEMENT_TIMEOUT'],
            'pool_size': ['DATABASE_POOL_SIZE', 'DB_POOL_SIZE'],
            'max_overflow': ['DATABASE_MAX_OVERFLOW', 'DB_MAX_OVERFLOW'],
            'pool_timeout': ['DATABASE_POOL_TIMEOUT', 'DB_POOL_TIMEOUT'],
            'pool_recycle': ['DATABASE_POOL_RECYCLE', 'DB_POOL_RECYCLE']
        }
        
        # Load configuration from environment variables
        config = default_config.copy()
        for config_key, env_keys in env_mappings.items():
            for env_key in env_keys:
                env_value = os.getenv(env_key)
                if env_value is not None:
                    # Convert numeric values
                    if config_key in ['port', 'connect_timeout', 'statement_timeout', 
                                     'pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']:
                        try:
                            config[config_key] = int(env_value)
                        except ValueError:
                            logger.warning(f"Invalid numeric value for {env_key}: {env_value}")
                    else:
                        config[config_key] = env_value
                    break  # Use first found environment variable
        
        # Special handling for DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            parsed_config = self._parse_database_url(database_url)
            if parsed_config:
                config.update(parsed_config)
        
        return config
    
    def _parse_database_url(self, database_url: str) -> Optional[Dict[str, Any]]:
        """Parse DATABASE_URL format: postgresql://user:pass@host:port/dbname"""
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(database_url)
            if parsed.scheme not in ['postgresql', 'postgres']:
                return None
            
            config = {}
            if parsed.hostname:
                config['host'] = parsed.hostname
            if parsed.port:
                config['port'] = parsed.port
            # Percent-decode username/password if present so they are stored
            # in plain form in the config and re-encoded when building the
            # final connection string.
            from urllib.parse import unquote
            if parsed.username:
                try:
                    config['username'] = unquote(parsed.username)
                except Exception:
                    config['username'] = parsed.username
            if parsed.password:
                try:
                    config['password'] = unquote(parsed.password)
                except Exception:
                    config['password'] = parsed.password
            if parsed.path and len(parsed.path) > 1:
                config['database'] = parsed.path[1:]  # Remove leading '/'
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            return None
    
    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        from urllib.parse import quote_plus
        
        # URL encode password to handle special characters
        password = quote_plus(self.config['password'])
        
        return (
            f"postgresql://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )
    
    def get_engine_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration"""
        return {
            'pool_size': self.config['pool_size'],
            'max_overflow': self.config['max_overflow'],
            'pool_timeout': self.config['pool_timeout'],
            'pool_recycle': self.config['pool_recycle'],
            'pool_pre_ping': True,
            'pool_reset_on_return': 'commit',
            'connect_args': {
                'connect_timeout': self.config['connect_timeout'],
                'application_name': 'ResumeCustomizer',
                'sslmode': self.config['ssl_mode']
            }
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate database configuration"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = ['host', 'port', 'database', 'username', 'password']
        for field in required_fields:
            if not self.config.get(field):
                validation_result['valid'] = False
                validation_result['errors'].append(f"Missing required field: {field}")
        
        # Port validation
        try:
            port = int(self.config['port'])
            if port < 1 or port > 65535:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Invalid port number: {port}")
        except (ValueError, TypeError):
            validation_result['valid'] = False
            validation_result['errors'].append(f"Invalid port format: {self.config['port']}")
        
        # Pool configuration validation
        pool_size = self.config.get('pool_size', 0)
        max_overflow = self.config.get('max_overflow', 0)
        
        if pool_size < 1:
            validation_result['warnings'].append("Pool size is less than 1, may cause connection issues")
        
        if max_overflow < 0:
            validation_result['warnings'].append("Max overflow is negative, setting to 0")
            self.config['max_overflow'] = 0
        
        if pool_size + max_overflow > 100:
            validation_result['warnings'].append("Total pool size is very high, may cause resource issues")
        
        # Timeout validation
        timeouts = ['connect_timeout', 'pool_timeout', 'pool_recycle']
        for timeout_field in timeouts:
            value = self.config.get(timeout_field, 0)
            if value < 1:
                validation_result['warnings'].append(f"{timeout_field} is very low, may cause timeout issues")
        
        return validation_result
    
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

# Global database configuration instance
db_config = DatabaseConfig()

def get_database_config() -> DatabaseConfig:
    """Get global database configuration instance"""
    return db_config

def get_connection_string() -> str:
    """Get database connection string"""
    return db_config.get_connection_string()

def get_engine_config() -> Dict[str, Any]:
    """Get SQLAlchemy engine configuration"""
    return db_config.get_engine_config()

def validate_database_config() -> Dict[str, Any]:
    """Validate database configuration"""
    return db_config.validate_config()

def create_env_file_template(file_path: str = ".env.template") -> bool:
    """
    Create a template .env file with database configuration variables
    
    Args:
        file_path: Path to create the template file
        
    Returns:
        bool: True if template created successfully
    """
    try:
        template_content = '''# Database Configuration for Resume Customizer
# PostgreSQL Database Settings

# Database Host (default: localhost)
DB_HOST=localhost

# Database Port (default: 5432)
DB_PORT=5432

# Database Name (default: resume_customizer)
DB_NAME=resume_customizer

# Database Username (default: postgres)
DB_USER=postgres

# Database Password (REQUIRED - set your password)
DB_PASSWORD=your_password_here

# SSL Mode (default: prefer)
# Options: disable, allow, prefer, require, verify-ca, verify-full
DB_SSL_MODE=prefer

# Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Timeout Settings (in seconds)
DB_CONNECT_TIMEOUT=10
DB_STATEMENT_TIMEOUT=60000

# Alternative: Use DATABASE_URL for complete connection string
# DATABASE_URL=postgresql://username:password@host:port/dbname

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost

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
        global db_config
        db_config = DatabaseConfig()
        
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



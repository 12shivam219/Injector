"""
Advanced PostgreSQL Connection Management for Resume Customizer
High-performance connection pooling, retry logic, and concurrent access support
"""

import os
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from urllib.parse import quote_plus
import threading

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from sqlalchemy.pool import QueuePool
import psycopg2
from psycopg2 import OperationalError as PsycopgOperationalError
from database.error_handler import handle_db_errors, with_retry, ConnectionError
from database.query_monitor import setup_query_monitoring
from database.adaptive_pool import setup_adaptive_pooling

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """
    High-performance database connection manager with advanced features:
    - Connection pooling for concurrent access
    - Automatic retry logic
    - Health monitoring
    - Performance optimization
    - Thread-safe operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global connection manager"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
            
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._connection_string: Optional[str] = None
        self._is_connected = False
        self._retry_count = 0
        self._max_retries = 3
        self._connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'active_connections': 0,
            'pool_size': 0,
            'overflow_connections': 0
        }
        self.initialized = True
    
    def initialize(self, database_url: Optional[str] = None, **kwargs) -> bool:
        """
        Initialize database connection with advanced configuration
        
        Args:
            database_url: PostgreSQL connection string
            **kwargs: Additional engine configuration options
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if not database_url:
                database_url = self._build_connection_string()
            
            print(f"Trying to connect with URL: {database_url}")
            self._connection_string = database_url
            
            # Simple engine configuration for testing
            engine_config = {
                'echo': True,  # Enable SQL debugging
                'pool_pre_ping': True,
                'connect_args': {
                    'application_name': 'ResumeCustomizer'
                }
            }
            
            # Create engine with optimizations
            self.engine = create_engine(database_url, **engine_config)
            
            # Set up query monitoring
            setup_query_monitoring(self.engine, slow_query_threshold_ms=100)
            
            # Set up adaptive connection pooling
            self.pool_manager = setup_adaptive_pooling(
                self.engine,
                min_pool_size=int(os.getenv('DB_MIN_POOL_SIZE', '5')),
                max_pool_size=int(os.getenv('DB_MAX_POOL_SIZE', '30'))
            )
            
            # Configure session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=True,
                bind=self.engine,
                expire_on_commit=False  # Keep objects accessible after commit
            )
            
            # Add event listeners for monitoring
            self._setup_event_listeners()
            
            # Test connection
            if self._test_connection():
                self._is_connected = True
                logger.info("✅ Database connection initialized successfully")
                return True
            else:
                logger.error("❌ Failed to establish database connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables with encryption"""
        import os
        from dotenv import load_dotenv
        from database.encryption import encrypt_connection_string, decrypt_connection_string
        
        # Load environment variables
        load_dotenv()
        
        # Check for encrypted connection string first
        encrypted_conn_str = os.getenv('DB_ENCRYPTED_CONNECTION_STRING')
        if encrypted_conn_str:
            # Use the encrypted connection string if available
            connection_string = decrypt_connection_string(encrypted_conn_str)
            if connection_string:
                logger.info("📡 Using encrypted connection string from environment")
                return connection_string
        
        # Use the specific Neon PostgreSQL connection string if USE_NEON_DIRECT is set
        if os.getenv('USE_NEON_DIRECT') == 'true':
            connection_string = "postgresql://neondb_owner:npg_XBRWbz1SqaU7@ep-winter-morning-a8r8xu2w-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require"
            logger.info("📡 Using direct Neon PostgreSQL connection string")
            return connection_string
                
        # Check for Neon PostgreSQL configuration
        if os.getenv('NEON_DB_HOST'):
            # Build Neon PostgreSQL connection string
            db_user = os.getenv('NEON_DB_USER')
            db_password = quote_plus(os.getenv('NEON_DB_PASSWORD', ''))
            db_host = os.getenv('NEON_DB_HOST')
            db_port = os.getenv('NEON_DB_PORT', '5432')
            db_name = os.getenv('NEON_DB_NAME')
            ssl_mode = os.getenv('NEON_DB_SSL_MODE', 'require')
            
            # Neon requires SSL connection
            connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode={ssl_mode}"
            logger.info("📡 Using Neon PostgreSQL connection")
            return connection_string
        
        # Fall back to building from individual credentials
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'resume_customizer'),
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # URL encode password to handle special characters
        password = quote_plus(db_config['password'])
        
        connection_string = (
            f"postgresql://{db_config['username']}:{password}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        # Log connection info without sensitive data
        logger.info(f"📡 Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Generate encrypted string for future use
        encrypted = encrypt_connection_string(connection_string)
        logger.info(f"💡 Add this to your .env file to use encrypted connection:\nDB_ENCRYPTED_CONNECTION_STRING={encrypted}")
        
        return connection_string
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring and optimization"""
        
        @event.listens_for(self.engine, 'connect')
        def on_connect(dbapi_connection, connection_record):
            """Configure connection on creation"""
            self._connection_stats['total_connections'] += 1
            
            # PostgreSQL-specific optimizations
            with dbapi_connection.cursor() as cursor:
                # Only set safe session-level parameters
                cursor.execute("SET synchronous_commit TO off")  # Better write performance
                cursor.execute("SET random_page_cost TO 1.1")  # SSD optimization
                
        @event.listens_for(self.engine, 'checkout')
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Track active connections"""
            self._connection_stats['active_connections'] += 1
            
        @event.listens_for(self.engine, 'checkin')
        def on_checkin(dbapi_connection, connection_record):
            """Track connection returns"""
            self._connection_stats['active_connections'] -= 1
            
        @event.listens_for(self.engine, 'invalidate')
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation"""
            logger.warning(f"⚠️ Connection invalidated: {exception}")
            
    @with_retry(max_retries=3, retry_delay=1.0)
    @handle_db_errors
    def _test_connection(self) -> bool:
        """Test database connectivity with standardized retry handling"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                self._connection_stats['successful_connections'] += 1
                return True
        self._connection_stats['failed_connections'] += 1
        return False
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for raw database connections
        
        Yields:
            Connection: Raw database connection object
        """
        if not self._is_connected:
            raise ConnectionError("Database not initialized. Call initialize() first.")
        
        # Get connection from engine
        conn = self.engine.raw_connection()
        try:
            yield conn
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise
        finally:
            conn.close()
    
    @contextmanager
    def get_session(self, auto_commit: bool = True) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic error handling
        
        Args:
            auto_commit: Whether to auto-commit on success
            
        Yields:
            Session: SQLAlchemy session object
        """
        if not self._is_connected:
            raise ConnectionError("Database not initialized. Call initialize() first.")
        
        session = self.SessionLocal()
        try:
            yield session
            if auto_commit:
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_with_retry(self, operation, max_retries: int = 3, *args, **kwargs):
        """
        Execute database operation with automatic retry on failure
        
        Args:
            operation: Function to execute
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the operation
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except (OperationalError, DisconnectionError, PsycopgOperationalError) as e:
                last_exception = e
                logger.warning(f"⚠️ Operation failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (attempt * 0.1)
                    time.sleep(wait_time)
                    
                    # Try to reconnect if connection is lost
                    if not self._test_connection():
                        logger.info("🔄 Attempting to reconnect to database...")
                        self.reconnect()
            except Exception as e:
                logger.error(f"❌ Non-recoverable error: {e}")
                raise
                
        # If all retries failed
        raise last_exception or Exception("All retry attempts failed")
    
    def reconnect(self) -> bool:
        """Reconnect to database after connection loss"""
        try:
            if self.engine:
                self.engine.dispose()
            return self.initialize(self._connection_string)
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        if self.engine and hasattr(self.engine.pool, 'size'):
            self._connection_stats.update({
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'overflow': self.engine.pool.overflow(),
                'checked_out': self.engine.pool.checkedout()
            })
        
        return self._connection_stats.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_status = {
            'connected': False,
            'response_time_ms': None,
            'pool_status': {},
            'errors': []
        }
        
        try:
            start_time = time.time()
            
            with self.get_session() as session:
                # Test basic query
                session.execute(text("SELECT 1"))
                
                # Test table access
                session.execute(text("SELECT COUNT(*) FROM requirements LIMIT 1"))
                
            end_time = time.time()
            
            health_status.update({
                'connected': True,
                'response_time_ms': round((end_time - start_time) * 1000, 2),
                'pool_status': self.get_connection_stats()
            })
            
        except Exception as e:
            health_status['errors'].append(str(e))
            logger.error(f"❌ Health check failed: {e}")
        
        return health_status
    
    def optimize_database(self):
        """Run database optimization commands"""
        optimization_queries = [
            "ANALYZE;",  # Update table statistics
            "VACUUM (ANALYZE);",  # Cleanup and analyze
            "REINDEX DATABASE resume_customizer;",  # Rebuild indexes
        ]
        
        try:
            with self.get_session() as session:
                for query in optimization_queries:
                    logger.info(f"🔧 Running optimization: {query}")
                    session.execute(text(query))
                    session.commit()
            logger.info("✅ Database optimization completed")
        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
    
    def close(self):
        """Close all database connections"""
        try:
            if self.engine:
                self.engine.dispose()
                self._is_connected = False
                logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")

# Global connection manager instance
db_manager = DatabaseConnectionManager()

# Convenience functions for external use
def get_db_session():
    """Get database session context manager"""
    return db_manager.get_session()

def initialize_database(database_url: Optional[str] = None, **kwargs) -> bool:
    """Initialize database connection"""
    return db_manager.initialize(database_url, **kwargs)

def get_database_stats() -> Dict[str, Any]:
    """Get database connection statistics"""
    return db_manager.get_connection_stats()

def database_health_check() -> Dict[str, Any]:
    """Perform database health check"""
    return db_manager.health_check()



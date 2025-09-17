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
from database.config import get_connection_string, get_engine_config
import threading

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from sqlalchemy.pool import QueuePool
import psycopg2
from psycopg2 import OperationalError as PsycopgOperationalError

# Import with fallback for missing modules
try:
    from database.error_handler import handle_db_errors, with_retry, ConnectionError
except ImportError:
    def handle_db_errors(func):
        return func
    def with_retry(max_retries=3, retry_delay=1.0):
        def decorator(func):
            return func
        return decorator
    class ConnectionError(Exception):
        pass

try:
    from database.query_monitor import setup_query_monitoring
except ImportError:
    def setup_query_monitoring(engine, slow_query_threshold_ms=100):
        pass

try:
    from database.adaptive_pool import setup_adaptive_pooling
except ImportError:
    def setup_adaptive_pooling(engine, min_pool_size=5, max_pool_size=30):
        return None

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
                # Use centralized DatabaseConfig to build connection string
                database_url = get_connection_string()
            
            # Avoid printing full connection URL (may contain secrets)
            logger.info("Attempting to initialize database engine (connection details masked)")
            self._connection_string = database_url
            
            # Load centralized engine configuration and allow overrides via kwargs
            engine_config = get_engine_config() or {}
            # Allow overriding via env for SQL echo
            engine_config['echo'] = os.getenv('DB_ECHO', 'false').lower() == 'true'
            # Merge any explicit kwargs into engine_config (kwargs take precedence)
            engine_config.update(kwargs)
            
            # Create engine with optimizations
            self.engine = create_engine(database_url, **engine_config)
            
            # Set up query monitoring
            setup_query_monitoring(self.engine, slow_query_threshold_ms=100)
            
            # Set up adaptive connection pooling using centralized pool config
            min_pool = int(engine_config.get('pool_size', 5))
            max_pool = int(min_pool + int(engine_config.get('max_overflow', 10)))
            self.pool_manager = setup_adaptive_pooling(
                self.engine,
                min_pool_size=min_pool,
                max_pool_size=max_pool
            )
            
            # Configure session factory
            # Use conservative session defaults: expire objects on commit to avoid stale state
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=True,
                bind=self.engine,
                expire_on_commit=True
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
    
    def create_database_if_not_exists(self) -> bool:
        """Create database if it doesn't exist"""
        try:
            # Parse connection string to get database name
            from urllib.parse import urlparse
            parsed = urlparse(self._connection_string)
            db_name = parsed.path[1:]  # Remove leading '/'
            
            # Create connection to postgres database
            admin_conn_str = self._connection_string.replace(f'/{db_name}', '/postgres')
            admin_engine = create_engine(admin_conn_str)

            # Validate database name to reduce risk of SQL injection via identifiers
            import re
            if not re.match(r'^[A-Za-z0-9_\-]+$', db_name):
                logger.error(f"Invalid database name detected: {db_name}")
                return False

            # Use autocommit for CREATE DATABASE (cannot run inside a transaction)
            with admin_engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                # Check if database exists using parameterized query
                result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {'name': db_name})
                if not result.fetchone():
                    # Create database
                    conn.execute(text(f"CREATE DATABASE \"{db_name}\""))
                    logger.info(f"✅ Created database: {db_name}")
                else:
                    logger.info(f"✅ Database {db_name} already exists")

            admin_engine.dispose()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create database: {e}")
            return False
    
    def initialize_schema(self) -> bool:
        """Initialize database schema with all tables"""
        try:
            from .models import Base
            from .resume_models import ResumeDocument, ResumeCustomization, EmailSend
            from .format_models import ResumeFormat, ResumeFormatMatch
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Create indexes for better performance
            # Create additional performance indexes using autocommit (CONCURRENTLY requires no surrounding transaction)
            indexes = [
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_search ON requirements USING gin(to_tsvector('english', job_title || ' ' || client_company))",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_tech_stack ON requirements USING gin(tech_stack)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_created_status ON requirements (created_at DESC, req_status)",
            ]

            try:
                with self.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                    for index_sql in indexes:
                        try:
                            conn.execute(text(index_sql))
                        except Exception as e:
                            logger.warning(f"Index creation skipped: {e}")
            except Exception as e:
                logger.warning(f"Index creation phase skipped due to engine connection issue: {e}")
            
            logger.info("✅ Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema initialization failed: {e}")
            return False
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables with encryption"""
        # Delegate to centralized DatabaseConfig
        try:
            return get_connection_string()
        except Exception as e:
            logger.exception("Failed to build connection string from DatabaseConfig: %s", e)
            raise
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring and optimization"""
        
        @event.listens_for(self.engine, 'connect')
        def on_connect(dbapi_connection, connection_record):
            """Configure connection on creation"""
            self._connection_stats['total_connections'] += 1
            # Apply optional session-level parameters if DBAPI supports cursor
            try:
                if hasattr(dbapi_connection, 'cursor'):
                    cursor = dbapi_connection.cursor()
                    try:
                        # Only execute safe, configurable session-level parameters
                        if os.getenv('DB_SET_SYNCHRONOUS_COMMIT', 'false').lower() == 'true':
                            cursor.execute("SET synchronous_commit TO off")
                        if os.getenv('DB_SET_RANDOM_PAGE_COST', 'false').lower() == 'true':
                            cursor.execute("SET random_page_cost TO 1.1")
                    finally:
                        try:
                            cursor.close()
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Unable to set session parameters on connect: {e}")
                
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
        
        # Use SQLAlchemy Connection object which integrates with pooling
        conn = None
        try:
            conn = self.engine.connect()
            yield conn
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
    
    @contextmanager
    def get_session(self, auto_commit: bool = False) -> Generator[Session, None, None]:
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



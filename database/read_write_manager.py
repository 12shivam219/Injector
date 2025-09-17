"""
Read/Write Connection Manager for high traffic scenarios.
Provides separate connection pools for read and write operations.
"""

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from database.error_handler import handle_db_errors
from database.encryption import decrypt_connection_string
from database.query_monitor import setup_query_monitoring
from database.adaptive_pool import setup_adaptive_pooling
from database.config import get_connection_string, get_engine_config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ReadWriteManager:
    """
    Manages separate read and write database connections.

    This class provides:
    1. Separate connection pools for read and write operations.
    2. Automatic routing of queries to appropriate connection.
    3. Fallback to write connection if read connection fails.
    """

    def __init__(
        self,
        write_connection_string: Optional[str] = None,
        read_connection_string: Optional[str] = None,
        min_read_pool_size: int = 10,
        max_read_pool_size: int = 50,
        min_write_pool_size: int = 5,
        max_write_pool_size: int = 20,
    ):
        """
        Initialize read/write connection manager.

        Args:
            write_connection_string: Primary database connection string.
            read_connection_string: Read replica connection string.
            min_read_pool_size: Minimum read connection pool size.
            max_read_pool_size: Maximum read connection pool size.
            min_write_pool_size: Minimum write connection pool size.
            max_write_pool_size: Maximum write connection pool size.
        """
        # Get connection strings from parameters or centralized config
        self.write_connection_string = write_connection_string or get_connection_string()

        # Resolve read connection string with support for encrypted env var
        self.read_connection_string = (
            read_connection_string
            or self._get_read_connection_string()
            or os.getenv("DB_READ_CONNECTION_STRING")
            or self.write_connection_string
        )

        # Validate required connection string
        if not self.write_connection_string:
            raise ValueError("Write connection string is required for ReadWriteManager")

        # Connection pool settings
        self.min_read_pool_size = min_read_pool_size
        self.max_read_pool_size = max_read_pool_size
        self.min_write_pool_size = min_write_pool_size
        self.max_write_pool_size = max_write_pool_size

        # Initialize engines and sessions
        self._initialize_connections()

    def _get_read_connection_string(self) -> Optional[str]:
        """
        Get read database connection string from environment
        or use write connection if not set.
        """
        encrypted_read_conn_str = os.getenv("DB_ENCRYPTED_READ_CONNECTION_STRING")
        if encrypted_read_conn_str:
            conn_str = decrypt_connection_string(encrypted_read_conn_str)
            if conn_str:
                return conn_str

        read_conn = os.getenv("DB_READ_CONNECTION_STRING")
        if read_conn:
            return read_conn

        # No read replica configured
        return None

    @handle_db_errors
    def _initialize_connections(self) -> None:
        """Initialize read and write database connections."""
        # Use centralized engine config where possible
        engine_opts = get_engine_config() or {}

        # Override pool sizes from constructor args
        write_opts = engine_opts.copy()
        write_opts.update(
            {
                "pool_size": self.min_write_pool_size,
                "max_overflow": max(
                    0, self.max_write_pool_size - self.min_write_pool_size
                ),
            }
        )

        read_opts = engine_opts.copy()
        read_opts.update(
            {
                "pool_size": self.min_read_pool_size,
                "max_overflow": max(
                    0, self.max_read_pool_size - self.min_read_pool_size
                ),
            }
        )

        # Create write engine
        self.write_engine = create_engine(self.write_connection_string, **write_opts)

        # Create read engine (fallback to write connection if none)
        read_conn_str = self.read_connection_string or self.write_connection_string
        self.read_engine = create_engine(read_conn_str, **read_opts)

        # Create session factories
        self.WriteSession = scoped_session(sessionmaker(bind=self.write_engine))
        self.ReadSession = scoped_session(sessionmaker(bind=self.read_engine))

        # Set up monitoring and adaptive pooling
        setup_query_monitoring(self.write_engine, slow_query_threshold_ms=100)
        setup_query_monitoring(self.read_engine, slow_query_threshold_ms=200)

        self.write_pool_manager = setup_adaptive_pooling(
            self.write_engine,
            min_pool_size=self.min_write_pool_size,
            max_pool_size=self.max_write_pool_size,
        )

        self.read_pool_manager = setup_adaptive_pooling(
            self.read_engine,
            min_pool_size=self.min_read_pool_size,
            max_pool_size=self.max_read_pool_size,
        )

    def get_read_session(self) -> Session:
        """Get a read-only database session."""
        return self.ReadSession()

    def get_write_session(self) -> Session:
        """Get a write-enabled database session."""
        return self.WriteSession()

    def get_session(self, for_write: bool = False) -> Session:
        """
        Get appropriate database session based on operation type.

        Args:
            for_write: True for write operations, False for read-only.

        Returns:
            Database session from appropriate connection pool.
        """
        if for_write:
            return self.get_write_session()
        return self.get_read_session()

    def close(self) -> None:
        """Close all database connections."""
        if hasattr(self, "ReadSession"):
            self.ReadSession.remove()

        if hasattr(self, "WriteSession"):
            self.WriteSession.remove()

        if hasattr(self, "read_pool_manager"):
            self.read_pool_manager.stop()

        if hasattr(self, "write_pool_manager"):
            self.write_pool_manager.stop()


# Global read/write manager instance
read_write_manager = None


def get_read_write_manager() -> ReadWriteManager:
    """Get or create global read/write manager instance."""
    global read_write_manager
    if read_write_manager is None:
        read_write_manager = ReadWriteManager()
    return read_write_manager


def get_read_session() -> Session:
    """Get a read-only database session."""
    return get_read_write_manager().get_read_session()


def get_write_session() -> Session:
    """Get a write-enabled database session."""
    return get_read_write_manager().get_write_session()


def get_session(for_write: bool = False) -> Session:
    """Get appropriate database session based on operation type."""
    return get_read_write_manager().get_session(for_write)

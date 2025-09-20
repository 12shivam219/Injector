"""
Session management for SQLAlchemy database operations.

Provides session factory and context managers for database operations.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

# Import from our connection module
from .connection import db_manager


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get database session context manager.
    
    This function provides a context manager that automatically handles
    session creation, transaction management, and cleanup.
    
    Yields:
        Session: SQLAlchemy session object
        
    Example:
        with get_session() as session:
            user = session.query(User).first()
    """
    # Use the existing connection manager's session context manager
    with db_manager.get_session() as session:
        yield session


@contextmanager
def get_db_session(auto_commit: bool = False) -> Generator[Session, None, None]:
    """
    Alternative session context manager with auto-commit option.
    
    Args:
        auto_commit: Whether to auto-commit on success
        
    Yields:
        Session: SQLAlchemy session object
    """
    with db_manager.get_session(auto_commit=auto_commit) as session:
        yield session


def get_session_factory():
    """
    Get the SessionLocal factory from the connection manager.
    
    Returns:
        SessionLocal factory for creating sessions
    """
    if not db_manager.SessionLocal:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return db_manager.SessionLocal


# For backward compatibility and convenience
SessionLocal = property(get_session_factory)

__all__ = [
    'get_session',
    'get_db_session', 
    'get_session_factory',
    'SessionLocal'
]
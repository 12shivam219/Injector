"""
Database read/write session management utilities.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from ..connection import db_manager

@contextmanager
def get_read_session() -> Generator[Session, None, None]:
    """Get a read-only database session."""
    with db_manager.get_session(auto_commit=False) as session:
        yield session

@contextmanager
def get_write_session() -> Generator[Session, None, None]:
    """Get a writable database session with auto-commit."""
    with db_manager.get_session(auto_commit=True) as session:
        yield session

__all__ = ['get_read_session', 'get_write_session']
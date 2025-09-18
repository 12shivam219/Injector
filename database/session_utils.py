"""
Database session utilities
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from database.connection import get_db_session

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session using context manager"""
    from database.connection import db_manager
    if not db_manager._is_connected:
        db_manager.initialize()
    
    with db_manager.get_session() as session:
        yield session
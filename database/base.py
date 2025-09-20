"""
Shared SQLAlchemy declarative base and base model for the project.

All models should import `Base` and `BaseModel` from this module to ensure
a single metadata object is used for schema creation and migrations.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime
from datetime import datetime
import uuid

# Single declarative base for the entire application
Base = declarative_base()

class BaseModel(Base):
    """
    Abstract base model class that provides common fields and functionality
    for all database models.
    """
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())

    def __repr__(self):
        """String representation of the model"""
        return f"<{self.__class__.__name__} id={self.id}>"

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update(self, **kwargs):
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

__all__ = ['Base', 'BaseModel']

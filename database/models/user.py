"""
User models for Resume Customizer application.
Provides database models for user authentication and management.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from ..base import BaseModel

# Optional encryption import
try:
    from ..utils.custom_types import EncryptedBinaryString
    ENCRYPTION_AVAILABLE = True
except ImportError:
    from sqlalchemy import LargeBinary
    EncryptedBinaryString = LargeBinary  # Fallback to regular binary
    ENCRYPTION_AVAILABLE = False


class User(BaseModel):
    """User model for authentication and user management."""
    __tablename__ = 'users'
    
    # User identification
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    
    # Authentication
    password_hash = Column(EncryptedBinaryString, nullable=False)
    reset_token = Column(String(100), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    
    # User status
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # User profile - sensitive profile data is now encrypted
    display_name = Column(String(100), nullable=True)
    profile_data = Column(JSONB, default=dict)
    
    # Additional security fields
    security_questions = Column(String(500), nullable=True)
    mfa_secret = Column(String(100), nullable=True)
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_user_username', username),
        Index('idx_user_email', email),
        Index('idx_user_active', is_active),
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


__all__ = ['User']
"""
Database models package.

This package exports all database models for the Resume Customizer application.
All models use the same declarative base and follow consistent patterns.
"""

# Import Base and BaseModel from the main base module
from ..base import Base, BaseModel

# Import all models from their respective modules
from .user import User

from .resume import (
    ResumeDocument,
    ResumeCustomization,
    EmailSend,
    ProcessingLog,
    UserSession,
    ResumeAnalytics
)

from .requirements import (
    Requirement,
    RequirementComment,
    RequirementConsultant,
    DatabaseStats,
    AuditLog,
    RequirementSummaryView
)

from .format import (
    ResumeFormat,
    ResumeFormatMatch,
    FormatElement
)

__all__ = [
    # Base classes
    'Base',
    'BaseModel',
    
    # User models
    'User',
    
    # Resume models
    'ResumeDocument',
    'ResumeCustomization',
    'EmailSend',
    'ProcessingLog',
    'UserSession',
    'ResumeAnalytics',
    
    # Requirements models
    'Requirement',
    'RequirementComment',
    'RequirementConsultant',
    'DatabaseStats',
    'AuditLog',
    'RequirementSummaryView',
    
    # Format models
    'ResumeFormat',
    'ResumeFormatMatch',
    'FormatElement'
]

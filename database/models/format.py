"""
Database models for resume format patterns and analysis
"""

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import BaseModel


class ResumeFormat(BaseModel):
    """Stores resume format templates and their patterns"""
    __tablename__ = 'resume_formats'

    name = Column(String(255), nullable=False, unique=True)
    description = Column(String(1000))
    
    # Format patterns stored as JSON
    name_pattern = Column(JSON)  # {start_marker: str, end_marker: str, regex: str}
    email_pattern = Column(JSON)  # {start_marker: str, end_marker: str, regex: str}
    phone_pattern = Column(JSON)  # {start_marker: str, end_marker: str, regex: str}
    
    # Section patterns
    section_patterns = Column(JSON)  # {section_name: {start_marker, end_marker, expected_content}}
    
    # Company and title patterns
    company_patterns = Column(JSON)  # List of {company_name, position, date_format, pattern}
    title_patterns = Column(JSON)  # List of {title_type, pattern, location}
    
    # Stats and metadata
    match_count = Column(Integer, default=0)  # Number of resumes matched to this format
    last_used = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    version = Column(String(10), nullable=False, server_default='1.0')  # Format version
    
    # Relationships
    matches = relationship("ResumeFormatMatch", back_populates="format")

    def __repr__(self):
        return f"<ResumeFormat(name='{self.name}', matches={self.match_count})>"


class ResumeFormatMatch(BaseModel):
    """Records which resumes matched which formats"""
    __tablename__ = 'resume_format_matches'

    format_id = Column(String(36), ForeignKey('resume_formats.id'))
    resume_hash = Column(String(64), nullable=False)  # Hash of the resume content
    match_score = Column(Integer)  # Score out of 100
    matched_elements = Column(JSON)  # Details of what was matched
    
    # When this match was made
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    format = relationship("ResumeFormat", back_populates="matches")

    def __repr__(self):
        return f"<ResumeFormatMatch(format='{self.format.name if self.format else 'Unknown'}', score={self.match_score})>"


class FormatElement(BaseModel):
    """Stores individual elements found in resume formats"""
    __tablename__ = 'format_elements'

    format_id = Column(Integer, ForeignKey('resume_formats.id'))
    element_type = Column(String(50))  # 'company', 'title', 'section', etc.
    element_value = Column(String(255))  # The actual text found
    frequency = Column(Integer, default=1)  # How often this element appears
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    
    # Pattern information
    context_before = Column(String(500))  # Text that typically appears before
    context_after = Column(String(500))   # Text that typically appears after
    pattern_data = Column(JSON)  # Additional pattern information
    
    def __repr__(self):
        return f"<FormatElement(type='{self.element_type}', value='{self.element_value}')>"


__all__ = [
    'ResumeFormat',
    'ResumeFormatMatch', 
    'FormatElement'
]
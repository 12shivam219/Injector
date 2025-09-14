"""
Database Models for Resume Customizer Application
Comprehensive PostgreSQL models with high performance and scalability features
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

Base = declarative_base()

class BaseModel(Base):
    """Base model with common fields for all tables"""
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking

class Requirement(BaseModel):
    """
    Main Requirements table with comprehensive fields and optimizations
    Designed for high performance with proper indexing and constraints
    """
    __tablename__ = 'requirements'
    
    # Basic requirement information
    req_status = Column(
        String(50), 
        nullable=False, 
        default='New', 
        index=True,
        server_default='New'
    )
    applied_for = Column(
        String(100), 
        nullable=False, 
        default='Raju', 
        index=True,
        server_default='Raju'
    )
    next_step = Column(Text)
    rate = Column(String(100))  # Flexible string to handle various rate formats
    tax_type = Column(
        String(50), 
        nullable=False, 
        default='C2C', 
        index=True,
        server_default='C2C'
    )
    
    # Company information
    client_company = Column(String(255), nullable=False, index=True)
    prime_vendor_company = Column(String(255), index=True)
    
    # Vendor details (normalized for better performance)
    vendor_company = Column(String(255), index=True)
    vendor_person_name = Column(String(255), index=True)
    vendor_phone_number = Column(String(50))
    vendor_email = Column(String(255), index=True)
    
    # Job requirement information
    requirement_entered_date = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    got_requirement_from = Column(String(100), nullable=False, default='Got from online resume', index=True)
    job_title = Column(String(255), nullable=False, index=True)
    job_portal_link = Column(Text)
    primary_tech_stack = Column(String(255), index=True)
    complete_job_description = Column(Text)
    
    # Tech stack as JSONB for high performance queries
    tech_stack = Column(JSONB, default=list, nullable=False)
    
    # Legacy fields for backward compatibility
    legacy_data = Column(JSONB, default=dict)
    
    # Interview information
    interview_id = Column(String(100), unique=True, index=True)
    
    # Relationships
    comments = relationship("RequirementComment", back_populates="requirement", cascade="all, delete-orphan")
    consultants = relationship("RequirementConsultant", back_populates="requirement", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            req_status.in_(['New', 'Working', 'Applied', 'Cancelled', 'Submitted', 'Interviewed', 'On Hold']),
            name='valid_req_status'
        ),
        CheckConstraint(
            tax_type.in_(['C2C', '1099', 'W2', 'Fulltime']),
            name='valid_tax_type'
        ),
        CheckConstraint(
            applied_for.in_(['Raju', 'Eric']),
            name='valid_applied_for'
        ),
        CheckConstraint(
            got_requirement_from.in_(['Got from online resume', 'Got through Job Portal']),
            name='valid_requirement_source'
        ),
        # Composite indexes for common query patterns
        Index('idx_req_status_applied_for', req_status, applied_for),
        Index('idx_client_job_title', client_company, job_title),
        Index('idx_created_status', 'created_at', req_status),
        Index('idx_tech_stack_gin', tech_stack, postgresql_using='gin'),  # GIN index for JSONB queries
        Index('idx_requirement_search', job_title, client_company, primary_tech_stack),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses"""
        return {
            'id': str(self.id),
            'req_status': self.req_status,
            'applied_for': self.applied_for,
            'next_step': self.next_step,
            'rate': self.rate,
            'tax_type': self.tax_type,
            'client_company': self.client_company,
            'prime_vendor_company': self.prime_vendor_company,
            'vendor_details': {
                'vendor_company': self.vendor_company,
                'vendor_person_name': self.vendor_person_name,
                'vendor_phone_number': self.vendor_phone_number,
                'vendor_email': self.vendor_email
            },
            'job_requirement_info': {
                'requirement_entered_date': self.requirement_entered_date.isoformat() if self.requirement_entered_date else None,
                'got_requirement_from': self.got_requirement_from,
                'tech_stack': self.tech_stack or [],
                'job_title': self.job_title,
                'job_portal_link': self.job_portal_link,
                'primary_tech_stack': self.primary_tech_stack,
                'complete_job_description': self.complete_job_description
            },
            'interview_id': self.interview_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version,
            'is_active': self.is_active
        }

class RequirementComment(BaseModel):
    """
    Comments table with optimized structure for timeline queries
    """
    __tablename__ = 'requirement_comments'
    
    requirement_id = Column(UUID(as_uuid=True), ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False, index=True)
    comment_text = Column(Text, nullable=False)
    author = Column(String(255), nullable=False, default='System', index=True)
    comment_type = Column(String(50), default='marketing', index=True)  # marketing, system, user, etc.
    
    # Relationship
    requirement = relationship("Requirement", back_populates="comments")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_req_comments_timeline', requirement_id, 'created_at'),
        Index('idx_comments_author_type', author, comment_type),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert comment to dictionary"""
        return {
            'id': str(self.id),
            'comment': self.comment_text,
            'timestamp': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'author': self.author,
            'comment_type': self.comment_type
        }

class RequirementConsultant(BaseModel):
    """
    Many-to-many relationship between requirements and consultants
    """
    __tablename__ = 'requirement_consultants'
    
    requirement_id = Column(UUID(as_uuid=True), ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False, index=True)
    consultant_name = Column(String(255), nullable=False, index=True)
    role = Column(String(100), default='consultant')
    priority = Column(Integer, default=1)  # For ordering
    
    # Relationship
    requirement = relationship("Requirement", back_populates="consultants")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('requirement_id', 'consultant_name', name='unique_req_consultant'),
        Index('idx_consultant_name', consultant_name),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert consultant assignment to dictionary"""
        return {
            'consultant_name': self.consultant_name,
            'role': self.role,
            'priority': self.priority
        }

class DatabaseStats(BaseModel):
    """
    Table for tracking database statistics and performance metrics
    """
    __tablename__ = 'database_stats'
    
    stat_name = Column(String(255), nullable=False, unique=True, index=True)
    stat_value = Column(JSONB, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    
    __table_args__ = (
        Index('idx_stats_category', category),
    )

class AuditLog(BaseModel):
    """
    Audit log for tracking all database changes
    """
    __tablename__ = 'audit_logs'
    
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation = Column(String(50), nullable=False, index=True)  # INSERT, UPDATE, DELETE
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    user_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    __table_args__ = (
        Index('idx_audit_table_operation', table_name, operation),
        Index('idx_audit_timeline', 'created_at'),
        Index('idx_audit_record', record_id, table_name),
    )

# Performance optimization: Create materialized view for common queries
class RequirementSummaryView(Base):
    """
    Materialized view for high-performance requirement summaries
    This will be created as an actual materialized view in PostgreSQL
    """
    __tablename__ = 'requirement_summary_view'
    __table_args__ = {'info': {'is_view': True}}
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    req_status = Column(String(50))
    applied_for = Column(String(100))
    client_company = Column(String(255))
    job_title = Column(String(255))
    primary_tech_stack = Column(String(255))
    tech_stack_count = Column(Integer)
    comment_count = Column(Integer)
    consultant_count = Column(Integer)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    days_since_created = Column(Integer)
    status_priority = Column(Integer)  # For sorting by status importance



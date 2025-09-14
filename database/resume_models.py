"""
Resume-specific Database Models for Resume Customizer Application
Models for storing resume data, customizations, and processing history
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

from .models import BaseModel, Base

class ResumeDocument(BaseModel):
    """
    Main table for storing resume documents and metadata
    """
    __tablename__ = 'resume_documents'
    
    # Basic document information
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    file_hash = Column(String(64), unique=True, index=True)  # SHA-256 hash for deduplication
    mime_type = Column(String(100), default='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    
    # Document content
    original_content = Column(Text)  # Extracted text content
    processed_content = Column(Text)  # Processed/cleaned content
    document_structure = Column(JSONB)  # Document structure metadata
    
    # Processing status
    processing_status = Column(String(50), default='uploaded', index=True)
    processing_error = Column(Text)
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    
    # User information
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), index=True)
    
    # Relationships
    customizations = relationship("ResumeCustomization", back_populates="resume_document", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="resume_document", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            processing_status.in_(['uploaded', 'processing', 'completed', 'failed', 'archived']),
            name='valid_processing_status'
        ),
        Index('idx_resume_user_status', user_id, processing_status),
        Index('idx_resume_filename', filename),
        Index('idx_resume_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resume document to dictionary"""
        return {
            'id': str(self.id),
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'mime_type': self.mime_type,
            'processing_status': self.processing_status,
            'processing_error': self.processing_error,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'customization_count': len(self.customizations) if self.customizations else 0
        }

class ResumeCustomization(BaseModel):
    """
    Table for storing resume customizations and job-specific modifications
    """
    __tablename__ = 'resume_customizations'
    
    # Foreign key to resume document
    resume_document_id = Column(UUID(as_uuid=True), ForeignKey('resume_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Job/requirement information
    job_title = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    job_description = Column(Text)
    
    # Tech stack and requirements
    tech_stack_input = Column(JSONB, default=list)  # User-provided tech stack
    required_skills = Column(JSONB, default=list)  # Extracted required skills
    matched_skills = Column(JSONB, default=list)  # Skills that match resume
    
    # Customization content
    customized_content = Column(Text)  # Final customized resume content
    added_bullet_points = Column(JSONB, default=list)  # New bullet points added
    modified_sections = Column(JSONB, default=dict)  # Sections that were modified
    
    # Processing metadata
    customization_strategy = Column(String(100), default='tech_stack_injection')
    ai_model_used = Column(String(100))
    processing_time_seconds = Column(Float)
    
    # Status and quality metrics
    customization_status = Column(String(50), default='pending', index=True)
    quality_score = Column(Float)  # 0.0 to 1.0
    match_percentage = Column(Float)  # Percentage of job requirements matched
    
    # User feedback
    user_rating = Column(Integer)  # 1-5 star rating
    user_feedback = Column(Text)
    
    # Relationships
    resume_document = relationship("ResumeDocument", back_populates="customizations")
    email_sends = relationship("EmailSend", back_populates="customization", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            customization_status.in_(['pending', 'processing', 'completed', 'failed', 'sent']),
            name='valid_customization_status'
        ),
        CheckConstraint(
            user_rating >= 1 and user_rating <= 5,
            name='valid_user_rating'
        ),
        Index('idx_customization_job', job_title, company_name),
        Index('idx_customization_status', customization_status, 'created_at'),
        Index('idx_customization_quality', 'quality_score'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert customization to dictionary"""
        return {
            'id': str(self.id),
            'resume_document_id': str(self.resume_document_id),
            'job_title': self.job_title,
            'company_name': self.company_name,
            'job_description': self.job_description,
            'tech_stack_input': self.tech_stack_input or [],
            'required_skills': self.required_skills or [],
            'matched_skills': self.matched_skills or [],
            'customization_status': self.customization_status,
            'quality_score': self.quality_score,
            'match_percentage': self.match_percentage,
            'user_rating': self.user_rating,
            'processing_time_seconds': self.processing_time_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EmailSend(BaseModel):
    """
    Table for tracking email sends and delivery status
    """
    __tablename__ = 'email_sends'
    
    # Foreign key to customization
    customization_id = Column(UUID(as_uuid=True), ForeignKey('resume_customizations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Email details
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255))
    subject = Column(String(500), nullable=False)
    body = Column(Text)
    
    # Attachment information
    attachment_filename = Column(String(255))
    attachment_size = Column(Integer)
    
    # Send status and tracking
    send_status = Column(String(50), default='pending', index=True)
    send_error = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    
    # Email service metadata
    email_service_id = Column(String(255))  # ID from email service provider
    email_service = Column(String(100), default='yagmail')
    
    # Relationships
    customization = relationship("ResumeCustomization", back_populates="email_sends")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            send_status.in_(['pending', 'sending', 'sent', 'failed', 'delivered', 'bounced']),
            name='valid_send_status'
        ),
        Index('idx_email_recipient', recipient_email),
        Index('idx_email_status_date', send_status, 'sent_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert email send to dictionary"""
        return {
            'id': str(self.id),
            'customization_id': str(self.customization_id),
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'send_status': self.send_status,
            'send_error': self.send_error,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'email_service': self.email_service,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ProcessingLog(BaseModel):
    """
    Detailed logging table for tracking processing steps and performance
    """
    __tablename__ = 'processing_logs'
    
    # Foreign key to resume document
    resume_document_id = Column(UUID(as_uuid=True), ForeignKey('resume_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Log details
    log_level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    step_name = Column(String(100), index=True)
    
    # Performance metrics
    execution_time_ms = Column(Float)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    # Context information
    function_name = Column(String(255))
    line_number = Column(Integer)
    stack_trace = Column(Text)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    resume_document = relationship("ResumeDocument", back_populates="processing_logs")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            log_level.in_(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
            name='valid_log_level'
        ),
        Index('idx_log_level_time', log_level, 'created_at'),
        Index('idx_log_step', step_name, 'created_at'),
    )

class UserSession(BaseModel):
    """
    Table for tracking user sessions and activity
    """
    __tablename__ = 'user_sessions'
    
    # Session information
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Session activity
    last_activity = Column(DateTime(timezone=True), default=func.now(), index=True)
    page_views = Column(Integer, default=0)
    actions_performed = Column(Integer, default=0)
    
    # Session data
    session_data = Column(JSONB, default=dict)
    preferences = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    ended_at = Column(DateTime(timezone=True))
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_session_user_active', user_id, is_active),
        Index('idx_session_activity', 'last_activity'),
    )

# Performance Analytics Views
class ResumeAnalytics(Base):
    """
    Materialized view for resume processing analytics
    """
    __tablename__ = 'resume_analytics_view'
    __table_args__ = {'info': {'is_view': True}}
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    date = Column(DateTime(timezone=True))
    total_resumes = Column(Integer)
    total_customizations = Column(Integer)
    total_emails_sent = Column(Integer)
    avg_processing_time = Column(Float)
    avg_quality_score = Column(Float)
    success_rate = Column(Float)
    popular_tech_stacks = Column(JSONB)
    top_companies = Column(JSONB)

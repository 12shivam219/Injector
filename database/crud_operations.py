"""
CRUD Operations for Resume Customizer PostgreSQL Database
Comprehensive Create, Read, Update, Delete operations with examples
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from .connection import get_db_session, db_manager
from .models import Requirement, RequirementComment, RequirementConsultant, AuditLog
from .resume_models import (
    ResumeDocument, ResumeCustomization, EmailSend, 
    ProcessingLog, UserSession
)

logger = logging.getLogger(__name__)

class ResumeCRUDOperations:
    """
    Comprehensive CRUD operations for Resume Customizer database
    """
    
    def __init__(self):
        self.session_manager = db_manager
    
    # ==================== RESUME DOCUMENT OPERATIONS ====================
    
    def create_resume_document(self, resume_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new resume document record
        
        Args:
            resume_data: Dictionary containing resume information
            
        Returns:
            str: Resume document ID if successful, None otherwise
        """
        try:
            with get_db_session() as session:
                resume_doc = ResumeDocument(
                    filename=resume_data['filename'],
                    original_filename=resume_data['original_filename'],
                    file_size=resume_data.get('file_size'),
                    file_hash=resume_data.get('file_hash'),
                    mime_type=resume_data.get('mime_type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                    original_content=resume_data.get('original_content'),
                    processed_content=resume_data.get('processed_content'),
                    document_structure=resume_data.get('document_structure', {}),
                    processing_status='uploaded',
                    user_id=resume_data['user_id'],
                    session_id=resume_data.get('session_id')
                )
                
                session.add(resume_doc)
                session.flush()  # Get the ID without committing
                
                # Log the creation
                self._log_processing_step(
                    session, 
                    resume_doc.id, 
                    'INFO', 
                    f'Resume document created: {resume_data["filename"]}',
                    'document_creation'
                )
                
                session.commit()
                logger.info(f"✅ Resume document created: {resume_doc.id}")
                return str(resume_doc.id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create resume document: {e}")
            return None
    
    def get_resume_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a resume document by ID
        
        Args:
            document_id: UUID of the resume document
            
        Returns:
            Dict containing resume document data or None
        """
        try:
            with get_db_session() as session:
                resume_doc = session.query(ResumeDocument).filter(
                    ResumeDocument.id == document_id,
                    ResumeDocument.is_active == True
                ).first()
                
                if resume_doc:
                    return resume_doc.to_dict()
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve resume document {document_id}: {e}")
            return None
    
    def get_user_resumes(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all resume documents for a specific user
        
        Args:
            user_id: User identifier
            limit: Maximum number of resumes to return
            
        Returns:
            List of resume document dictionaries
        """
        try:
            with get_db_session() as session:
                resumes = session.query(ResumeDocument).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeDocument.is_active == True
                ).order_by(desc(ResumeDocument.created_at)).limit(limit).all()
                
                return [resume.to_dict() for resume in resumes]
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve user resumes for {user_id}: {e}")
            return []
    
    def update_resume_processing_status(self, document_id: str, status: str, error: str = None) -> bool:
        """
        Update resume processing status
        
        Args:
            document_id: Resume document ID
            status: New processing status
            error: Error message if status is 'failed'
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                resume_doc = session.query(ResumeDocument).filter(
                    ResumeDocument.id == document_id
                ).first()
                
                if not resume_doc:
                    return False
                
                old_status = resume_doc.processing_status
                resume_doc.processing_status = status
                resume_doc.processing_error = error
                
                if status == 'processing':
                    resume_doc.processing_started_at = func.now()
                elif status in ['completed', 'failed']:
                    resume_doc.processing_completed_at = func.now()
                
                # Log the status change
                self._log_processing_step(
                    session,
                    document_id,
                    'INFO',
                    f'Status changed from {old_status} to {status}',
                    'status_update'
                )
                
                session.commit()
                logger.info(f"✅ Resume {document_id} status updated to {status}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update resume status: {e}")
            return False
    
    # ==================== RESUME CUSTOMIZATION OPERATIONS ====================
    
    def create_customization(self, customization_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new resume customization
        
        Args:
            customization_data: Dictionary containing customization information
            
        Returns:
            str: Customization ID if successful
        """
        try:
            with get_db_session() as session:
                customization = ResumeCustomization(
                    resume_document_id=customization_data['resume_document_id'],
                    job_title=customization_data['job_title'],
                    company_name=customization_data['company_name'],
                    job_description=customization_data.get('job_description'),
                    tech_stack_input=customization_data.get('tech_stack_input', []),
                    required_skills=customization_data.get('required_skills', []),
                    customized_content=customization_data.get('customized_content'),
                    added_bullet_points=customization_data.get('added_bullet_points', []),
                    modified_sections=customization_data.get('modified_sections', {}),
                    customization_strategy=customization_data.get('customization_strategy', 'tech_stack_injection'),
                    processing_time_seconds=customization_data.get('processing_time_seconds')
                )
                
                session.add(customization)
                session.flush()
                
                # Log the customization creation
                self._log_processing_step(
                    session,
                    customization_data['resume_document_id'],
                    'INFO',
                    f'Customization created for {customization_data["company_name"]} - {customization_data["job_title"]}',
                    'customization_creation'
                )
                
                session.commit()
                logger.info(f"✅ Customization created: {customization.id}")
                return str(customization.id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create customization: {e}")
            return None
    
    def get_customization(self, customization_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a customization by ID
        
        Args:
            customization_id: UUID of the customization
            
        Returns:
            Dict containing customization data or None
        """
        try:
            with get_db_session() as session:
                customization = session.query(ResumeCustomization).filter(
                    ResumeCustomization.id == customization_id,
                    ResumeCustomization.is_active == True
                ).first()
                
                if customization:
                    return customization.to_dict()
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve customization {customization_id}: {e}")
            return None
    
    def get_resume_customizations(self, resume_document_id: str) -> List[Dict[str, Any]]:
        """
        Get all customizations for a specific resume document
        
        Args:
            resume_document_id: Resume document UUID
            
        Returns:
            List of customization dictionaries
        """
        try:
            with get_db_session() as session:
                customizations = session.query(ResumeCustomization).filter(
                    ResumeCustomization.resume_document_id == resume_document_id,
                    ResumeCustomization.is_active == True
                ).order_by(desc(ResumeCustomization.created_at)).all()
                
                return [customization.to_dict() for customization in customizations]
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve customizations for resume {resume_document_id}: {e}")
            return []
    
    def update_customization_quality(self, customization_id: str, quality_score: float, match_percentage: float) -> bool:
        """
        Update customization quality metrics
        
        Args:
            customization_id: Customization UUID
            quality_score: Quality score (0.0 to 1.0)
            match_percentage: Match percentage (0.0 to 100.0)
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                customization = session.query(ResumeCustomization).filter(
                    ResumeCustomization.id == customization_id
                ).first()
                
                if not customization:
                    return False
                
                customization.quality_score = quality_score
                customization.match_percentage = match_percentage
                customization.customization_status = 'completed'
                
                session.commit()
                logger.info(f"✅ Customization quality updated: {customization_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update customization quality: {e}")
            return False
    
    # ==================== EMAIL OPERATIONS ====================
    
    def create_email_send(self, email_data: Dict[str, Any]) -> Optional[str]:
        """
        Create an email send record
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            str: Email send ID if successful
        """
        try:
            with get_db_session() as session:
                email_send = EmailSend(
                    customization_id=email_data['customization_id'],
                    recipient_email=email_data['recipient_email'],
                    recipient_name=email_data.get('recipient_name'),
                    subject=email_data['subject'],
                    body=email_data.get('body'),
                    attachment_filename=email_data.get('attachment_filename'),
                    attachment_size=email_data.get('attachment_size'),
                    email_service=email_data.get('email_service', 'yagmail')
                )
                
                session.add(email_send)
                session.flush()
                
                session.commit()
                logger.info(f"✅ Email send record created: {email_send.id}")
                return str(email_send.id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create email send record: {e}")
            return None
    
    def update_email_status(self, email_send_id: str, status: str, error: str = None) -> bool:
        """
        Update email send status
        
        Args:
            email_send_id: Email send UUID
            status: New status
            error: Error message if applicable
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                email_send = session.query(EmailSend).filter(
                    EmailSend.id == email_send_id
                ).first()
                
                if not email_send:
                    return False
                
                email_send.send_status = status
                email_send.send_error = error
                
                if status == 'sent':
                    email_send.sent_at = func.now()
                elif status == 'delivered':
                    email_send.delivered_at = func.now()
                
                session.commit()
                logger.info(f"✅ Email status updated: {email_send_id} -> {status}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update email status: {e}")
            return False
    
    def get_email_history(self, customization_id: str) -> List[Dict[str, Any]]:
        """
        Get email send history for a customization
        
        Args:
            customization_id: Customization UUID
            
        Returns:
            List of email send dictionaries
        """
        try:
            with get_db_session() as session:
                email_sends = session.query(EmailSend).filter(
                    EmailSend.customization_id == customization_id
                ).order_by(desc(EmailSend.created_at)).all()
                
                return [email.to_dict() for email in email_sends]
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve email history: {e}")
            return []
    
    # ==================== ANALYTICS AND REPORTING ====================
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing user statistics
        """
        try:
            with get_db_session() as session:
                # Basic counts
                total_resumes = session.query(ResumeDocument).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeDocument.is_active == True
                ).count()
                
                total_customizations = session.query(ResumeCustomization).join(
                    ResumeDocument
                ).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeCustomization.is_active == True
                ).count()
                
                total_emails = session.query(EmailSend).join(
                    ResumeCustomization
                ).join(ResumeDocument).filter(
                    ResumeDocument.user_id == user_id
                ).count()
                
                # Success rates
                successful_customizations = session.query(ResumeCustomization).join(
                    ResumeDocument
                ).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeCustomization.customization_status == 'completed'
                ).count()
                
                sent_emails = session.query(EmailSend).join(
                    ResumeCustomization
                ).join(ResumeDocument).filter(
                    ResumeDocument.user_id == user_id,
                    EmailSend.send_status == 'sent'
                ).count()
                
                # Average quality score
                avg_quality = session.query(func.avg(ResumeCustomization.quality_score)).join(
                    ResumeDocument
                ).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeCustomization.quality_score.isnot(None)
                ).scalar() or 0.0
                
                return {
                    'user_id': user_id,
                    'total_resumes': total_resumes,
                    'total_customizations': total_customizations,
                    'total_emails_sent': total_emails,
                    'successful_customizations': successful_customizations,
                    'sent_emails': sent_emails,
                    'success_rate': (successful_customizations / total_customizations * 100) if total_customizations > 0 else 0,
                    'email_success_rate': (sent_emails / total_emails * 100) if total_emails > 0 else 0,
                    'average_quality_score': round(float(avg_quality), 2)
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get user statistics: {e}")
            return {}
    
    def get_processing_performance(self, days: int = 7) -> Dict[str, Any]:
        """
        Get processing performance metrics for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing performance metrics
        """
        try:
            with get_db_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Processing times
                avg_processing_time = session.query(
                    func.avg(ResumeCustomization.processing_time_seconds)
                ).filter(
                    ResumeCustomization.created_at >= cutoff_date,
                    ResumeCustomization.processing_time_seconds.isnot(None)
                ).scalar() or 0.0
                
                # Daily processing counts
                daily_stats = session.query(
                    func.date(ResumeDocument.created_at).label('date'),
                    func.count(ResumeDocument.id).label('resumes_processed'),
                    func.count(ResumeCustomization.id).label('customizations_created')
                ).outerjoin(ResumeCustomization).filter(
                    ResumeDocument.created_at >= cutoff_date
                ).group_by(func.date(ResumeDocument.created_at)).all()
                
                return {
                    'period_days': days,
                    'average_processing_time_seconds': round(float(avg_processing_time), 2),
                    'daily_statistics': [
                        {
                            'date': stat.date.isoformat() if stat.date else None,
                            'resumes_processed': stat.resumes_processed,
                            'customizations_created': stat.customizations_created
                        }
                        for stat in daily_stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get processing performance: {e}")
            return {}
    
    # ==================== UTILITY METHODS ====================
    
    def _log_processing_step(self, session: Session, resume_document_id: str, 
                           level: str, message: str, step_name: str, 
                           execution_time_ms: float = None) -> None:
        """
        Log a processing step
        
        Args:
            session: Database session
            resume_document_id: Resume document UUID
            level: Log level
            message: Log message
            step_name: Name of the processing step
            execution_time_ms: Execution time in milliseconds
        """
        try:
            log_entry = ProcessingLog(
                resume_document_id=resume_document_id,
                log_level=level,
                message=message,
                step_name=step_name,
                execution_time_ms=execution_time_ms
            )
            session.add(log_entry)
            
        except Exception as e:
            logger.error(f"❌ Failed to log processing step: {e}")
    
    def search_resumes(self, user_id: str, search_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search resumes by filename or content
        
        Args:
            user_id: User identifier
            search_query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching resume documents
        """
        try:
            with get_db_session() as session:
                resumes = session.query(ResumeDocument).filter(
                    ResumeDocument.user_id == user_id,
                    ResumeDocument.is_active == True,
                    or_(
                        ResumeDocument.filename.ilike(f'%{search_query}%'),
                        ResumeDocument.original_filename.ilike(f'%{search_query}%'),
                        ResumeDocument.original_content.ilike(f'%{search_query}%')
                    )
                ).order_by(desc(ResumeDocument.created_at)).limit(limit).all()
                
                return [resume.to_dict() for resume in resumes]
                
        except Exception as e:
            logger.error(f"❌ Failed to search resumes: {e}")
            return []

# Global CRUD operations instance
crud_ops = ResumeCRUDOperations()

# Convenience functions
def create_resume_document(resume_data: Dict[str, Any]) -> Optional[str]:
    """Create a new resume document"""
    return crud_ops.create_resume_document(resume_data)

def get_resume_document(document_id: str) -> Optional[Dict[str, Any]]:
    """Get a resume document by ID"""
    return crud_ops.get_resume_document(document_id)

def create_customization(customization_data: Dict[str, Any]) -> Optional[str]:
    """Create a new resume customization"""
    return crud_ops.create_customization(customization_data)

def get_user_statistics(user_id: str) -> Dict[str, Any]:
    """Get user statistics"""
    return crud_ops.get_user_statistics(user_id)

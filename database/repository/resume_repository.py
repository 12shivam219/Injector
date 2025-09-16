"""
Resume repository implementation for data access layer
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from database.repository.base import BaseRepository
from database.models import ResumeDocument

class ResumeRepository(BaseRepository[ResumeDocument]):
    """Repository for Resume document operations"""
    
    def __init__(self, session: Session):
        super().__init__(ResumeDocument, session)
    
    def find_by_user_id(self, user_id: str) -> List[ResumeDocument]:
        """Find all resumes for a specific user"""
        return self.session.query(self.model_class).filter_by(user_id=user_id).all()
    
    def find_latest_by_user_id(self, user_id: str) -> Optional[ResumeDocument]:
        """Find the most recent resume for a user"""
        return (self.session.query(self.model_class)
                .filter_by(user_id=user_id)
                .order_by(desc(self.model_class.created_at))
                .first())
    
    def find_by_job_id(self, job_id: str) -> List[ResumeDocument]:
        """Find all resumes for a specific job"""
        return self.session.query(self.model_class).filter_by(job_id=job_id).all()
    
    def find_by_status(self, status: str) -> List[ResumeDocument]:
        """Find all resumes with a specific status"""
        return self.session.query(self.model_class).filter_by(status=status).all()
    
    def search_by_content(self, search_term: str) -> List[ResumeDocument]:
        """Search resumes by content"""
        search_pattern = f"%{search_term}%"
        return (self.session.query(self.model_class)
                .filter(self.model_class.content.ilike(search_pattern))
                .all())
    
    def get_recent_resumes(self, limit: int = 10) -> List[ResumeDocument]:
        """Get most recently created resumes"""
        return (self.session.query(self.model_class)
                .order_by(desc(self.model_class.created_at))
                .limit(limit)
                .all())
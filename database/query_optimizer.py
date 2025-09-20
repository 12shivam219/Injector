"""
Query Optimizer for Resume Customizer application.
Provides optimization strategies for database queries, especially for large resume sets.
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Set
from sqlalchemy import func, text, desc, asc, and_, or_, not_, select
from sqlalchemy.orm import Session, Query, joinedload, contains_eager, selectinload
from sqlalchemy.sql.expression import literal_column
from sqlalchemy.dialects.postgresql import array, ARRAY

from .base import Base
from .models import ResumeDocument, ResumeCustomization
from .utils.read_write_manager import get_read_session, get_write_session
from infrastructure.monitoring.advanced_cache import cached, CacheLevel
from infrastructure.utilities.logger import get_logger

logger = get_logger()

class QueryOptimizer:
    """
    Optimizes database queries for large resume sets.
    Provides strategies for efficient data retrieval and processing.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """Initialize query optimizer with optional session"""
        self._session = session
        self._query_stats = {}
    
    @property
    def session(self) -> Session:
        """Get or create session"""
        if self._session:
            return self._session
        return get_read_session()
    
    def optimize_resume_query(self, query: Query) -> Query:
        """
        Apply general optimization strategies to resume queries
        
        Args:
            query: SQLAlchemy query object
            
        Returns:
            Optimized query
        """
        # Apply common optimizations
        return query.options(
            # Load only what's needed in a single query
            selectinload(ResumeDocument.customizations),
            # Avoid N+1 query problems
            joinedload(ResumeDocument.processing_logs)
        )
    
    @cached(namespace="resume_counts", ttl=300)  # Cache for 5 minutes
    def get_resume_counts_by_user(self, user_id: str) -> Dict[str, int]:
        """
        Get resume counts by status for a user with caching
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of status counts
        """
        try:
            result = (self.session.query(
                ResumeDocument.processing_status,
                func.count(ResumeDocument.id).label('count')
            )
            .filter(ResumeDocument.user_id == user_id)
            .group_by(ResumeDocument.processing_status)
            .all())
            
            return {status: count for status, count in result}
        except Exception as e:
            logger.error(f"Error getting resume counts: {e}")
            return {}
    
    def get_resumes_paginated(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 20,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc"
    ) -> Tuple[List[ResumeDocument], int]:
        """
        Get paginated resume list with optimized query
        
        Args:
            user_id: User identifier
            page: Page number (1-indexed)
            page_size: Items per page
            status_filter: Filter by processing status
            sort_by: Column to sort by
            sort_dir: Sort direction ('asc' or 'desc')
            
        Returns:
            Tuple of (resume list, total count)
        """
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Build base query
        query = self.session.query(ResumeDocument).filter(
            ResumeDocument.user_id == user_id
        )
        
        # Apply status filter if provided
        if status_filter:
            query = query.filter(ResumeDocument.processing_status == status_filter)
        
        # Get total count (cached separately)
        total_count = query.count()
        
        # Apply sorting
        sort_column = getattr(ResumeDocument, sort_by, ResumeDocument.created_at)
        if sort_dir.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Apply pagination and optimization
        query = self.optimize_resume_query(query).offset(offset).limit(page_size)
        
        # Execute query
        resumes = query.all()
        
        return resumes, total_count
    
    def get_resume_with_customizations(self, resume_id: str) -> Optional[ResumeDocument]:
        """
        Get resume with all customizations efficiently loaded
        
        Args:
            resume_id: Resume document ID
            
        Returns:
            Resume document with customizations or None
        """
        query = (self.session.query(ResumeDocument)
                .options(
                    selectinload(ResumeDocument.customizations)
                    .selectinload(ResumeCustomization.email_sends)
                )
                .filter(ResumeDocument.id == resume_id))
        
        return query.first()
    
    def search_resumes_optimized(
        self, 
        user_id: str, 
        search_query: str, 
        limit: int = 20
    ) -> List[ResumeDocument]:
        """
        Search resumes with optimized full-text search
        
        Args:
            user_id: User identifier
            search_query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching resume documents
        """
        # Use PostgreSQL full-text search for better performance
        search_vector = func.to_tsvector('english', 
            ResumeDocument.filename + ' ' + 
            ResumeDocument.original_filename + ' ' + 
            ResumeDocument.original_content
        )
        search_query_tsquery = func.plainto_tsquery('english', search_query)
        
        query = (self.session.query(ResumeDocument)
                .filter(
                    ResumeDocument.user_id == user_id,
                    search_vector.op('@@')(search_query_tsquery)
                )
                .order_by(
                    # Rank results by relevance
                    func.ts_rank(search_vector, search_query_tsquery).desc()
                )
                .limit(limit))
        
        return self.optimize_resume_query(query).all()
    
    def bulk_process_resumes(
        self, 
        resume_ids: List[str], 
        update_data: Dict[str, Any]
    ) -> int:
        """
        Process multiple resumes in bulk
        
        Args:
            resume_ids: List of resume IDs to update
            update_data: Dictionary of fields to update
            
        Returns:
            Number of updated records
        """
        try:
            # Use bulk update for better performance
            result = (self.session.query(ResumeDocument)
                    .filter(ResumeDocument.id.in_(resume_ids))
                    .update(
                        update_data,
                        synchronize_session=False
                    ))
            
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in bulk processing: {e}")
            raise
             
    def process_resumes_in_batches(
        self,
        user_id: str,
        processor_func,
        batch_size: int = 100,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process large resume sets in batches to avoid memory issues
        
        Args:
            user_id: User identifier
            processor_func: Function to process each batch of resumes
            batch_size: Number of resumes to process in each batch
            status_filter: Optional filter by processing status
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "processed": 0,
            "failed": 0,
            "batches": 0
        }
        
        try:
            with get_write_session() as session:
                offset = 0
                while True:
                    # Build query for current batch
                    query = session.query(ResumeDocument).filter(
                        ResumeDocument.user_id == user_id
                    )
                    
                    if status_filter:
                        query = query.filter(ResumeDocument.processing_status == status_filter)
                    
                    # Get current batch
                    batch = query.order_by(ResumeDocument.id).offset(offset).limit(batch_size).all()
                    
                    if not batch:
                        break
                        
                    try:
                        # Process the batch
                        batch_result = processor_func(batch)
                        stats["processed"] += len(batch)
                        
                        # Update any additional stats from batch result
                        if isinstance(batch_result, dict):
                            for key, value in batch_result.items():
                                if key not in stats:
                                    stats[key] = 0
                                stats[key] += value
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")
                        stats["failed"] += len(batch)
                    
                    # Move to next batch
                    offset += batch_size
                    stats["batches"] += 1
                    
                    # Clear session to prevent memory buildup
                    session.expunge_all()
            
            return stats
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return stats
            
    def create_resume_indexes(self) -> Dict[str, Any]:
        """
        Create or update indexes for resume queries
        
        Returns:
            Dictionary with index creation results
        """
        results = {
            "created": 0,
            "errors": 0,
            "details": []
        }
        
        index_definitions = [
            # User ID index for filtering
            "CREATE INDEX IF NOT EXISTS idx_resume_user_id ON resume_documents (user_id)",
            
            # Created date index for sorting
            "CREATE INDEX IF NOT EXISTS idx_resume_created_at ON resume_documents (created_at DESC)",
            
            # Status index for filtering
            "CREATE INDEX IF NOT EXISTS idx_resume_status ON resume_documents (processing_status)",
            
            # Full-text search index
            """
            CREATE INDEX IF NOT EXISTS idx_resume_content_gin 
            ON resume_documents 
            USING gin(to_tsvector('english', coalesce(original_content, '') || ' ' || coalesce(filename, '')))
            """
        ]
        
        try:
            with get_write_session() as session:
                for idx_def in index_definitions:
                    try:
                        session.execute(text(idx_def))
                        results["created"] += 1
                        results["details"].append({
                            "status": "success",
                            "definition": idx_def
                        })
                    except Exception as e:
                        results["errors"] += 1
                        results["details"].append({
                            "status": "error",
                            "definition": idx_def,
                            "error": str(e)
                        })
                        logger.error(f"Error creating index: {e}")
                
                session.commit()
            
            return results
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return {
                "created": 0,
                "errors": 1,
                "details": [{"status": "error", "error": str(e)}]
            }
    
    def analyze_query_performance(self, query_text: str) -> Dict[str, Any]:
        """
        Analyze query performance using PostgreSQL EXPLAIN ANALYZE
        
        Args:
            query_text: SQL query to analyze
            
        Returns:
            Dictionary with query analysis results
        """
        try:
            with get_read_session() as session:
                # Run EXPLAIN ANALYZE
                result = session.execute(
                    text(f"EXPLAIN ANALYZE {query_text}")
                ).fetchall()
                
                # Parse execution plan
                plan_lines = [row[0] for row in result]
                
                # Extract key metrics
                execution_time = None
                planning_time = None
                
                for line in plan_lines:
                    if "Execution Time:" in line:
                        execution_time = float(line.split("Execution Time:")[1].split("ms")[0].strip())
                    elif "Planning Time:" in line:
                        planning_time = float(line.split("Planning Time:")[1].split("ms")[0].strip())
                
                return {
                    "success": True,
                    "execution_time_ms": execution_time,
                    "planning_time_ms": planning_time,
                    "plan": plan_lines
                }
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
_query_optimizer = None

def get_query_optimizer(session: Optional[Session] = None) -> QueryOptimizer:
    """Get or create global query optimizer instance"""
    global _query_optimizer
    
    if session:
        return QueryOptimizer(session)
        
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
        
    return _query_optimizer


# Global instance
_query_optimizer = None

def get_query_optimizer(session: Optional[Session] = None) -> QueryOptimizer:
    """Get or create global query optimizer instance"""
    global _query_optimizer
    
    if session:
        return QueryOptimizer(session)
        
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
        
    return _query_optimizer
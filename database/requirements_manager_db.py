"""
PostgreSQL-based Requirements Manager for Resume Customizer
High-performance, concurrent-safe, and scalable requirements management
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from .models import Requirement, RequirementComment, RequirementConsultant, DatabaseStats
from .connection import get_db_session, db_manager

logger = logging.getLogger(__name__)

class PostgreSQLRequirementsManager:
    """
    High-performance PostgreSQL-based Requirements Manager
    
    Features:
    - Concurrent access with optimistic locking
    - High-performance queries with proper indexing
    - Transaction management for data consistency
    - Advanced search and filtering
    - Batch operations for performance
    - Real-time statistics tracking
    """
    
    def __init__(self):
        self._cache = {}  # Simple in-memory cache for frequent queries
        self._stats_cache_ttl = 300  # 5 minutes cache for stats
        self._last_stats_update = None
    
    @contextmanager
    def _get_session_with_context(self, user_id: str = None, session_id: str = None):
        """Get database session with audit context"""
        with get_db_session() as session:
            # Set audit context for triggers
            if user_id:
                session.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))
            if session_id:
                session.execute(text(f"SET LOCAL app.session_id = '{session_id}'"))
            yield session
    
    def create_requirement(self, requirement_data: Dict[str, Any], user_id: str = None) -> str:
        """
        Create a new requirement with full transaction safety
        
        Args:
            requirement_data: Requirement data dictionary
            user_id: User ID for audit logging
            
        Returns:
            str: Created requirement ID
        """
        try:
            with self._get_session_with_context(user_id=user_id) as session:
                # Create main requirement record
                requirement = Requirement(
                    req_status=requirement_data.get('req_status', 'New'),
                    applied_for=requirement_data.get('applied_for', 'Raju'),
                    next_step=requirement_data.get('next_step', ''),
                    rate=requirement_data.get('rate', ''),
                    tax_type=requirement_data.get('tax_type', 'C2C'),
                    client_company=requirement_data.get('client_company', ''),
                    prime_vendor_company=requirement_data.get('prime_vendor_company', ''),
                    
                    # Vendor details (flattened for performance)
                    vendor_company=requirement_data.get('vendor_details', {}).get('vendor_company', ''),
                    vendor_person_name=requirement_data.get('vendor_details', {}).get('vendor_person_name', ''),
                    vendor_phone_number=requirement_data.get('vendor_details', {}).get('vendor_phone_number', ''),
                    vendor_email=requirement_data.get('vendor_details', {}).get('vendor_email', ''),
                    
                    # Job information
                    requirement_entered_date=datetime.now(),
                    got_requirement_from=requirement_data.get('job_requirement_info', {}).get('got_requirement_from', 'Got from online resume'),
                    job_title=requirement_data.get('job_requirement_info', {}).get('job_title', ''),
                    job_portal_link=requirement_data.get('job_requirement_info', {}).get('job_portal_link', ''),
                    primary_tech_stack=requirement_data.get('job_requirement_info', {}).get('primary_tech_stack', ''),
                    complete_job_description=requirement_data.get('job_requirement_info', {}).get('complete_job_description', ''),
                    
                    # Tech stack as JSONB for high performance queries
                    tech_stack=requirement_data.get('job_requirement_info', {}).get('tech_stack', []),
                    
                    # Interview info
                    interview_id=requirement_data.get('interview_id'),
                    
                    # Legacy compatibility
                    legacy_data={
                        'job_title': requirement_data.get('job_title', ''),
                        'client': requirement_data.get('client', ''),
                        'prime_vendor': requirement_data.get('prime_vendor', ''),
                        'status': requirement_data.get('status', ''),
                        'next_steps': requirement_data.get('next_steps', ''),
                        'vendor_info': requirement_data.get('vendor_info', {})
                    }
                )
                
                session.add(requirement)
                session.flush()  # Get the ID before adding related records
                
                # Add comments if provided
                comments = requirement_data.get('marketing_comments', [])
                if comments:
                    for comment_data in comments:
                        comment = RequirementComment(
                            requirement_id=requirement.id,
                            comment_text=comment_data.get('comment', ''),
                            author=comment_data.get('author', 'System'),
                            comment_type='marketing'
                        )
                        # Set custom timestamp if provided
                        if 'timestamp' in comment_data:
                            try:
                                comment.created_at = datetime.strptime(
                                    comment_data['timestamp'], 
                                    '%Y-%m-%d %H:%M:%S'
                                )
                            except:
                                pass  # Use default timestamp
                        
                        session.add(comment)
                
                # Add consultants if provided
                consultants = requirement_data.get('consultants', [])
                if consultants:
                    for i, consultant_name in enumerate(consultants):
                        if consultant_name.strip():
                            consultant = RequirementConsultant(
                                requirement_id=requirement.id,
                                consultant_name=consultant_name.strip(),
                                priority=i + 1
                            )
                            session.add(consultant)
                
                session.commit()
                
                # Update statistics
                self._update_stats(session, 'requirement_created')
                
                requirement_id = str(requirement.id)
                logger.info(f"✅ Created requirement {requirement_id}")
                
                # Clear cache
                self._clear_cache()
                
                return requirement_id
                
        except IntegrityError as e:
            logger.error(f"❌ Integrity error creating requirement: {e}")
            raise ValueError(f"Data integrity error: {e}")
        except Exception as e:
            logger.error(f"❌ Error creating requirement: {e}")
            raise
    
    def get_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """
        Get requirement by ID with optimized loading
        
        Args:
            requirement_id: Requirement UUID
            
        Returns:
            Dict containing requirement data or None
        """
        try:
            # Check cache first
            cache_key = f"req_{requirement_id}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            with get_db_session() as session:
                # Use optimized query with eager loading
                requirement = session.query(Requirement).options(
                    selectinload(Requirement.comments),
                    selectinload(Requirement.consultants)
                ).filter(
                    and_(
                        Requirement.id == uuid.UUID(requirement_id),
                        Requirement.is_active == True
                    )
                ).first()
                
                if not requirement:
                    return None
                
                # Convert to dictionary with all related data
                result = self._requirement_to_dict(requirement)
                
                # Cache the result
                self._cache[cache_key] = result
                
                return result
                
        except ValueError as e:
            logger.error(f"❌ Invalid requirement ID format: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting requirement {requirement_id}: {e}")
            return None
    
    def update_requirement(self, requirement_id: str, update_data: Dict[str, Any], user_id: str = None) -> bool:
        """
        Update requirement with optimistic locking for concurrent access
        
        Args:
            requirement_id: Requirement UUID
            update_data: Data to update
            user_id: User ID for audit logging
            
        Returns:
            bool: True if update successful
        """
        try:
            with self._get_session_with_context(user_id=user_id) as session:
                # Get requirement with version for optimistic locking
                requirement = session.query(Requirement).filter(
                    and_(
                        Requirement.id == uuid.UUID(requirement_id),
                        Requirement.is_active == True
                    )
                ).with_for_update().first()
                
                if not requirement:
                    logger.warning(f"⚠️ Requirement {requirement_id} not found for update")
                    return False
                
                # Check version for optimistic locking
                current_version = update_data.get('version')
                if current_version and requirement.version != current_version:
                    raise ValueError(f"Concurrent modification detected. Expected version {current_version}, got {requirement.version}")
                
                # Update basic fields
                if 'req_status' in update_data:
                    requirement.req_status = update_data['req_status']
                if 'applied_for' in update_data:
                    requirement.applied_for = update_data['applied_for']
                if 'next_step' in update_data:
                    requirement.next_step = update_data['next_step']
                if 'rate' in update_data:
                    requirement.rate = update_data['rate']
                if 'tax_type' in update_data:
                    requirement.tax_type = update_data['tax_type']
                if 'client_company' in update_data:
                    requirement.client_company = update_data['client_company']
                if 'prime_vendor_company' in update_data:
                    requirement.prime_vendor_company = update_data['prime_vendor_company']
                
                # Update vendor details
                vendor_details = update_data.get('vendor_details', {})
                if vendor_details:
                    requirement.vendor_company = vendor_details.get('vendor_company', requirement.vendor_company)
                    requirement.vendor_person_name = vendor_details.get('vendor_person_name', requirement.vendor_person_name)
                    requirement.vendor_phone_number = vendor_details.get('vendor_phone_number', requirement.vendor_phone_number)
                    requirement.vendor_email = vendor_details.get('vendor_email', requirement.vendor_email)
                
                # Update job info
                job_info = update_data.get('job_requirement_info', {})
                if job_info:
                    if 'got_requirement_from' in job_info:
                        requirement.got_requirement_from = job_info['got_requirement_from']
                    if 'job_title' in job_info:
                        requirement.job_title = job_info['job_title']
                    if 'job_portal_link' in job_info:
                        requirement.job_portal_link = job_info['job_portal_link']
                    if 'primary_tech_stack' in job_info:
                        requirement.primary_tech_stack = job_info['primary_tech_stack']
                    if 'complete_job_description' in job_info:
                        requirement.complete_job_description = job_info['complete_job_description']
                    if 'tech_stack' in job_info:
                        requirement.tech_stack = job_info['tech_stack']
                
                # Update interview ID
                if 'interview_id' in update_data:
                    requirement.interview_id = update_data['interview_id']
                
                # Handle new comments
                new_comments = update_data.get('marketing_comments', [])
                if new_comments:
                    # Only add new comments (not replace all)
                    existing_comment_texts = {c.comment_text for c in requirement.comments}
                    for comment_data in new_comments:
                        comment_text = comment_data.get('comment', '')
                        if comment_text and comment_text not in existing_comment_texts:
                            comment = RequirementComment(
                                requirement_id=requirement.id,
                                comment_text=comment_text,
                                author=comment_data.get('author', 'System'),
                                comment_type='marketing'
                            )
                            session.add(comment)
                
                # Update consultants (replace all)
                consultants = update_data.get('consultants')
                if consultants is not None:
                    # Remove existing consultants
                    session.query(RequirementConsultant).filter(
                        RequirementConsultant.requirement_id == requirement.id
                    ).delete()
                    
                    # Add new consultants
                    for i, consultant_name in enumerate(consultants):
                        if consultant_name.strip():
                            consultant = RequirementConsultant(
                                requirement_id=requirement.id,
                                consultant_name=consultant_name.strip(),
                                priority=i + 1
                            )
                            session.add(consultant)
                
                # Increment version for optimistic locking
                requirement.version += 1
                requirement.updated_at = datetime.now()
                
                session.commit()
                
                logger.info(f"✅ Updated requirement {requirement_id}")
                
                # Clear cache
                self._clear_cache()
                
                return True
                
        except ValueError as e:
            logger.error(f"❌ Validation error updating requirement: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error updating requirement {requirement_id}: {e}")
            return False
    
    def delete_requirement(self, requirement_id: str, user_id: str = None) -> bool:
        """
        Soft delete requirement (mark as inactive)
        
        Args:
            requirement_id: Requirement UUID
            user_id: User ID for audit logging
            
        Returns:
            bool: True if deletion successful
        """
        try:
            with self._get_session_with_context(user_id=user_id) as session:
                requirement = session.query(Requirement).filter(
                    and_(
                        Requirement.id == uuid.UUID(requirement_id),
                        Requirement.is_active == True
                    )
                ).first()
                
                if not requirement:
                    return False
                
                # Soft delete (mark as inactive)
                requirement.is_active = False
                requirement.updated_at = datetime.now()
                
                # Also soft delete related records
                session.query(RequirementComment).filter(
                    RequirementComment.requirement_id == requirement.id
                ).update({'is_active': False})
                
                session.query(RequirementConsultant).filter(
                    RequirementConsultant.requirement_id == requirement.id
                ).update({'is_active': False})
                
                session.commit()
                
                logger.info(f"✅ Deleted requirement {requirement_id}")
                
                # Clear cache
                self._clear_cache()
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error deleting requirement {requirement_id}: {e}")
            return False
    
    def list_requirements(self, 
                         filters: Dict[str, Any] = None, 
                         sort_by: str = 'created_at', 
                         sort_order: str = 'desc',
                         limit: int = None,
                         offset: int = 0) -> List[Dict[str, Any]]:
        """
        List requirements with advanced filtering and pagination
        
        Args:
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of requirement dictionaries
        """
        try:
            with get_db_session() as session:
                # Start with base query
                query = session.query(Requirement).options(
                    selectinload(Requirement.comments),
                    selectinload(Requirement.consultants)
                ).filter(Requirement.is_active == True)
                
                # Apply filters
                if filters:
                    if 'req_status' in filters:
                        query = query.filter(Requirement.req_status == filters['req_status'])
                    
                    if 'applied_for' in filters:
                        query = query.filter(Requirement.applied_for == filters['applied_for'])
                    
                    if 'client_company' in filters:
                        query = query.filter(Requirement.client_company.ilike(f"%{filters['client_company']}%"))
                    
                    if 'job_title' in filters:
                        query = query.filter(Requirement.job_title.ilike(f"%{filters['job_title']}%"))
                    
                    if 'tech_stack' in filters:
                        # JSONB query for tech stack
                        tech_filter = filters['tech_stack']
                        if isinstance(tech_filter, str):
                            query = query.filter(Requirement.tech_stack.contains([tech_filter]))
                        elif isinstance(tech_filter, list):
                            for tech in tech_filter:
                                query = query.filter(Requirement.tech_stack.contains([tech]))
                    
                    if 'date_range' in filters:
                        start_date, end_date = filters['date_range']
                        if start_date:
                            query = query.filter(Requirement.created_at >= start_date)
                        if end_date:
                            query = query.filter(Requirement.created_at <= end_date)
                    
                    if 'search' in filters:
                        search_term = f"%{filters['search']}%"
                        query = query.filter(
                            or_(
                                Requirement.job_title.ilike(search_term),
                                Requirement.client_company.ilike(search_term),
                                Requirement.complete_job_description.ilike(search_term),
                                Requirement.vendor_company.ilike(search_term)
                            )
                        )
                
                # Apply sorting
                if hasattr(Requirement, sort_by):
                    sort_column = getattr(Requirement, sort_by)
                    if sort_order == 'desc':
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))
                else:
                    # Default sort by created_at desc
                    query = query.order_by(desc(Requirement.created_at))
                
                # Apply pagination
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                requirements = query.all()
                
                # Convert to dictionaries
                results = [self._requirement_to_dict(req) for req in requirements]
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error listing requirements: {e}")
            return []
    
    def search_requirements(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Full-text search across requirements
        
        Args:
            search_term: Search term
            limit: Maximum results
            
        Returns:
            List of matching requirements
        """
        try:
            with get_db_session() as session:
                # Use PostgreSQL full-text search
                search_query = text("""
                    SELECT r.id, ts_rank(
                        to_tsvector('english', 
                            COALESCE(r.job_title, '') || ' ' || 
                            COALESCE(r.client_company, '') || ' ' || 
                            COALESCE(r.complete_job_description, '') || ' ' ||
                            COALESCE(r.primary_tech_stack, '')
                        ),
                        plainto_tsquery('english', :search_term)
                    ) as rank
                    FROM requirements r
                    WHERE r.is_active = true
                    AND to_tsvector('english', 
                        COALESCE(r.job_title, '') || ' ' || 
                        COALESCE(r.client_company, '') || ' ' || 
                        COALESCE(r.complete_job_description, '') || ' ' ||
                        COALESCE(r.primary_tech_stack, '')
                    ) @@ plainto_tsquery('english', :search_term)
                    ORDER BY rank DESC, r.created_at DESC
                    LIMIT :limit
                """)
                
                results = session.execute(search_query, {
                    'search_term': search_term,
                    'limit': limit
                }).fetchall()
                
                # Get full requirement data for matching IDs
                requirement_ids = [str(row.id) for row in results]
                if requirement_ids:
                    requirements = session.query(Requirement).options(
                        selectinload(Requirement.comments),
                        selectinload(Requirement.consultants)
                    ).filter(
                        Requirement.id.in_([uuid.UUID(rid) for rid in requirement_ids])
                    ).all()
                    
                    return [self._requirement_to_dict(req) for req in requirements]
                
                return []
                
        except Exception as e:
            logger.error(f"❌ Error searching requirements: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive requirements statistics
        
        Returns:
            Dict containing various statistics
        """
        try:
            # Check cache first
            now = datetime.now()
            if (self._last_stats_update and 
                (now - self._last_stats_update).seconds < self._stats_cache_ttl and
                'stats' in self._cache):
                return self._cache['stats']
            
            with get_db_session() as session:
                # Use materialized view for fast statistics
                stats_query = text("""
                    SELECT 
                        COUNT(*) as total_requirements,
                        COUNT(CASE WHEN req_status = 'New' THEN 1 END) as new_count,
                        COUNT(CASE WHEN req_status = 'Working' THEN 1 END) as working_count,
                        COUNT(CASE WHEN req_status = 'Applied' THEN 1 END) as applied_count,
                        COUNT(CASE WHEN req_status = 'Submitted' THEN 1 END) as submitted_count,
                        COUNT(CASE WHEN req_status = 'Interviewed' THEN 1 END) as interviewed_count,
                        COUNT(CASE WHEN req_status = 'On Hold' THEN 1 END) as on_hold_count,
                        COUNT(CASE WHEN req_status = 'Cancelled' THEN 1 END) as cancelled_count,
                        COUNT(CASE WHEN applied_for = 'Raju' THEN 1 END) as raju_count,
                        COUNT(CASE WHEN applied_for = 'Eric' THEN 1 END) as eric_count,
                        AVG(tech_stack_count) as avg_tech_stack_count,
                        AVG(comment_count) as avg_comment_count,
                        AVG(days_since_created) as avg_days_since_created
                    FROM requirement_summary_view
                """)
                
                result = session.execute(stats_query).fetchone()
                
                # Get top technologies
                tech_query = text("""
                    SELECT 
                        tech.value as technology,
                        COUNT(*) as count
                    FROM requirements r,
                    jsonb_array_elements_text(r.tech_stack) as tech
                    WHERE r.is_active = true
                    GROUP BY tech.value
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                tech_results = session.execute(tech_query).fetchall()
                
                # Get top clients
                client_query = text("""
                    SELECT 
                        client_company,
                        COUNT(*) as count
                    FROM requirements
                    WHERE is_active = true AND client_company IS NOT NULL
                    GROUP BY client_company
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                client_results = session.execute(client_query).fetchall()
                
                # Compile statistics
                stats = {
                    'total_requirements': result.total_requirements or 0,
                    'by_status': {
                        'New': result.new_count or 0,
                        'Working': result.working_count or 0,
                        'Applied': result.applied_count or 0,
                        'Submitted': result.submitted_count or 0,
                        'Interviewed': result.interviewed_count or 0,
                        'On Hold': result.on_hold_count or 0,
                        'Cancelled': result.cancelled_count or 0
                    },
                    'by_consultant': {
                        'Raju': result.raju_count or 0,
                        'Eric': result.eric_count or 0
                    },
                    'averages': {
                        'tech_stack_count': float(result.avg_tech_stack_count or 0),
                        'comment_count': float(result.avg_comment_count or 0),
                        'days_since_created': float(result.avg_days_since_created or 0)
                    },
                    'top_technologies': {row.technology: row.count for row in tech_results},
                    'top_clients': {row.client_company: row.count for row in client_results},
                    'last_updated': now.isoformat()
                }
                
                # Cache the results
                self._cache['stats'] = stats
                self._last_stats_update = now
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {}
    
    def _requirement_to_dict(self, requirement: Requirement) -> Dict[str, Any]:
        """Convert Requirement model to dictionary with legacy compatibility"""
        
        # Get comments sorted by date
        comments = sorted(requirement.comments, key=lambda c: c.created_at, reverse=True)
        marketing_comments = [
            {
                'comment': comment.comment_text,
                'timestamp': comment.created_at.strftime('%Y-%m-%d %H:%M:%S') if comment.created_at else None,
                'author': comment.author
            }
            for comment in comments if comment.is_active
        ]
        
        # Get consultants sorted by priority
        consultants = sorted([c for c in requirement.consultants if c.is_active], key=lambda c: c.priority)
        consultant_names = [c.consultant_name for c in consultants]
        
        return {
            'id': str(requirement.id),
            'req_status': requirement.req_status,
            'applied_for': requirement.applied_for,
            'next_step': requirement.next_step,
            'rate': requirement.rate,
            'tax_type': requirement.tax_type,
            'marketing_comments': marketing_comments,
            'client_company': requirement.client_company,
            'prime_vendor_company': requirement.prime_vendor_company,
            'vendor_details': {
                'vendor_company': requirement.vendor_company,
                'vendor_person_name': requirement.vendor_person_name,
                'vendor_phone_number': requirement.vendor_phone_number,
                'vendor_email': requirement.vendor_email
            },
            'job_requirement_info': {
                'requirement_entered_date': requirement.requirement_entered_date.isoformat() if requirement.requirement_entered_date else None,
                'got_requirement_from': requirement.got_requirement_from,
                'tech_stack': requirement.tech_stack or [],
                'job_title': requirement.job_title,
                'job_portal_link': requirement.job_portal_link,
                'primary_tech_stack': requirement.primary_tech_stack,
                'complete_job_description': requirement.complete_job_description
            },
            'consultants': consultant_names,
            'interview_id': requirement.interview_id,
            'created_at': requirement.created_at.isoformat() if requirement.created_at else None,
            'updated_at': requirement.updated_at.isoformat() if requirement.updated_at else None,
            'version': requirement.version,
            
            # Legacy compatibility fields
            'job_title': requirement.job_title,
            'client': requirement.client_company,
            'prime_vendor': requirement.prime_vendor_company,
            'status': requirement.req_status,
            'next_steps': requirement.next_step,
            'vendor_info': {
                'name': requirement.vendor_person_name,
                'company': requirement.vendor_company,
                'phone': requirement.vendor_phone_number,
                'email': requirement.vendor_email
            }
        }
    
    def _update_stats(self, session, operation: str):
        """Update database statistics"""
        try:
            # Update total count
            if operation == 'requirement_created':
                total_stat = session.query(DatabaseStats).filter_by(
                    stat_name='total_requirements'
                ).first()
                
                if total_stat:
                    current_count = total_stat.stat_value.get('count', 0)
                    total_stat.stat_value = {
                        'count': current_count + 1,
                        'last_updated': datetime.now().isoformat()
                    }
                    session.add(total_stat)
                    
        except Exception as e:
            logger.warning(f"⚠️ Failed to update stats: {e}")
    
    def _clear_cache(self):
        """Clear internal cache"""
        self._cache.clear()
        self._last_stats_update = None
    
    def batch_create_requirements(self, requirements_data: List[Dict[str, Any]], user_id: str = None) -> List[str]:
        """
        Batch create multiple requirements for high performance
        
        Args:
            requirements_data: List of requirement data dictionaries
            user_id: User ID for audit logging
            
        Returns:
            List of created requirement IDs
        """
        created_ids = []
        
        try:
            with self._get_session_with_context(user_id=user_id) as session:
                for req_data in requirements_data:
                    try:
                        # Use individual create method for consistency
                        req_id = self.create_requirement(req_data, user_id)
                        created_ids.append(req_id)
                    except Exception as e:
                        logger.error(f"❌ Failed to create requirement in batch: {e}")
                        continue
                
                logger.info(f"✅ Batch created {len(created_ids)} requirements")
                
        except Exception as e:
            logger.error(f"❌ Batch create failed: {e}")
        
        return created_ids
    
    def export_requirements(self, filters: Dict[str, Any] = None) -> str:
        """
        Export requirements as JSON with filtering support
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            JSON string of requirements data
        """
        try:
            requirements = self.list_requirements(filters=filters)
            
            export_data = {
                'requirements': {req['id']: req for req in requirements},
                'exported_at': datetime.now().isoformat(),
                'version': '2.0',
                'total_count': len(requirements)
            }
            
            import json
            return json.dumps(export_data, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return ""
    
    def get_database_health(self) -> Dict[str, Any]:
        """Get database health status"""
        return db_manager.health_check()

# Create alias for backward compatibility
RequirementsManager = PostgreSQLRequirementsManager



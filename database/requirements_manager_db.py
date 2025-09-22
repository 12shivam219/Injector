from typing import Dict, Any, List, Optional
from .connection import DatabaseConnectionManager
from .models import Requirement
import logging

logger = logging.getLogger(__name__)


class PostgreSQLRequirementsManager:
    """Lightweight PostgreSQL-backed requirements manager."""

    def __init__(self):
        self.conn = DatabaseConnectionManager()
        initialized = self.conn.initialize()
        if not initialized:
            raise RuntimeError("Failed to initialize database connection for RequirementsManager")
        # Ensure schema exists (creates tables if missing)
        try:
            self.conn.initialize_schema()
        except Exception:
            # Non-fatal: schema initialization may be handled by migrations
            pass

    def create_requirement(self, data: Dict[str, Any]) -> str:
        try:
            with self.conn.get_session(auto_commit=True) as session:
                req = Requirement()
                # Map and validate required fields with sensible defaults to satisfy DB constraints
                req.client_company = (data.get('client_company') or data.get('client') or 'Unknown Client')[:255]
                job_info = data.get('job_requirement_info', {})
                req.job_title = (job_info.get('job_title') or data.get('job_title') or 'Untitled Job')[:255]

                # Validate request status
                allowed_status = ['New', 'Working', 'Applied', 'Cancelled', 'Submitted', 'Interviewed', 'On Hold']
                incoming_status = (data.get('req_status') or job_info.get('req_status'))
                req.req_status = incoming_status if incoming_status in allowed_status else 'New'

                # Defaults for small required enums/fields
                req.applied_for = (data.get('applied_for') or 'Raju')[:100]
                req.tax_type = (data.get('tax_type') or 'C2C')[:50]

                # Vendor details (truncate to column sizes)
                v = data.get('vendor_details', {})
                req.vendor_company = (v.get('vendor_company') or '')[:255]
                req.vendor_person_name = (v.get('vendor_person_name') or '')[:255]
                req.vendor_phone_number = (v.get('vendor_phone_number') or '')[:50]
                req.vendor_email = (v.get('vendor_email') or '')[:255]

                # Tech stack and descriptions
                req.tech_stack = job_info.get('tech_stack', []) or []
                req.complete_job_description = job_info.get('complete_job_description', '')

                # Ensure required booleans / flags have defaults
                if not getattr(req, 'is_active', None):
                    req.is_active = True
                # Version default
                if not getattr(req, 'version', None):
                    req.version = 1

                # Priority and application status defaults
                req.priority_score = int(data.get('priority_score') or 5)
                req.application_status = data.get('application_status') or 'Not Applied'
                session.add(req)
                session.flush()
                rid = str(req.id)
                return rid
        except Exception as e:
            logger.error(f"Failed to create requirement in DB: {e}")
            raise

    def get_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self.conn.get_session() as session:
                req = session.get(Requirement, requirement_id)
                if not req:
                    return None
                return req.to_dict()
        except Exception as e:
            logger.error(f"Failed to get requirement {requirement_id}: {e}")
            return None

    def update_requirement(self, requirement_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            with self.conn.get_session(auto_commit=True) as session:
                req = session.get(Requirement, requirement_id)
                if not req:
                    return False
                # Update allowed fields
                if 'client_company' in update_data:
                    req.client_company = update_data['client_company']
                job_info = update_data.get('job_requirement_info', {})
                if job_info.get('job_title'):
                    req.job_title = job_info['job_title']
                session.add(req)
                return True
        except Exception as e:
            logger.error(f"Failed to update requirement {requirement_id}: {e}")
            return False

    def delete_requirement(self, requirement_id: str) -> bool:
        try:
            with self.conn.get_session(auto_commit=True) as session:
                req = session.get(Requirement, requirement_id)
                if not req:
                    return False
                session.delete(req)
                return True
        except Exception as e:
            logger.error(f"Failed to delete requirement {requirement_id}: {e}")
            return False

    def list_requirements(self) -> List[Dict[str, Any]]:
        try:
            with self.conn.get_session() as session:
                rows = session.query(Requirement).order_by(Requirement.created_at.desc()).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            logger.error(f"Failed to list requirements: {e}")
            return []


__all__ = ['PostgreSQLRequirementsManager']

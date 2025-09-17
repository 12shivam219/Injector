"""
Audit Logger Module for Resume Customizer Application.
Provides comprehensive audit logging for security and compliance tracking.
"""

import json
import datetime
from typing import Dict, Any, Optional
from infrastructure.utilities.logger import get_logger

logger = get_logger()


class AuditLogger:
    """Centralized audit logging for security and compliance tracking."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def log(self, action: str, user: str, details: Optional[Dict[str, Any]] = None, 
            status: str = "success", error: Optional[str] = None):
        """
        Log an audit event.
        
        Args:
            action: The action being performed
            user: User identifier
            details: Additional details about the action
            status: Status of the action (success, failure, etc.)
            error: Error message if applicable
        """
        try:
            audit_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "action": action,
                "user": user,
                "status": status,
                "details": details or {},
            }
            
            if error:
                audit_entry["error"] = error
                audit_entry["status"] = "failure"
            
            # Log as structured JSON for easy parsing
            self.logger.info(f"AUDIT: {json.dumps(audit_entry)}")
            
        except Exception as e:
            # Fallback logging if audit logging fails
            logger.error(f"Audit logging failed: {str(e)}")
            logger.info(f"AUDIT_FALLBACK: action={action}, user={user}, status={status}")
    
    def log_security_event(self, event_type: str, user: str, details: Dict[str, Any]):
        """
        Log a security-related event.
        
        Args:
            event_type: Type of security event
            user: User identifier
            details: Event details
        """
        self.log(
            action=f"security_{event_type}",
            user=user,
            details=details
        )
    
    def log_file_operation(self, operation: str, user: str, filename: str, 
                          success: bool = True, error: Optional[str] = None):
        """
        Log file operations for audit trail.
        
        Args:
            operation: Type of file operation
            user: User identifier
            filename: Name of the file
            success: Whether operation was successful
            error: Error message if failed
        """
        self.log(
            action=f"file_{operation}",
            user=user,
            details={"filename": filename},
            status="success" if success else "failure",
            error=error
        )
    
    def log_email_operation(self, operation: str, user: str, recipient: str,
                           success: bool = True, error: Optional[str] = None):
        """
        Log email operations for audit trail.
        
        Args:
            operation: Type of email operation
            user: User identifier
            recipient: Email recipient
            success: Whether operation was successful
            error: Error message if failed
        """
        self.log(
            action=f"email_{operation}",
            user=user,
            details={"recipient": recipient},
            status="success" if success else "failure",
            error=error
        )


# Global audit logger instance
audit_logger = AuditLogger()

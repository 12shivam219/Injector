"""
Enhanced error handling system for Resume Customizer application.
Provides structured error responses, user-friendly messages, and detailed logging.
"""

import traceback
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Type, List
from dataclasses import dataclass, field
from enum import Enum
import streamlit as st

from infrastructure.utilities.logger import get_logger
from audit_logger import audit_logger
from contextlib import contextmanager
import json

logger = get_logger()

# Try to use structlog for better structured logging
try:
    import structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structured_logger = structlog.get_logger()
    STRUCTLOG_AVAILABLE = True
except ImportError:
    # Fallback to regular logger if structlog is not available
    structured_logger = logger
    STRUCTLOG_AVAILABLE = False


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    file_name: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredError:
    """Structured error with comprehensive information."""
    error_id: str
    error_type: str
    message: str
    user_message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: ErrorContext
    traceback_info: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)


class ErrorMessageGenerator:
    """Generate user-friendly error messages."""
    
    ERROR_MESSAGES = {
        # File processing errors
        "FileNotFoundError": "The file you're trying to process could not be found. Please check the file and try uploading again.",
        "PermissionError": "We don't have permission to access this file. Please check the file permissions or try a different file.",
        "FileProcessingError": "There was an issue processing your file. Please ensure it's a valid Word document (.docx) and try again.",
        
        # Network/Email errors
        "ConnectionError": "We're having trouble connecting to the email server. Please check your internet connection and try again.",
        "SMTPAuthenticationError": "Email authentication failed. Please verify your email address and password (use app-specific password for Gmail).",
        "SMTPServerDisconnected": "Lost connection to the email server. Please try again in a moment.",
        
        # Processing errors
        "ValidationError": "The input data doesn't meet our requirements. Please check your entries and try again.",
        "ProcessingTimeoutError": "The operation took too long to complete. Please try with fewer files or smaller documents.",
        "MemoryError": "The system is running low on memory. Please try processing fewer files at once or restart the application.",
        
        # Generic errors
        "UnexpectedError": "Something unexpected happened. Our team has been notified and will investigate the issue."
    }
    
    SUGGESTED_ACTIONS = {
        "FileNotFoundError": [
            "Re-upload the file",
            "Check if the file was moved or deleted",
            "Try a different file"
        ],
        "PermissionError": [
            "Close the file in other applications",
            "Save the file to a different location",
            "Check file permissions"
        ],
        "SMTPAuthenticationError": [
            "Verify your email address is correct",
            "Use an app-specific password for Gmail/Office365",
            "Check if 2-factor authentication is enabled",
            "Try a different email account"
        ],
        "ConnectionError": [
            "Check your internet connection",
            "Try again in a few minutes",
            "Use a different network if possible"
        ],
        "MemoryError": [
            "Process fewer files at once",
            "Restart the application",
            "Close other browser tabs",
            "Try smaller document files"
        ]
    }
    
    @classmethod
    def get_user_message(cls, error_type: str, original_message: str = "") -> str:
        """Get user-friendly error message."""
        base_message = cls.ERROR_MESSAGES.get(error_type, cls.ERROR_MESSAGES["UnexpectedError"])
        
        # Add specific details if available
        if original_message and error_type not in ["UnexpectedError"]:
            base_message += f" Technical details: {original_message}"
        
        return base_message
    
    @classmethod
    def get_suggested_actions(cls, error_type: str) -> List[str]:
        """Get suggested actions for error type."""
        return cls.SUGGESTED_ACTIONS.get(error_type, [
            "Refresh the page and try again",
            "Contact support if the problem persists"
        ])


class ErrorHandler:
    """Central error handler for the application."""
    
    def __init__(self):
        self.message_generator = ErrorMessageGenerator()
    
    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        show_to_user: bool = True,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> StructuredError:
        """Handle an error with comprehensive logging and user feedback."""
        
        # Generate unique error ID
        error_id = str(uuid.uuid4())[:8]
        
        # Determine error type
        error_type = type(exception).__name__
        
        # Get user-friendly message
        user_message = self.message_generator.get_user_message(error_type, str(exception))
        suggested_actions = self.message_generator.get_suggested_actions(error_type)
        
        # Create structured error
        structured_error = StructuredError(
            error_id=error_id,
            error_type=error_type,
            message=str(exception),
            user_message=user_message,
            severity=severity,
            timestamp=datetime.now(),
            context=context,
            traceback_info=traceback.format_exc(),
            suggested_actions=suggested_actions
        )
        
        # Log error with appropriate level
        self._log_error(structured_error)
        
        # Show to user if requested
        if show_to_user:
            self._display_error_to_user(structured_error)
        
        # Audit log for security-related errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            audit_logger.log(
                action="error_occurred",
                user=context.user_id,
                details={
                    "error_id": error_id,
                    "error_type": error_type,
                    "operation": context.operation,
                    "severity": severity.value
                },
                status="error"
            )
        
        return structured_error
    
    def _log_error(self, error: StructuredError):
        """Log error with appropriate level based on severity."""
        log_message = (
            f"[{error.error_id}] {error.error_type} in {error.context.operation}: {error.message}"
        )
        
        if error.severity == ErrorSeverity.LOW:
            logger.info(log_message, error_id=error.error_id)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, error_id=error.error_id)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, error_id=error.error_id, exception=Exception(error.message))
        else:  # CRITICAL
            logger.critical(log_message, error_id=error.error_id, exception=Exception(error.message))
    
    def _display_error_to_user(self, error: StructuredError):
        """Display error to user with contextual information."""
        try:
            # Create contextual error message
            contextual_message = self._create_contextual_error_message(error)
            
            if error.severity == ErrorSeverity.LOW:
                st.info(f"ℹ️ {contextual_message}")
            elif error.severity == ErrorSeverity.MEDIUM:
                st.warning(f"⚠️ {contextual_message}")
            else:  # HIGH or CRITICAL
                st.error(f"🚨 {contextual_message}")
            
            # Show suggested actions in expandable section
            if error.suggested_actions:
                with st.expander("💡 Suggested Solutions", expanded=False):
                    for i, action in enumerate(error.suggested_actions, 1):
                        st.write(f"{i}. {action}")
            
            # Show error ID for critical errors
            if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                st.caption(f"Error ID: {error.error_id} (Please provide this ID when contacting support)")
        
        except Exception as e:
            logger.error(f"Failed to display error to user: {e}")
    
    def _create_contextual_error_message(self, error: StructuredError) -> str:
        """Create contextual error message with helpful information."""
        base_message = error.user_message
        
        # Add context based on operation
        if error.context.operation:
            if "upload" in error.context.operation.lower():
                base_message += " Please ensure your file is a valid Word document (.docx) and try again."
            elif "email" in error.context.operation.lower():
                base_message += " Please check your email settings and internet connection."
            elif "process" in error.context.operation.lower():
                base_message += " Please try with a different file or contact support if the issue persists."
        
        # Add file context if available
        if error.context.file_name:
            base_message += f" (File: {error.context.file_name})"
        
        return base_message


@contextmanager
def error_context(operation: str, **context):
    """Standardized error context for consistent logging and handling."""
    error_id = str(uuid.uuid4())[:8]
    
    # Start operation logging
    structured_logger.info(
        "Starting operation", 
        operation=operation, 
        error_id=error_id,
        **context
    )
    
    try:
        yield error_id
        # Success logging
        structured_logger.info(
            "Operation completed successfully", 
            operation=operation, 
            error_id=error_id,
            **context
        )
    except Exception as e:
        # Error logging with structured data
        structured_logger.error(
            "Operation failed", 
            operation=operation,
            error_id=error_id,
            error=str(e),
            error_type=type(e).__name__,
            **context
        )
        
        # Handle the error using existing error handler
        error_handler = ErrorHandler()
        error_context_obj = ErrorContext(
            user_id=context.get('user_id', st.session_state.get('user_id', 'anonymous')),
            session_id=context.get('session_id', st.session_state.get('session_id')),
            operation=operation,
            file_name=context.get('file_name'),
            additional_data=context
        )
        
        severity = ErrorSeverity.MEDIUM
        if 'severity' in context:
            severity = context['severity']
        
        error_handler.handle_error(e, error_context_obj, show_to_user=True, severity=severity)
        raise


class PerformanceTimer:
    """Context manager for timing operations and logging performance metrics."""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            # Log performance metrics
            structured_logger.info(
                "Operation performance",
                operation=self.operation,
                duration_seconds=duration,
                success=exc_type is None,
                **self.context
            )
            
            # Store performance data in session state for monitoring
            if 'performance_metrics' not in st.session_state:
                st.session_state.performance_metrics = []
            
            st.session_state.performance_metrics.append({
                'operation': self.operation,
                'duration': duration,
                'timestamp': time.time(),
                'success': exc_type is None
            })
            
            # Keep only last 100 metrics
            if len(st.session_state.performance_metrics) > 100:
                st.session_state.performance_metrics = st.session_state.performance_metrics[-100:]




# Decorator for automatic error handling
def handle_errors(
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    show_to_user: bool = True,
    return_on_error: Any = None
):
    """Decorator for automatic error handling."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            
            context = ErrorContext(
                user_id=st.session_state.get('user_id', 'anonymous'),
                session_id=st.session_state.get('session_id'),
                operation=operation,
                additional_data={"function": func.__name__}
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context, show_to_user, severity)
                return return_on_error
        
        return wrapper
    return decorator


# Context manager for operation-specific error handling
class ErrorHandlerContext:
    """Context manager for handling errors in specific operations."""
    
    def __init__(
        self,
        operation: str,
        file_name: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        show_to_user: bool = True
    ):
        self.operation = operation
        self.file_name = file_name
        self.severity = severity
        self.show_to_user = show_to_user
        self.error_handler = ErrorHandler()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            context = ErrorContext(
                user_id=st.session_state.get('user_id', 'anonymous'),
                session_id=st.session_state.get('session_id'),
                operation=self.operation,
                file_name=self.file_name
            )
            
            self.error_handler.handle_error(
                exc_val, context, self.show_to_user, self.severity
            )
            
            # Suppress the exception (return True)
            return True
        return False


# Usage examples and utility functions:

def get_error_summary() -> Dict[str, Any]:
    """Get summary of errors from session state."""
    if 'error_history' not in st.session_state:
        st.session_state.error_history = []
    
    recent_errors = [e for e in st.session_state.error_history 
                    if (datetime.now() - e.get('timestamp', datetime.now())).seconds < 3600]
    
    return {
        'total_errors': len(st.session_state.error_history),
        'recent_errors': len(recent_errors),
        'error_types': list(set(e.get('error_type', 'Unknown') for e in recent_errors))
    }


def clear_error_history():
    """Clear error history from session state."""
    if 'error_history' in st.session_state:
        st.session_state.error_history = []


@handle_errors("file_processing", ErrorSeverity.HIGH, show_to_user=True, return_on_error=None)
def process_resume_with_error_handling(file_obj, tech_stacks):
    """Example function with automatic error handling."""
    # Your processing logic here
    pass


def example_context_usage():
    """Example of using the error handler context manager."""
    with ErrorHandlerContext("email_sending", "resume.docx", ErrorSeverity.HIGH):
        # Email sending logic here
        # Any exceptions will be handled automatically
        pass


def example_new_context_usage():
    """Example of using the new error context manager."""
    with error_context("document_processing", file_name="resume.docx", user_id="user123"):
        # Document processing logic here
        # Automatic logging and error handling
        pass


def example_performance_timing():
    """Example of using performance timer."""
    with PerformanceTimer("bulk_processing", file_count=5):
        # Bulk processing logic here
        # Performance metrics will be automatically collected
        pass




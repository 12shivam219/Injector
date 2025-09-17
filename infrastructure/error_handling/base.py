"""
Base error handling functionality for Resume Customizer application.
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
from infrastructure.utilities.structured_logger import get_structured_logger

logger = get_logger()
structured_logger = get_structured_logger("error_handler")


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Minor issues, can continue
    MEDIUM = "medium"     # Significant issues, may need attention
    HIGH = "high"         # Critical issues, needs immediate attention
    FATAL = "fatal"       # System cannot continue


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None


class ErrorHandler:
    """Main error handling class."""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self._setup_logging()

    @staticmethod
    def with_error_handling(operation_name: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                          show_to_user: bool = True, component: Optional[str] = None):
        """
        Decorator for handling errors in methods.
        
        Args:
            operation_name (str): Name of the operation being performed
            severity (ErrorSeverity): Severity level of potential errors
            show_to_user (bool): Whether to show errors to the user
            component (str, optional): Component where the operation is performed
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_context = ErrorContext(
                        severity=severity,
                        component=component or func.__module__,
                        operation=operation_name,
                        stack_trace=traceback.format_exc(),
                        details={
                            'function': func.__name__,
                            'args': str(args),
                            'kwargs': str(kwargs),
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    )
                    
                    # Log the error
                    structured_logger.error(
                        f"Error in {operation_name}",
                        extra={
                            'error_id': error_context.error_id,
                            'severity': severity.value,
                            'component': error_context.component,
                            'operation': operation_name,
                            'error_details': error_context.details
                        }
                    )
                    
                    # Show error to user if requested
                    if show_to_user and hasattr(st, 'error'):
                        st.error(f"❌ Error in {operation_name}: {str(e)}")
                        
                        # For high severity errors, show more details
                        if severity in [ErrorSeverity.HIGH, ErrorSeverity.FATAL]:
                            with st.expander("📝 Error Details"):
                                st.code(error_context.stack_trace)
                    
                    # Re-raise the exception if it's a fatal error
                    if severity == ErrorSeverity.FATAL:
                        raise
                    
                    return None
            return wrapper
        return decorator
    def _setup_logging(self):
        """Configure structured logging."""
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
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        except ImportError:
            logger.warning("structlog not available, falling back to standard logging")

    def handle_error(self, error: Exception, context: Optional[ErrorContext] = None) -> ErrorContext:
        """Handle an error with optional context."""
        if context is None:
            context = ErrorContext()
        
        context.stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        self.error_history.append(context)
        self._log_error(error, context)
        
        return context

    def _log_error(self, error: Exception, context: ErrorContext):
        """Log error with structured data."""
        log_data = {
            "error_id": context.error_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": context.severity.value,
            "timestamp": context.timestamp.isoformat(),
            "user_id": context.user_id,
            "session_id": context.session_id,
            "component": context.component,
            "operation": context.operation,
            "details": context.details
        }
        
        if context.severity in (ErrorSeverity.HIGH, ErrorSeverity.FATAL):
            log_data["stack_trace"] = context.stack_trace
            structured_logger.error("Critical error occurred", **log_data)
        else:
            structured_logger.warning("Error occurred", **log_data)


# Global error handler instance
_error_handler = ErrorHandler()

# Convenience functions
def handle_error(error: Exception, context: Optional[ErrorContext] = None) -> ErrorContext:
    """Global function to handle errors."""
    return _error_handler.handle_error(error, context)

def log_error(message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, **kwargs):
    """Log an error message with context."""
    context = ErrorContext(severity=severity, details=kwargs)
    error = Exception(message)
    return handle_error(error, context)

def format_error(error: Exception) -> str:
    """Format an error for display."""
    if isinstance(error, Exception):
        return f"{type(error).__name__}: {str(error)}"
    return str(error)
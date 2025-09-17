"""
Enhanced structured logging system for Resume Customizer application.
Provides correlation IDs, structured logging, and performance tracking.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from functools import wraps
import streamlit as st

from .logger import get_logger

# Base logger
base_logger = get_logger()


class CorrelationContext:
    """Manages correlation IDs for tracking requests across components."""
    
    def __init__(self):
        self._context = {}
    
    def get_correlation_id(self) -> str:
        """Get or create correlation ID for current context."""
        if 'correlation_id' not in st.session_state:
            st.session_state.correlation_id = str(uuid.uuid4())
        return st.session_state.correlation_id
    
    def get_session_id(self) -> str:
        """Get session ID for current user session."""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        return st.session_state.session_id
    
    def get_user_id(self) -> str:
        """Get user ID for current user."""
        return st.session_state.get('user_id', 'anonymous')


class StructuredLogger:
    """Enhanced logger with structured logging and correlation."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.correlation = CorrelationContext()
        self.base_logger = base_logger
    
    def _create_log_entry(
        self, 
        level: str, 
        message: str, 
        operation: Optional[str] = None,
        duration: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create structured log entry."""
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'component': self.component_name,
            'correlation_id': self.correlation.get_correlation_id(),
            'session_id': self.correlation.get_session_id(),
            'user_id': self.correlation.get_user_id(),
            'message': message,
        }
        
        if operation:
            entry['operation'] = operation
        
        if duration is not None:
            entry['duration_ms'] = round(duration * 1000, 2)
        
        # Add any additional fields
        entry.update(kwargs)
        
        return entry
    
    def debug(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log debug message with structured data."""
        entry = self._create_log_entry('DEBUG', message, operation, **kwargs)
        self.base_logger.debug(json.dumps(entry))
    
    def info(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log info message with structured data."""
        entry = self._create_log_entry('INFO', message, operation, **kwargs)
        self.base_logger.info(json.dumps(entry))
    
    def warning(self, message: str, operation: Optional[str] = None, **kwargs):
        """Log warning message with structured data."""
        entry = self._create_log_entry('WARNING', message, operation, **kwargs)
        self.base_logger.warning(json.dumps(entry))
    
    def error(
        self, 
        message: str, 
        operation: Optional[str] = None, 
        exception: Optional[Exception] = None,
        **kwargs
    ):
        """Log error message with structured data and exception details."""
        entry = self._create_log_entry('ERROR', message, operation, **kwargs)
        
        if exception:
            entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': self._get_exception_traceback(exception)
            }
        
        self.base_logger.error(json.dumps(entry))
    
    def critical(
        self, 
        message: str, 
        operation: Optional[str] = None, 
        exception: Optional[Exception] = None,
        **kwargs
    ):
        """Log critical message with structured data."""
        entry = self._create_log_entry('CRITICAL', message, operation, **kwargs)
        
        if exception:
            entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': self._get_exception_traceback(exception)
            }
        
        self.base_logger.critical(json.dumps(entry))
    
    def performance(
        self, 
        operation: str, 
        duration: float, 
        success: bool = True,
        **metrics
    ):
        """Log performance metrics."""
        entry = self._create_log_entry(
            'INFO', 
            f"Performance: {operation}",
            operation=operation,
            duration=duration,
            success=success,
            **metrics
        )
        self.base_logger.info(json.dumps(entry))
    
    def user_action(
        self, 
        action: str, 
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log user actions for analytics and audit."""
        entry = self._create_log_entry(
            'INFO',
            f"User action: {action}",
            operation='user_action',
            action=action,
            details=details or {},
            **kwargs
        )
        self.base_logger.info(json.dumps(entry))
    
    def _get_exception_traceback(self, exception: Exception) -> str:
        """Get formatted exception traceback."""
        import traceback
        return ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))
    
    @contextmanager
    def operation_context(self, operation: str, **context_data):
        """Context manager for tracking operations."""
        start_time = time.time()
        operation_id = str(uuid.uuid4())[:8]
        
        # Log operation start
        self.info(
            f"Starting operation: {operation}",
            operation=operation,
            operation_id=operation_id,
            **context_data
        )
        
        try:
            yield operation_id
            # Log success
            duration = time.time() - start_time
            self.performance(
                operation,
                duration,
                success=True,
                operation_id=operation_id,
                **context_data
            )
        except Exception as e:
            # Log failure
            duration = time.time() - start_time
            self.error(
                f"Operation failed: {operation}",
                operation=operation,
                exception=e,
                operation_id=operation_id,
                duration=duration,
                **context_data
            )
            raise


class LoggingManager:
    """Manages loggers for different components."""
    
    _loggers: Dict[str, StructuredLogger] = {}
    
    @classmethod
    def get_logger(cls, component_name: str) -> StructuredLogger:
        """Get or create logger for component."""
        if component_name not in cls._loggers:
            cls._loggers[component_name] = StructuredLogger(component_name)
        return cls._loggers[component_name]
    
    @classmethod
    def get_all_loggers(cls) -> Dict[str, StructuredLogger]:
        """Get all registered loggers."""
        return cls._loggers.copy()


def with_structured_logging(component_name: str, operation: str = None):
    """Decorator to add structured logging to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = LoggingManager.get_logger(component_name)
            op_name = operation or func.__name__
            
            with logger.operation_context(op_name, function=func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_performance(component_name: str, operation: str = None):
    """Decorator for performance logging."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = LoggingManager.get_logger(component_name)
            op_name = operation or func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.performance(op_name, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.performance(op_name, duration, success=False)
                logger.error(f"Performance logged failure in {op_name}", exception=e)
                raise
        
        return wrapper
    return decorator


class LogAnalytics:
    """Analytics for log data."""
    
    def __init__(self):
        self.correlation = CorrelationContext()
    
    def get_session_logs(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logs for current or specified session."""
        target_session = session_id or self.correlation.get_session_id()
        
        # In a real implementation, this would query a log store
        # For now, we'll return a placeholder
        return []
    
    def get_operation_timeline(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get timeline of operations for a correlation ID."""
        # Placeholder for operation timeline
        return []
    
    def get_performance_metrics(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics summary."""
        # Placeholder for performance metrics
        return {
            'component': component,
            'total_operations': 0,
            'avg_duration_ms': 0,
            'success_rate': 100.0
        }


# Convenience functions for getting loggers
def get_structured_logger(component_name: str) -> StructuredLogger:
    """Get structured logger for component."""
    return LoggingManager.get_logger(component_name)

# Create a default processing logger instance
processing_logger = get_structured_logger("processing")

# Create app logger instance
app_logger = get_structured_logger("app")

# Log analytics instance
log_analytics = LogAnalytics()

# Backward compatibility
__all__ = ['StructuredLogger', 'get_structured_logger', 'processing_logger', 'app_logger', 'with_structured_logging', 'log_performance']




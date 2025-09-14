"""
Error handling package for Resume Customizer application.
Provides comprehensive error handling, recovery, and logging functionality.
"""

from .base import (
    ErrorHandler,
    ErrorContext,
    ErrorSeverity,
    handle_error,
    log_error,
    format_error
)

from .recovery import (
    RecoveryStrategy,
    RetryConfig,
    ErrorRecoveryManager,
    with_error_recovery,
    get_error_recovery_manager
)

__all__ = [
    'ErrorHandler',
    'ErrorContext',
    'ErrorSeverity',
    'handle_error',
    'log_error',
    'format_error',
    'RecoveryStrategy',
    'RetryConfig',
    'ErrorRecoveryManager',
    'with_error_recovery',
    'get_error_recovery_manager'
]
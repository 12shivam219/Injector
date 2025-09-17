"""
DEPRECATED: Structured logger - use infrastructure.utilities.structured_logger instead.
This module provides backward compatibility shims.
"""
import warnings
from infrastructure.utilities.structured_logger import (
    StructuredLogger as InfraStructuredLogger,
    get_structured_logger as get_infra_structured_logger,
    with_structured_logging,
    log_performance,
    LoggingManager,
    LogAnalytics
)

# Issue deprecation warning
warnings.warn(
    "utilities.structured_logger is deprecated. Use infrastructure.utilities.structured_logger instead.",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility wrapper for old StructuredLogger interface
class StructuredLogger:
    """Backward compatibility wrapper for infrastructure StructuredLogger."""
    
    def __init__(self, name=None):
        self._logger = get_infra_structured_logger(name or "legacy")
    
    def log_structured(self, level, message, **kwargs):
        """Log a structured message."""
        getattr(self._logger, level.lower())(message, **kwargs)
    
    def info(self, message, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def error(self, message, **kwargs):
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def warning(self, message, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def debug(self, message, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)

def get_structured_logger(name=None):
    """Get a structured logger instance."""
    return StructuredLogger(name)

# Create a default processing logger instance
processing_logger = get_structured_logger("processing")

# Backward compatibility exports
__all__ = ['StructuredLogger', 'get_structured_logger', 'processing_logger', 'with_structured_logging', 'log_performance']
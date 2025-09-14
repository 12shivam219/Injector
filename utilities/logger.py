"""
DEPRECATED: Logger utilities - use infrastructure.utilities.logger instead.
This module provides backward compatibility shims.
"""
import warnings
from infrastructure.utilities.logger import (
    ApplicationLogger,
    get_logger as get_infrastructure_logger,
    log_function_call,
    display_logs_in_sidebar
)

# Issue deprecation warning
warnings.warn(
    "utilities.logger is deprecated. Use infrastructure.utilities.logger instead.",
    DeprecationWarning,
    stacklevel=2
)

def get_logger(name=None):
    """
    Backward compatibility wrapper for infrastructure logger.
    
    Args:
        name: Logger name (ignored, uses ApplicationLogger instead)
        
    Returns:
        ApplicationLogger instance
    """
    return get_infrastructure_logger()

# Backward compatibility exports
__all__ = ['get_logger', 'log_function_call', 'display_logs_in_sidebar']
"""
DEPRECATED: Retry handler - use infrastructure.utilities.retry_handler instead.
This module provides backward compatibility shims.
"""
import warnings
from infrastructure.utilities.retry_handler import (
    RetryHandler as InfraRetryHandler,
    RetryConfig,
    RetryableError,
    NonRetryableError,
    with_retry as infra_with_retry,
    get_retry_handler as get_infra_retry_handler,
    CircuitBreaker
)

# Issue deprecation warning
warnings.warn(
    "utilities.retry_handler is deprecated. Use infrastructure.utilities.retry_handler instead.",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility wrapper for old RetryHandler interface
class RetryHandler:
    """Backward compatibility wrapper for infrastructure RetryHandler."""
    
    def __init__(self, max_retries=3, delay=1.0, backoff=2.0):
        config = RetryConfig(
            max_attempts=max_retries,
            base_delay=delay,
            backoff_factor=backoff
        )
        self._handler = get_infra_retry_handler("default")
        self._handler.config = config
    
    def execute(self, func, *args, **kwargs):
        """Execute a function with retry logic."""
        return self._handler.execute_with_retry(func, *args, **kwargs)

def retry_operation(max_retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    """Decorator for adding retry logic to functions."""
    return infra_with_retry(
        max_attempts=max_retries,
        base_delay=delay,
        backoff_factor=backoff,
        retry_exceptions=exceptions
    )

def retry_with_exponential_backoff(func, max_retries=3, initial_delay=1.0, max_delay=60.0):
    """Retry a function with exponential backoff."""
    handler = RetryHandler(max_retries, initial_delay, 2.0)
    return handler.execute(func)

def retry_network_operation(func, *args, **kwargs):
    """Retry a network operation with appropriate settings."""
    @retry_operation(max_retries=5, delay=2.0, backoff=1.5, 
                    exceptions=(ConnectionError, TimeoutError, OSError))
    def network_func():
        return func(*args, **kwargs)
    return network_func()

def retry_file_operation(func, *args, **kwargs):
    """Retry a file operation with appropriate settings."""
    @retry_operation(max_retries=3, delay=0.5, backoff=2.0, 
                    exceptions=(OSError, IOError, PermissionError))
    def file_func():
        return func(*args, **kwargs)
    return file_func()

def get_retry_handler(max_retries=3, delay=1.0, backoff=2.0):
    """Get a configured retry handler instance."""
    return RetryHandler(max_retries, delay, backoff)

def with_retry(max_retries=3, max_attempts=None, delay=1.0, base_delay=None, backoff=2.0):
    """Decorator alias for retry_operation for backward compatibility."""
    if max_attempts is not None:
        max_retries = max_attempts
    if base_delay is not None:
        delay = base_delay
    return retry_operation(max_retries, delay, backoff)

# Backward compatibility exports
__all__ = [
    'RetryHandler', 'retry_operation', 'retry_with_exponential_backoff',
    'retry_network_operation', 'retry_file_operation', 'get_retry_handler', 'with_retry'
]
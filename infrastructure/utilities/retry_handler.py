"""
Retry handler module for Resume Customizer application.
Provides robust retry logic for network operations and email sending.
"""

import time
import random
from typing import Callable, Any, Optional, Type, Tuple, List
from functools import wraps
import smtplib
import socket
from email.errors import MessageError

from .logger import get_logger

logger = get_logger()


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should not trigger a retry."""
    pass


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter."""
    
    # Network-related exceptions that should trigger retries
    RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        socket.timeout,
        socket.gaierror,
        smtplib.SMTPConnectError,
        smtplib.SMTPServerDisconnected,
        smtplib.SMTPRecipientsRefused,
        OSError,
    )
    
    # Exceptions that should not trigger retries
    NON_RETRYABLE_EXCEPTIONS = (
        smtplib.SMTPAuthenticationError,
        smtplib.SMTPDataError,
        MessageError,
        ValueError,
        TypeError,
    )
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (1-based)
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if we've exceeded max attempts
        if attempt >= self.config.max_attempts:
            return False
        
        # Don't retry non-retryable exceptions
        if isinstance(exception, self.NON_RETRYABLE_EXCEPTIONS):
            return False
        
        # Retry retryable exceptions
        if isinstance(exception, self.RETRYABLE_EXCEPTIONS):
            return True
        
        # For unknown exceptions, be conservative and don't retry
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using exponential backoff with jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(f"Executing {func.__name__} (attempt {attempt}/{self.config.max_attempts})")
                result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"Successfully executed {func.__name__} on attempt {attempt}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise e
                
                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} attempts failed for {func.__name__}: {str(e)}"
                    )
        
        # If we get here, all retries failed
        raise last_exception


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delays
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            handler = RetryHandler(config)
            return handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Predefined retry configurations for common scenarios
EMAIL_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=1.5,
    jitter=True
)

FILE_OPERATION_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=False
)


def get_retry_handler(config_type: str = "default") -> RetryHandler:
    """
    Get a retry handler with predefined configuration.
    
    Args:
        config_type: Type of configuration ('email', 'network', 'file', 'default')
        
    Returns:
        RetryHandler instance
    """
    configs = {
        'email': EMAIL_RETRY_CONFIG,
        'network': NETWORK_RETRY_CONFIG,
        'file': FILE_OPERATION_RETRY_CONFIG,
        'default': RetryConfig()
    }
    
    config = configs.get(config_type, RetryConfig())
    return RetryHandler(config)




"""
Error recovery functionality for Resume Customizer application.
Provides robust error recovery, automatic retry mechanisms, and graceful degradation.
"""

import gc
import time
import threading
from typing import Dict, Any, Optional, Callable, List, Union, Type
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum
import psutil
from io import BytesIO

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
from .base import ErrorHandler, ErrorContext, ErrorSeverity
from infrastructure.monitoring import CircuitBreakerConfig, get_circuit_breaker, CircuitBreakerError

logger = get_logger()
structured_logger = get_structured_logger("error_recovery")


class RecoveryStrategy(Enum):
    """Error recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: float = 0.1


class ErrorRecoveryManager:
    """Manages error recovery strategies."""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self._recovery_strategies: Dict[str, Dict[Type[Exception], RecoveryStrategy]] = {}
        self._fallback_functions: Dict[str, Callable] = {}
        self._circuit_breakers: Dict[str, Any] = {}
    
    def register_strategy(self, 
                        component: str, 
                        exception_type: Type[Exception], 
                        strategy: RecoveryStrategy):
        """Register a recovery strategy for a component and exception type."""
        if component not in self._recovery_strategies:
            self._recovery_strategies[component] = {}
        self._recovery_strategies[component][exception_type] = strategy
    
    def register_fallback(self, component: str, fallback_func: Callable):
        """Register a fallback function for a component."""
        self._fallback_functions[component] = fallback_func
    
    def setup_circuit_breaker(self, component: str, config: CircuitBreakerConfig):
        """Set up a circuit breaker for a component."""
        self._circuit_breakers[component] = get_circuit_breaker(config)
    
    def get_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate the delay for the next retry attempt."""
        delay = min(
            config.initial_delay * (config.exponential_base ** (attempt - 1)),
            config.max_delay
        )
        jitter = config.jitter * delay * (2 * random.random() - 1)
        return max(0, delay + jitter)
    
    def handle_with_recovery(self, 
                           component: str,
                           func: Callable,
                           *args,
                           retry_config: Optional[RetryConfig] = None,
                           **kwargs) -> Any:
        """Execute a function with error recovery."""
        if retry_config is None:
            retry_config = RetryConfig()
        
        attempt = 1
        last_error = None
        
        while attempt <= retry_config.max_attempts:
            try:
                # Check circuit breaker
                if component in self._circuit_breakers:
                    self._circuit_breakers[component].check()
                
                result = func(*args, **kwargs)
                
                # Success, reset circuit breaker if exists
                if component in self._circuit_breakers:
                    self._circuit_breakers[component].success()
                
                return result
                
            except Exception as e:
                last_error = e
                strategy = self._get_strategy(component, type(e))
                
                if strategy == RecoveryStrategy.RETRY and attempt < retry_config.max_attempts:
                    delay = self.get_retry_delay(attempt, retry_config)
                    logger.warning(f"Retry attempt {attempt} for {component} after {delay:.2f}s")
                    time.sleep(delay)
                    attempt += 1
                    continue
                    
                elif strategy == RecoveryStrategy.FALLBACK:
                    if component in self._fallback_functions:
                        logger.info(f"Using fallback for {component}")
                        return self._fallback_functions[component](*args, **kwargs)
                        
                elif strategy == RecoveryStrategy.CIRCUIT_BREAK:
                    if component in self._circuit_breakers:
                        self._circuit_breakers[component].failure()
                        
                # Log and re-raise if no recovery possible
                context = ErrorContext(
                    severity=ErrorSeverity.HIGH,
                    component=component,
                    operation=func.__name__,
                    details={
                        "attempts": attempt,
                        "strategy": strategy.value if strategy else None
                    }
                )
                self.error_handler.handle_error(last_error, context)
                raise
        
        # If we get here, all retries failed
        raise last_error
    
    def _get_strategy(self, 
                     component: str, 
                     exception_type: Type[Exception]) -> Optional[RecoveryStrategy]:
        """Get the recovery strategy for a component and exception type."""
        if component in self._recovery_strategies:
            # Check for exact match
            if exception_type in self._recovery_strategies[component]:
                return self._recovery_strategies[component][exception_type]
            
            # Check for parent exception types
            for exc_type, strategy in self._recovery_strategies[component].items():
                if issubclass(exception_type, exc_type):
                    return strategy
        
        return None


# Global error recovery manager instance
_error_recovery_manager = ErrorRecoveryManager()

def get_error_recovery_manager() -> ErrorRecoveryManager:
    """Get the global error recovery manager instance."""
    return _error_recovery_manager

def with_error_recovery(component: str, retry_config: Optional[RetryConfig] = None):
    """Decorator to add error recovery to a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return get_error_recovery_manager().handle_with_recovery(
                component, func, *args, retry_config=retry_config, **kwargs
            )
        return wrapper
    return decorator
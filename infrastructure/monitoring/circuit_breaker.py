"""
Circuit Breaker implementation for the Resume Customizer application.
Provides fault tolerance and graceful degradation of services.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, allowing requests
    OPEN = "open"         # Failed state, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for Circuit Breaker behavior"""
    failure_threshold: int = 5  # Number of failures before opening
    reset_timeout: int = 60     # Seconds to wait before attempting reset
    failure_window: int = 60    # Time window (in seconds) to track failures

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker prevents an operation"""
    pass

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = None
        self.last_attempt_time = None

    def can_execute(self) -> bool:
        """Check if the circuit breaker will allow execution"""
        now = datetime.now()

        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= timedelta(seconds=self.config.reset_timeout):
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.last_attempt_time and now - self.last_attempt_time < timedelta(seconds=self.config.reset_timeout):
                return False
            return True

        return True

    def record_success(self) -> None:
        """Record a successful operation"""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
        self.last_attempt_time = datetime.now()

    def record_failure(self) -> None:
        """Record a failed operation"""
        now = datetime.now()
        self.failures += 1
        self.last_failure_time = now
        self.last_attempt_time = now

        if self.failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failures} failures")

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker protection"""
        def wrapper(*args, **kwargs) -> Any:
            if not self.can_execute():
                raise CircuitBreakerError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise e

        return wrapper

_circuit_breakers = {}

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker instance"""
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig()
        _circuit_breakers[name] = CircuitBreaker(config)
    return _circuit_breakers[name]
"""
Standardized error handling for database operations
Provides consistent error handling, logging, and retry mechanisms
"""

import time
import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from typing import Callable, Any, Dict, Optional, Type, Union

# Configure logger
logger = logging.getLogger(__name__)

# Define custom exception classes
class DatabaseError(Exception):
    """Base class for all database-related exceptions"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class ConnectionError(DatabaseError):
    """Exception raised for connection-related errors"""
    pass

class QueryError(DatabaseError):
    """Exception raised for query-related errors"""
    pass

class DataIntegrityError(DatabaseError):
    """Exception raised for data integrity violations"""
    pass

class TransactionError(DatabaseError):
    """Exception raised for transaction-related errors"""
    pass

# Error mapping dictionary
ERROR_MAPPING: Dict[Type[SQLAlchemyError], Type[DatabaseError]] = {
    OperationalError: ConnectionError,
    IntegrityError: DataIntegrityError,
}

def handle_db_errors(func: Callable) -> Callable:
    """
    Decorator for handling database errors consistently
    
    Args:
        func: The function to wrap with error handling
        
    Returns:
        Wrapped function with standardized error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            # Map SQLAlchemy errors to our custom exceptions
            error_class = ERROR_MAPPING.get(type(e), DatabaseError)
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            
            # Create and raise our custom exception
            raise error_class(
                message=f"Database operation failed: {str(e)}",
                original_error=e
            )
        except Exception as e:
            # Handle non-SQLAlchemy exceptions
            logger.error(f"Unexpected error in database operation {func.__name__}: {str(e)}")
            raise DatabaseError(
                message=f"Unexpected error in database operation: {str(e)}",
                original_error=e
            )
    return wrapper

def with_retry(
    max_retries: int = 3,
    retry_delay: float = 0.5,
    exceptions: Union[Type[Exception], tuple] = OperationalError
) -> Callable:
    """
    Decorator for retrying database operations on specific exceptions
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        exceptions: Exception type(s) that should trigger a retry
        
    Returns:
        Wrapped function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        # Map to our custom exception
                        error_class = ERROR_MAPPING.get(type(e), DatabaseError)
                        raise error_class(
                            message=f"Operation failed after {max_retries} retries: {str(e)}",
                            original_error=e
                        )
                    
                    # Log retry attempt
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after error: {str(e)}"
                    )
                    
                    # Wait before retrying
                    time.sleep(retry_delay * (2 ** (retries - 1)))  # Exponential backoff
        return wrapper
    return decorator

# Example usage:
# @handle_db_errors
# @with_retry(max_retries=3)
# def get_user_by_id(session, user_id):
#     return session.query(User).filter(User.id == user_id).one()
"""
DEPRECATED: This module has been moved to database.utils.error_handler
This file exists for backward compatibility and will be removed in a future version.
"""

import warnings
from database.utils.error_handler import (
    handle_db_errors,
    with_retry,
    DatabaseError,
    ConnectionError,
    QueryError,
)

# Issue deprecation warning
warnings.warn(
    "Importing from database.error_handler is deprecated. Use database.utils.error_handler instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'handle_db_errors',
    'with_retry',
    'DatabaseError',
    'ConnectionError',
    'QueryError',
]
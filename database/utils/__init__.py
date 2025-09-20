"""
Database utility modules for the Resume Customizer application.
Contains shared utilities used across the database layer.
"""

from .error_handler import (
    handle_db_errors,
    with_retry,
    DatabaseError,
    ConnectionError,
    QueryError
)

# Optional encryption imports
try:
    from .encryption import (
        encrypt_data,
        decrypt_data,
        generate_key,
        EncryptionManager
    )
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    encrypt_data = None
    decrypt_data = None
    generate_key = None
    EncryptionManager = None

# Optional custom types imports
try:
    from .custom_types import (
        EncryptedString,
        EncryptedBinaryString,
        JSONEncodedDict,
        CompressedBinary
    )
    CUSTOM_TYPES_AVAILABLE = True
except ImportError:
    CUSTOM_TYPES_AVAILABLE = False
    EncryptedString = None
    EncryptedBinaryString = None
    JSONEncodedDict = None
    CompressedBinary = None

__all__ = [
    'handle_db_errors',
    'with_retry',
    'DatabaseError',
    'ConnectionError',
    'QueryError',
    'encrypt_data',
    'decrypt_data',
    'generate_key',
    'EncryptionManager',
    'EncryptedString',
    'EncryptedBinaryString',
    'JSONEncodedDict',
    'CompressedBinary'
]
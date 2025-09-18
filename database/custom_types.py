"""
Custom SQLAlchemy types for handling encrypted data
"""
from sqlalchemy.types import TypeDecorator, String, LargeBinary
import base64

class EncryptedBinaryString(TypeDecorator):
    """
    Custom type for storing encrypted binary data in the database
    """
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert the value before storing in database"""
        if value is not None:
            if isinstance(value, str):
                return value.encode()
            return value
        return None

    def process_result_value(self, value, dialect):
        """Convert the value when retrieving from database"""
        if value is not None:
            if isinstance(value, bytes):
                return value
            return value.encode()
        return None
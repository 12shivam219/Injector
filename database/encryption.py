"""
Database encryption utilities
Provides secure encryption and decryption for database connection strings
and sensitive user data
"""

import os
import base64
import secrets
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
import logging
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.ext.mutable import MutableComposite

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class EncryptionManager:
    """
    Handles encryption and decryption of sensitive data
    using Fernet symmetric encryption with key derivation
    """
    
    def __init__(self):
        """Initialize encryption with key from environment or generate one"""
        # Get encryption keys from environment or generate new ones
        self.primary_key = self._get_or_create_key('DB_ENCRYPTION_KEY')
        self.user_data_key = self._get_or_create_key('USER_DATA_ENCRYPTION_KEY')
        
        # Create Fernet instances for different encryption purposes
        self.connection_fernet = Fernet(self.primary_key)
        self.user_data_fernet = MultiFernet([
            Fernet(self.user_data_key),
            Fernet(self.primary_key)  # Fallback key for rotation
        ])
    
    def _get_or_create_key(self, env_var_name):
        """Get encryption key from environment or create a new one"""
        key = os.getenv(env_var_name)

        # Decide behavior based on environment early
        env_mode = os.getenv('ENV', os.getenv('ENVIRONMENT', 'development')).lower()

        # If key is present, validate it's a proper Fernet key and return it encoded
        if key:
            try:
                decoded = base64.urlsafe_b64decode(key.encode())
                if len(decoded) != 32:
                    raise ValueError("incorrect key length")
                return key.encode()
            except Exception:
                msg = (
                    f"Environment variable {env_var_name} is not a valid Fernet key. "
                    "Generate a new key with `python scripts/generate_keys.py` or use the setup script."
                )
                if env_mode in ('dev', 'development', ''):
                    logger.warning(msg + " Using a temporary development key instead.")
                    # fall through to generate a temporary dev key below
                else:
                    # In production-like environments, fail fast with a clear message
                    raise RuntimeError(msg)

        # No valid key found in environment -> generate temporary key in development
        salt = os.urandom(16)
        app_name = os.getenv('APP_NAME', 'ResumeCustomizer')
        password = f"{app_name}_{env_var_name}_{secrets.token_hex(8)}"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        generated_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        if env_mode in ('dev', 'development', ''):
            logger.warning(
                "%s missing or invalid; generated a temporary key for development. "
                "Add a stable key to your environment as %s for production.",
                env_var_name, env_var_name,
            )
            return generated_key

        # In production-like environments, fail fast so secrets aren't silently regenerated
        raise RuntimeError(
            f"Missing or invalid environment variable {env_var_name}. "
            "Set this as a secure secret in your deployment environment."
        )
    
    def encrypt_connection_string(self, connection_string):
        """
        Encrypt a database connection string
        
        Args:
            connection_string: Plain text connection string
            
        Returns:
            Encrypted connection string (base64 encoded)
        """
        if not connection_string:
            return None
            
        encrypted = self.connection_fernet.encrypt(connection_string.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_connection_string(self, encrypted_string):
        """
        Decrypt an encrypted database connection string
        
        Args:
            encrypted_string: Encrypted connection string (base64 encoded)
            
        Returns:
            Plain text connection string
        """
        if not encrypted_string:
            return None
            
        try:
            decoded = base64.urlsafe_b64decode(encrypted_string.encode())
            decrypted = self.connection_fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.exception("Error decrypting connection string: %s", e)
            return None
            
    def encrypt_user_data(self, data):
        """
        Encrypt sensitive user data
        
        Args:
            data: Plain text data
            
        Returns:
            Encrypted data (base64 encoded)
        """
        if not data:
            return None
            
        if isinstance(data, str):
            data = data.encode()
            
        encrypted = self.user_data_fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_user_data(self, encrypted_data):
        """
        Decrypt encrypted user data
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
            
        Returns:
            Plain text data
        """
        if not encrypted_data:
            return None
            
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.user_data_fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.exception("Error decrypting user data: %s", e)
            return None

# Global encryption instance
encryption_manager = EncryptionManager()

def encrypt_connection_string(connection_string):
    """Encrypt a database connection string"""
    return encryption_manager.encrypt_connection_string(connection_string)

def decrypt_connection_string(encrypted_string):
    """Decrypt an encrypted database connection string"""
    return encryption_manager.decrypt_connection_string(encrypted_string)

def encrypt_user_data(data):
    """Encrypt sensitive user data"""
    return encryption_manager.encrypt_user_data(data)

def decrypt_user_data(encrypted_data):
    """Decrypt encrypted user data"""
    return encryption_manager.decrypt_user_data(encrypted_data)


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type decorator that automatically encrypts and decrypts
    sensitive string data stored in the database
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt data before storing in database"""
        if value is not None:
            return encrypt_user_data(value)
        return None

    def process_result_value(self, value, dialect):
        """Decrypt data when retrieving from database"""
        if value is not None:
            return decrypt_user_data(value)
        return None


class MutableEncryptedString(MutableComposite):
    """
    Mutable encrypted string type for SQLAlchemy models
    Allows tracking changes to encrypted fields
    """
    
    def __init__(self, value=None):
        self._value = value
        
    def __composite_values__(self):
        return (self._value,)
        
    def __eq__(self, other):
        if isinstance(other, MutableEncryptedString):
            return self._value == other._value
        return self._value == other
        
    def __repr__(self):
        return f"<MutableEncryptedString(value='{self._value}')>"
        
    @classmethod
    def coerce(cls, key, value):
        """Convert plain strings to MutableEncryptedString"""
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        return cls(value)
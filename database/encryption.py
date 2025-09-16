"""
Database connection string encryption utilities
Provides secure encryption and decryption for database connection strings
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConnectionEncryption:
    """
    Handles encryption and decryption of database connection strings
    using Fernet symmetric encryption with key derivation
    """
    
    def __init__(self):
        """Initialize encryption with key from environment or generate one"""
        # Get encryption key from environment or generate a new one
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_key(self):
        """Get encryption key from environment or create a new one"""
        key = os.getenv('DB_ENCRYPTION_KEY')
        
        if not key:
            # Generate a new key if not found in environment
            salt = os.urandom(16)
            # Use application name as password with salt
            app_name = os.getenv('APP_NAME', 'ResumeCustomizer')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(app_name.encode()))
            print(f"Generated new encryption key: {key.decode()}")
            print("Add this key to your .env file as DB_ENCRYPTION_KEY")
        else:
            # Use the key from environment
            key = key.encode()
            
        return key
    
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
            
        encrypted = self.fernet.encrypt(connection_string.encode())
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
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            print(f"Error decrypting connection string: {e}")
            return None

# Global encryption instance
connection_encryption = ConnectionEncryption()

def encrypt_connection_string(connection_string):
    """Encrypt a database connection string"""
    return connection_encryption.encrypt_connection_string(connection_string)

def decrypt_connection_string(encrypted_string):
    """Decrypt an encrypted database connection string"""
    return connection_encryption.decrypt_connection_string(encrypted_string)
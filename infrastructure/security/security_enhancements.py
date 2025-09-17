"""
Security enhancements for Resume Customizer application.
Provides password encryption, input sanitization, and rate limiting.
"""

import hashlib
import secrets
import time
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from functools import wraps
import streamlit as st

class SecurePasswordManager:
    """Secure password handling with encryption."""
    
    def __init__(self):
        # Generate or retrieve encryption key (should be stored securely in production)
        if 'encryption_key' not in st.session_state:
            st.session_state.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(st.session_state.encryption_key)
    
    def encrypt_password(self, password: str) -> bytes:
        """Encrypt password for temporary storage."""
        return self.cipher.encrypt(password.encode())
    
    def decrypt_password(self, encrypted_password: bytes) -> str:
        """Decrypt password when needed."""
        return self.cipher.decrypt(encrypted_password).decode()
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple:
        """Hash password with salt for secure storage."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Using PBKDF2 with SHA256
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return password_hash, salt


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks."""
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email input."""
        if not email:
            return ""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\n', '\r', '\t']
        sanitized = email.strip()
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        return sanitized
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        if not filename:
            return ""
        # Remove path traversal attempts
        sanitized = filename.replace('..', '').replace('/', '').replace('\\', '')
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        return sanitized.strip()
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 10000) -> str:
        """Sanitize general text input."""
        if not text:
            return ""
        # Limit length to prevent DoS
        sanitized = text[:max_length]
        # Remove control characters except newlines and tabs
        sanitized = ''.join(char for char in sanitized 
                          if ord(char) >= 32 or char in ['\n', '\t', '\r'])
        return sanitized.strip()


class RateLimiter:
    """Simple rate limiting to prevent abuse."""
    
    def __init__(self):
        if 'rate_limits' not in st.session_state:
            st.session_state.rate_limits = {}
    
    def check_rate_limit(self, user_id: str, action: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user is within rate limits."""
        now = time.time()
        key = f"{user_id}_{action}"
        
        if key not in st.session_state.rate_limits:
            st.session_state.rate_limits[key] = []
        
        # Clean old entries
        st.session_state.rate_limits[key] = [
            timestamp for timestamp in st.session_state.rate_limits[key] 
            if now - timestamp < window
        ]
        
        # Check limit
        if len(st.session_state.rate_limits[key]) >= limit:
            return False
        
        # Add current request
        st.session_state.rate_limits[key].append(now)
        return True


def rate_limit(action: str, limit: int = 10, window: int = 60):
    """Decorator for rate limiting functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = st.session_state.get('user_id', 'anonymous')
            limiter = RateLimiter()
            
            if not limiter.check_rate_limit(user_id, action, limit, window):
                st.error(f"Rate limit exceeded for {action}. Please try again later.")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class SessionSecurityManager:
    """Manage session security features."""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token for forms."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token: str, expected: str) -> bool:
        """Validate CSRF token."""
        return secrets.compare_digest(token, expected)
    
    @staticmethod
    def session_timeout_check(timeout_minutes: int = 30) -> bool:
        """Check if session has timed out."""
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = time.time()
            return False
        
        if time.time() - st.session_state.last_activity > (timeout_minutes * 60):
            # Clear sensitive session data
            sensitive_keys = [key for key in st.session_state.keys() 
                            if 'password' in key.lower() or 'credential' in key.lower()]
            for key in sensitive_keys:
                del st.session_state[key]
            return True
        
        st.session_state.last_activity = time.time()
        return False


# Usage examples:
def secure_email_form(file_name: str):
    """Secure version of email form with encryption and sanitization."""
    password_manager = SecurePasswordManager()
    sanitizer = InputSanitizer()
    
    # CSRF protection
    if 'csrf_token' not in st.session_state:
        st.session_state.csrf_token = SessionSecurityManager.generate_csrf_token()
    
    with st.form(f"secure_email_form_{file_name}"):
        email_to = st.text_input(f"Recipient email for {file_name}")
        sender_email = st.text_input(f"Sender email for {file_name}")
        sender_password = st.text_input(f"Password for {file_name}", type="password")
        
        # Hidden CSRF token
        csrf_token = st.text_input("", value=st.session_state.csrf_token, 
                                 type="password", label_visibility="hidden")
        
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            # Validate CSRF token
            if not SessionSecurityManager.validate_csrf_token(csrf_token, st.session_state.csrf_token):
                st.error("Security validation failed. Please refresh and try again.")
                return None
            
            # Sanitize inputs
            clean_email_to = sanitizer.sanitize_email(email_to)
            clean_sender_email = sanitizer.sanitize_email(sender_email)
            
            # Encrypt password for temporary storage
            if sender_password:
                encrypted_password = password_manager.encrypt_password(sender_password)
                # Store encrypted password in session
                st.session_state[f"encrypted_password_{file_name}"] = encrypted_password
            
            return {
                'email_to': clean_email_to,
                'sender_email': clean_sender_email,
                'has_password': bool(sender_password)
            }
    
    return None



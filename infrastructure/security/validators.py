"""
Input validation and security module for Resume Customizer application.
Provides comprehensive validation for files, emails, and user inputs.
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Any
from email.utils import parseaddr
import streamlit as st
from datetime import datetime, timedelta

# Try to import python-magic, fall back to basic validation if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from ..utilities.logger import get_logger

# Import InputSanitizer with error handling to avoid circular imports
try:
    from .security_enhancements import InputSanitizer
except ImportError:
    # Fallback if security_enhancements is not available
    class InputSanitizer:
        @staticmethod
        def sanitize_text(text):
            return str(text).strip()
        
        @staticmethod
        def sanitize_filename(filename):
            return str(filename).strip()

logger = get_logger()


class FileValidator:
    """Validates uploaded files for security and compatibility."""
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB total
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.docx', '.doc'}
    
    # Suspicious file patterns
    SUSPICIOUS_PATTERNS = [
        r'\.exe$', r'\.bat$', r'\.cmd$', r'\.scr$', r'\.vbs$', r'\.js$',
        r'\.jar$', r'\.com$', r'\.pif$', r'\.msi$', r'\.dll$'
    ]
    
    def __init__(self):
        self.total_uploaded_size = 0
        self.sanitizer = InputSanitizer()
    
    def validate_file(self, file_obj) -> Dict[str, Any]:
        """
        Validate a single uploaded file.
        
        Args:
            file_obj: Streamlit uploaded file object
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Basic file info
            if hasattr(file_obj, 'getvalue'):
                file_size = len(file_obj.getvalue())
            elif hasattr(file_obj, 'size'):
                file_size = file_obj.size
            elif hasattr(file_obj, 'read'):
                # Try to read and get length, then reset pointer
                pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
                file_content = file_obj.read()
                file_size = len(file_content)
                if hasattr(file_obj, 'seek') and pos is not None:
                    file_obj.seek(pos)
            else:
                file_size = 0
            file_name = getattr(file_obj, 'name', 'unknown')
            # Sanitize filename for security
            clean_file_name = self.sanitizer.sanitize_filename(file_name)

            result['file_info'] = {
                'name': clean_file_name,
                'original_name': file_name,
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2)
            }
            
            # File size validation
            if file_size > self.MAX_FILE_SIZE:
                result['valid'] = False
                result['errors'].append(
                    f"File '{clean_file_name}' is too large ({result['file_info']['size_mb']}MB). "
                    f"Maximum allowed: {self.MAX_FILE_SIZE // (1024 * 1024)}MB"
                )
            
            # Total size validation
            self.total_uploaded_size += file_size
            if self.total_uploaded_size > self.MAX_TOTAL_SIZE:
                result['valid'] = False
                result['errors'].append(
                    f"Total upload size exceeds limit ({self.MAX_TOTAL_SIZE // (1024 * 1024)}MB)"
                )
            
            # File extension validation
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                result['valid'] = False
                result['errors'].append(
                    f"File '{file_name}' has unsupported extension '{file_ext}'. "
                    f"Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
                )
            
            # Suspicious filename patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, file_name, re.IGNORECASE):
                    result['valid'] = False
                    result['errors'].append(f"File '{file_name}' has suspicious extension")
                    break
            
            # MIME type validation (if python-magic is available)
            if MAGIC_AVAILABLE:
                try:
                    file_content = file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read()
                    mime_type = magic.from_buffer(file_content, mime=True)
                    if mime_type not in self.ALLOWED_MIME_TYPES:
                        result['warnings'].append(
                            f"File '{file_name}' MIME type '{mime_type}' may not be supported"
                        )
                    # Reset file pointer if possible
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                except Exception as e:
                    logger.warning(f"Could not validate MIME type for {file_name}: {str(e)}")
                    result['warnings'].append("Could not verify file type")
            else:
                # Only warn if python-magic is actually not available
                result['warnings'].append("File type validation is less robust because 'python-magic' is not installed. Please install it for better security.")
                try:
                    file_content = file_obj.getvalue() if hasattr(file_obj, 'getvalue') else file_obj.read()
                    # Check for DOCX signature (PK header + specific content)
                    if len(file_content) >= 4:
                        # DOCX files start with PK (ZIP signature)
                        if file_content[:2] == b'PK':
                            # More comprehensive check for DOCX-specific content
                            docx_indicators = [
                                b'word/',
                                b'docProps',
                                b'[Content_Types].xml',
                                b'_rels/.rels',
                                b'word/document.xml'
                            ]
                            # Check in larger portion of file for DOCX structure
                            search_content = file_content[:4096]  # Search first 4KB
                            has_docx_structure = any(indicator in search_content for indicator in docx_indicators)
                            if has_docx_structure:
                                logger.debug(f"File '{file_name}' appears to be a valid DOCX file")
                            else:
                                logger.info(f"File '{file_name}' has ZIP structure but DOCX indicators not found in header - attempting to process anyway")
                        else:
                            result['warnings'].append(
                                f"File '{file_name}' does not appear to be a DOCX file (missing ZIP signature)"
                            )
                    # Reset file pointer if possible
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                except Exception as e:
                    logger.warning(f"Could not validate file signature for {file_name}: {str(e)}")
                    result['warnings'].append("Could not verify file type (python-magic not available)")
            
            # Empty file check
            if file_size == 0:
                result['valid'] = False
                result['errors'].append(f"File '{file_name}' is empty")
            elif file_size < 100:  # Very small files might be corrupt
                result['warnings'].append(f"File '{file_name}' is very small ({file_size} bytes) - may be corrupt")
            
            # Log validation result without sensitive data
            status = 'PASSED' if result['valid'] else 'FAILED'
            logger.info(f"File validation for '{file_name}': {status} (size: {result['file_info']['size_mb']}MB)")
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"File validation error: {str(e)}")
            logger.error(f"File validation failed for {file_name}", exception=e)
        
        return result
    
    def validate_batch(self, files: List) -> Dict[str, Any]:
        """
        Validate multiple files.
        
        Args:
            files: List of uploaded file objects
            
        Returns:
            Batch validation result
        """
        self.total_uploaded_size = 0  # Reset counter
        
        results = {
            'valid': True,
            'files': {},
            'summary': {
                'total_files': len(files),
                'valid_files': 0,
                'total_size_mb': 0,
                'errors': [],
                'warnings': []
            }
        }
        
        for file_obj in files:
            file_name = getattr(file_obj, 'name', 'unknown')
            file_result = self.validate_file(file_obj)
            results['files'][file_name] = file_result
            
            if file_result['valid']:
                results['summary']['valid_files'] += 1
            else:
                results['valid'] = False
                results['summary']['errors'].extend(file_result['errors'])
            
            results['summary']['warnings'].extend(file_result['warnings'])
        
        results['summary']['total_size_mb'] = round(self.total_uploaded_size / (1024 * 1024), 2)
        
        return results


class EmailValidator:
    """Validates email addresses and configurations."""
    
    # Common email domains for validation
    COMMON_DOMAINS = {
        'gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 
        'protonmail.com', 'icloud.com', 'aol.com'
    }
    
    # Suspicious email patterns
    SUSPICIOUS_PATTERNS = [
        r'[<>"\']',  # HTML/script characters
        r'javascript:', r'data:', r'vbscript:',  # Script protocols
        r'\.\.',  # Directory traversal
    ]
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """
        Validate email address format and security.
        
        Args:
            email: Email address to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        if not email or not email.strip():
            result['valid'] = False
            result['errors'].append("Email address is required")
            return result
        
        email = email.strip()
        
        # Parse email address
        parsed_name, parsed_email = parseaddr(email)
        if not parsed_email:
            result['valid'] = False
            result['errors'].append("Invalid email format")
            return result
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, parsed_email):
            result['valid'] = False
            result['errors'].append("Invalid email format")
            return result
        
        # Security checks
        for pattern in EmailValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, email, re.IGNORECASE):
                result['valid'] = False
                result['errors'].append("Email contains suspicious characters")
                break
        
        # Extract domain
        domain = parsed_email.split('@')[1].lower()
        result['info']['domain'] = domain
        
        # Domain validation
        if domain in EmailValidator.COMMON_DOMAINS:
            result['info']['domain_type'] = 'common'
        else:
            result['info']['domain_type'] = 'custom'
            result['warnings'].append(f"Using custom domain: {domain}")
        
        # Length validation
        if len(parsed_email) > 254:  # RFC 5321 limit
            result['valid'] = False
            result['errors'].append("Email address too long")
        
        return result
    
    @staticmethod
    def validate_smtp_config(smtp_server: str, smtp_port: int) -> Dict[str, Any]:
        """
        Validate SMTP configuration.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Server validation
        if not smtp_server or not smtp_server.strip():
            result['valid'] = False
            result['errors'].append("SMTP server is required")
        elif smtp_server.strip().lower() == 'custom':
            result['warnings'].append("Custom SMTP server may have limited support")
        
        # Port validation
        if not isinstance(smtp_port, int) or smtp_port < 1 or smtp_port > 65535:
            result['valid'] = False
            result['errors'].append("Invalid SMTP port (must be 1-65535)")
        elif smtp_port not in [25, 465, 587, 2525]:
            result['warnings'].append(f"Uncommon SMTP port: {smtp_port}")
        
        return result


class TextValidator:
    """Validates text inputs for security and content."""
    
    MAX_TEXT_LENGTH = 50000  # 50KB of text
    
    # Suspicious patterns in text
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'data:.*base64',  # Base64 data URLs
        r'<iframe[^>]*>',  # Iframe tags
        r'<object[^>]*>',  # Object tags
        r'<embed[^>]*>',  # Embed tags
    ]
    
    @staticmethod
    def validate_text_input(text: str, field_name: str = "text") -> Dict[str, Any]:
        """
        Validate text input for security and content.
        
        Args:
            text: Text to validate
            field_name: Name of the field for error messages
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        if not text:
            return result  # Empty text is allowed
        
        # Length validation
        if len(text) > TextValidator.MAX_TEXT_LENGTH:
            result['valid'] = False
            result['errors'].append(
                f"{field_name} is too long ({len(text)} chars). "
                f"Maximum: {TextValidator.MAX_TEXT_LENGTH}"
            )
        
        # Security validation
        for pattern in TextValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                result['valid'] = False
                result['errors'].append(f"{field_name} contains potentially malicious content")
                break
        
        # Content analysis
        result['info'] = {
            'length': len(text),
            'lines': len(text.splitlines()),
            'words': len(text.split())
        }
        
        # Check for reasonable content structure
        if result['info']['lines'] > 1000:
            result['warnings'].append(f"{field_name} has many lines ({result['info']['lines']})")
        
        return result


class RateLimiter:
    """Simple rate limiter for user actions."""
    
    def __init__(self):
        self.user_actions = {}
    
    def is_rate_limited(
        self, 
        user_id: str, 
        action: str, 
        max_requests: int = 10, 
        time_window: int = 60
    ) -> bool:
        """
        Check if user is rate limited for a specific action.
        
        Args:
            user_id: User identifier
            action: Action name
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        now = datetime.now()
        key = f"{user_id}:{action}"
        
        if key not in self.user_actions:
            self.user_actions[key] = []
        
        # Clean old entries
        cutoff = now - timedelta(seconds=time_window)
        self.user_actions[key] = [
            timestamp for timestamp in self.user_actions[key] 
            if timestamp > cutoff
        ]
        
        # Check rate limit
        if len(self.user_actions[key]) >= max_requests:
            return True
        
        # Record this action
        self.user_actions[key].append(now)
        return False


# Global instances
file_validator = FileValidator()
_rate_limiter = RateLimiter()


def get_file_validator() -> FileValidator:
    """Get the global file validator instance."""
    return file_validator


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def validate_email_format(email: str) -> Dict[str, Any]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validation result dictionary
    """
    return EmailValidator.validate_email(email)


def validate_file_upload(file_obj) -> Dict[str, Any]:
    """
    Validate uploaded file.
    
    Args:
        file_obj: Streamlit uploaded file object
        
    Returns:
        Validation result dictionary
    """
    return file_validator.validate_file(file_obj)


class SecurityValidator:
    """Main security validator class."""
    
    def __init__(self):
        self.file_validator = FileValidator()
        self.rate_limiter = RateLimiter()
    
    def validate_all(self, **kwargs) -> Dict[str, Any]:
        """Validate multiple inputs at once."""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate email if provided
        if 'email' in kwargs:
            email_result = validate_email_format(kwargs['email'])
            if not email_result['valid']:
                results['valid'] = False
                results['errors'].extend(email_result['errors'])
            results['warnings'].extend(email_result.get('warnings', []))
        
        # Validate files if provided
        if 'files' in kwargs:
            file_result = self.file_validator.validate_batch(kwargs['files'])
            if not file_result['valid']:
                results['valid'] = False
                results['errors'].extend(file_result['summary']['errors'])
            results['warnings'].extend(file_result['summary']['warnings'])
        
        return results


def validate_session_state() -> Dict[str, Any]:
    """
    Validate Streamlit session state for security.
    
    Returns:
        Validation result dictionary
    """
    result = {
        'valid': True,
        'warnings': [],
        'cleaned_keys': []
    }
    
    try:
        # Check for suspicious session keys
        suspicious_patterns = [
            r'<script', r'javascript:', r'eval\(', r'exec\('
        ]
        
        for key in list(st.session_state.keys()):
            key_str = str(key)
            for pattern in suspicious_patterns:
                if re.search(pattern, key_str, re.IGNORECASE):
                    del st.session_state[key]
                    result['cleaned_keys'].append(key_str)
                    result['warnings'].append(f"Removed suspicious session key: {key_str}")
                    break
        
        # Limit session state size
        if len(st.session_state) > 100:
            result['warnings'].append(f"Large session state ({len(st.session_state)} keys)")
        
    except Exception as e:
        logger.error("Session state validation failed", exception=e)
        result['valid'] = False
    
    return result




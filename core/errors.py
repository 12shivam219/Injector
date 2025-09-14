"""
Core error definitions for the Resume Customizer application.
"""

class ResumeCustomizerError(Exception):
    """Base exception for Resume Customizer application."""
    pass

class ProcessingError(ResumeCustomizerError):
    """Error during document processing."""
    pass

class ValidationError(ResumeCustomizerError):
    """Error during input validation."""
    pass

class ConfigurationError(ResumeCustomizerError):
    """Error in application configuration."""
    pass

class DatabaseError(ResumeCustomizerError):
    """Error during database operations."""
    pass

class EmailError(ResumeCustomizerError):
    """Error during email operations."""
    pass

class FileError(ResumeCustomizerError):
    """Error during file operations."""
    pass

class NetworkError(ResumeCustomizerError):
    """Error during network operations."""
    pass

class AuthenticationError(ResumeCustomizerError):
    """Error during authentication."""
    pass

class AuthorizationError(ResumeCustomizerError):
    """Error during authorization."""
    pass

class TimeoutError(ResumeCustomizerError):
    """Operation timeout error."""
    pass

class ResourceExhaustedError(ResumeCustomizerError):
    """System resources exhausted."""
    pass

# Export all errors
__all__ = [
    'ResumeCustomizerError', 'ProcessingError', 'ValidationError', 'ConfigurationError',
    'DatabaseError', 'EmailError', 'FileError', 'NetworkError',
    'AuthenticationError', 'AuthorizationError', 'TimeoutError', 'ResourceExhaustedError'
]
"""
Core type definitions for the Resume Customizer application.
"""

from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum

# Generic types
T = TypeVar('T')
ResponseType = TypeVar('ResponseType')

# Document types
class DocumentFormat(Enum):
    """Supported document formats."""
    DOCX = "docx"
    DOC = "doc" 
    PDF = "pdf"
    TXT = "txt"

class ProcessingStatus(Enum):
    """Processing status for documents."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    processing_time: Optional[float] = None

@dataclass
class FileInfo:
    """Information about uploaded files."""
    name: str
    size: int
    format: DocumentFormat
    content: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class UserPreferences:
    """User interface and processing preferences."""
    theme: str = "light"
    show_debug: bool = False
    auto_save: bool = True
    preferred_format: DocumentFormat = DocumentFormat.DOCX
    email_notifications: bool = True

# Function type aliases
ProcessorFunction = Callable[[Any], ProcessingResult]
ValidatorFunction = Callable[[Any], bool]
HandlerFunction = Callable[[Any], Any]

# Export all types
__all__ = [
    'T', 'ResponseType', 'DocumentFormat', 'ProcessingStatus', 'LogLevel',
    'ProcessingResult', 'FileInfo', 'UserPreferences',
    'ProcessorFunction', 'ValidatorFunction', 'HandlerFunction'
]
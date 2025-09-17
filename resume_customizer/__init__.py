"""
Resume Customizer Module

This module contains all components related to resume customization:
- Text parsers for different input formats
- Document processors for handling Word documents
- Project detectors for finding resume sections
- Bullet formatters for consistent formatting
- Email handlers for sending customized resumes
"""

# Import main interfaces
from .parsers.text_parser import get_parser, parse_input_text
from .parsers.restricted_text_parser import parse_input_text_restricted, RestrictedFormatError
from .processors.resume_processor import get_resume_manager
from .processors.document_processor import get_document_processor
from .email.email_handler import get_email_manager

__all__ = [
    'get_parser',
    'parse_input_text', 
    'parse_input_text_restricted',
    'RestrictedFormatError',
    'get_resume_manager',
    'get_document_processor',
    'get_email_manager'
]
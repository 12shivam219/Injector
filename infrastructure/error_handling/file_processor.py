"""
File processor error handling module for Resume Customizer application.
Provides specialized error handling for file processing operations.
"""

import os
import traceback
from typing import Dict, Any, Optional, Callable, TypeVar, List
from functools import wraps
from datetime import datetime
import streamlit as st

from core.errors import FileError, ProcessingError
from infrastructure.utilities.logger import get_logger
from infrastructure.error_handling.base import ErrorContext, ErrorSeverity

logger = get_logger()

# Type variable for generic function return type
T = TypeVar('T')

class FileProcessingError(FileError):
    """Specialized error for file processing failures."""
    def __init__(self, message: str, filename: str, original_error: Optional[Exception] = None):
        self.filename = filename
        self.original_error = original_error
        self.timestamp = datetime.now()
        super().__init__(f"{message} (File: {filename})")


class FileErrorHandler:
    """Handler for file processing errors with detailed diagnostics."""
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def handle_file_error(self, error: Exception, filename: str, operation: str) -> Dict[str, Any]:
        """Handle a file processing error and return diagnostic information."""
        error_info = {
            'timestamp': datetime.now(),
            'filename': filename,
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        # Add diagnostic information
        error_info['diagnostics'] = self._diagnose_error(error, filename)
        
        # Log the error
        logger.error(
            f"File processing error: {error_info['error_type']} in {operation} for {filename}: {str(error)}"
        )
        
        # Add to history with limit
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        return error_info
    
    def _diagnose_error(self, error: Exception, filename: str) -> Dict[str, Any]:
        """Diagnose common file processing errors."""
        diagnostics = {
            'possible_causes': [],
            'suggested_solutions': [],
            'severity': 'medium'
        }
        
        # Check file existence
        if not os.path.exists(filename) and isinstance(error, (FileNotFoundError, IOError)):
            diagnostics['possible_causes'].append("File does not exist or was moved")
            diagnostics['suggested_solutions'].append("Verify the file path and try uploading again")
            diagnostics['severity'] = 'high'
        
        # Check file permissions
        elif isinstance(error, PermissionError):
            diagnostics['possible_causes'].append("Insufficient permissions to access the file")
            diagnostics['suggested_solutions'].append("Check file permissions or try with different credentials")
            diagnostics['severity'] = 'high'
        
        # Check file format issues
        elif "format" in str(error).lower() or "corrupt" in str(error).lower():
            diagnostics['possible_causes'].append("File may be corrupted or in an unsupported format")
            diagnostics['suggested_solutions'].append("Try with a different file or convert to a supported format")
            diagnostics['severity'] = 'medium'
        
        # Memory issues
        elif "memory" in str(error).lower() or isinstance(error, MemoryError):
            diagnostics['possible_causes'].append("File is too large to process with available memory")
            diagnostics['suggested_solutions'].append("Try with a smaller file or increase system resources")
            diagnostics['severity'] = 'high'
        
        # Generic fallback
        else:
            diagnostics['possible_causes'].append("Unknown error during file processing")
            diagnostics['suggested_solutions'].append("Check the file and try again")
            diagnostics['severity'] = 'medium'
        
        return diagnostics


def with_file_error_handling(operation_name: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Decorator for handling file processing errors with user feedback.
    
    Args:
        operation_name: Name of the operation for error reporting
        severity: Severity level of errors from this operation
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            # Extract filename from args or kwargs
            filename = None
            for arg in args:
                if isinstance(arg, str) and (arg.endswith('.docx') or arg.endswith('.pdf')):
                    filename = arg
                    break
            
            if not filename and 'file' in kwargs:
                file_arg = kwargs['file']
                if hasattr(file_arg, 'name'):
                    filename = file_arg.name
                elif isinstance(file_arg, str):
                    filename = file_arg
            
            if not filename:
                filename = "unknown_file"
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create error handler if needed
                handler = FileErrorHandler()
                error_info = handler.handle_file_error(e, filename, operation_name)
                
                # Display user-friendly error in Streamlit
                if st._is_running:
                    st.error(f"❌ Error processing file {filename}: {str(e)}")
                    
                    # Show detailed diagnostics for medium/high severity
                    if error_info['diagnostics']['severity'] in ['medium', 'high']:
                        with st.expander("📊 Error Diagnostics"):
                            st.write("**Possible Causes:**")
                            for cause in error_info['diagnostics']['possible_causes']:
                                st.write(f"- {cause}")
                            
                            st.write("**Suggested Solutions:**")
                            for solution in error_info['diagnostics']['suggested_solutions']:
                                st.write(f"- {solution}")
                    
                    # Show technical details for developers
                    with st.expander("🔍 Technical Details (for support)"):
                        st.code(error_info['traceback'])
                
                # Return None or error info depending on the use case
                return None
        
        return wrapper
    return decorator
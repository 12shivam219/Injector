"""
Logging module for Resume Customizer application.
Provides structured logging with different levels and formatters.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List, Any
from functools import wraps
from threading import Lock
import streamlit as st


class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        return formatted


class StreamlitLogHandler(logging.Handler):
    """Thread-safe custom log handler for Streamlit integration."""
    
    def __init__(self, max_logs: int = 50):
        super().__init__()
        self.logs = []
        self.max_logs = max_logs
        self._lock = Lock()  # Thread safety for logs list
    
    def emit(self, record):
        """Emit a log record with thread safety."""
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # Store log with comprehensive metadata
            log_entry = {
                'timestamp': timestamp,
                'level': record.levelname.strip('\033[0-9;m'),  # Remove color codes
                'message': record.getMessage(),
                'module': getattr(record, 'module', 'unknown'),
                'funcName': getattr(record, 'funcName', ''),
                'lineno': getattr(record, 'lineno', 0),
                'created': record.created
            }
            
            # Thread-safe log storage
            with self._lock:
                self.logs.append(log_entry)
                # Keep only recent logs
                if len(self.logs) > self.max_logs:
                    self.logs = self.logs[-self.max_logs:]
                
        except Exception as e:
            # Use handleError for proper error handling
            self.handleError(record)
    
    def get_recent_logs(self, level: Optional[str] = None, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs with optional filtering and thread safety.
        
        Args:
            level: Optional log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            count: Maximum number of logs to return
            
        Returns:
            List of log entries sorted by timestamp (newest first)
        """
        try:
            with self._lock:
                # Create a copy to avoid thread safety issues
                logs_copy = self.logs.copy()
            
            # Filter by level if specified
            if level:
                logs_copy = [log for log in logs_copy if log['level'].upper() == level.upper()]
            
            # Sort by created timestamp (newest first) and limit count
            sorted_logs = sorted(logs_copy, key=lambda x: x['created'], reverse=True)
            return sorted_logs[:count]
            
        except Exception:
            # Return empty list on any error
            return []


class ApplicationLogger:
    """Main logger class for the Resume Customizer application."""
    
    def __init__(self, name: str = "ResumeCustomizer"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
        
        self.streamlit_handler = None
        self._setup_streamlit_handler()
    
    def _setup_handlers(self):
        """Setup file and console handlers."""
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"{self.name.lower()}.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = CustomFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _setup_streamlit_handler(self):
        """Setup Streamlit-specific handler."""
        self.streamlit_handler = StreamlitLogHandler()
        self.streamlit_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        self.streamlit_handler.setFormatter(formatter)
        self.logger.addHandler(self.streamlit_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.critical(message, extra=kwargs)
    
    def log_performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics."""
        self.info(
            f"Performance: {operation} completed in {duration:.2f}s",
            operation=operation,
            duration=duration,
            **metrics
        )
    
    def log_user_action(self, action: str, user_id: Optional[str] = None, **details):
        """Log user actions for analytics."""
        self.info(
            f"User Action: {action}",
            action=action,
            user_id=user_id or "anonymous",
            **details
        )
    
    def get_recent_logs(self, level: Optional[str] = None, count: int = 10):
        """Get recent logs from Streamlit handler."""
        if self.streamlit_handler:
            return self.streamlit_handler.get_recent_logs(level, count)
        return []


# Global logger instance
app_logger = ApplicationLogger()


def get_logger() -> ApplicationLogger:
    """Get the global application logger."""
    return app_logger


def log_function_call(func_name: Optional[str] = None, log_args: bool = False, log_result: bool = False):
    """Enhanced decorator to log function calls with optional argument and result logging.
    
    Args:
        func_name: Optional custom name for the function (defaults to actual function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result (be careful with sensitive data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **func_kwargs):
            name = func_name or func.__name__
            start_time = datetime.now()
            
            # Log function start
            log_msg = f"Starting {name}"
            if log_args and (args or func_kwargs):
                log_msg += f" with args={args[:3]}..." if len(args) > 3 else f" with args={args}"
                if func_kwargs:
                    log_msg += f" kwargs={list(func_kwargs.keys())}"
            
            app_logger.debug(log_msg)
            
            try:
                result = func(*args, **func_kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Log completion
                completion_msg = f"Completed {name} in {duration:.2f}s"
                if log_result and result is not None:
                    result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                    completion_msg += f" -> {result_preview}"
                    
                app_logger.debug(completion_msg)
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                app_logger.error(f"Failed {name} after {duration:.2f}s: {type(e).__name__}: {str(e)}", exception=e)
                raise
        return wrapper
    return decorator


def display_logs_in_sidebar():
    """Display recent logs in Streamlit sidebar."""
    try:
        with st.sidebar:
            if st.checkbox("Show Application Logs", value=False):
                st.subheader("📋 Recent Logs")
                
                # Log level filter
                log_level = st.selectbox(
                    "Filter by Level",
                    ["All", "INFO", "WARNING", "ERROR"],
                    index=0,
                    key="log_level_filter"
                )
                
                # Get logs
                level_filter = None if log_level == "All" else log_level
                recent_logs = app_logger.get_recent_logs(level=level_filter, count=20)
                
                if recent_logs:
                    for log in reversed(recent_logs):  # Show newest first
                        level_color = {
                            'INFO': '🟢',
                            'WARNING': '🟡', 
                            'ERROR': '🔴',
                            'DEBUG': '🔵'
                        }.get(log['level'], '⚪')
                        
                        st.text(f"{level_color} {log['timestamp']} - {log['message']}")
                else:
                    st.info("No recent logs to display")
    except Exception:
        # Don't let logging errors break the app
        pass




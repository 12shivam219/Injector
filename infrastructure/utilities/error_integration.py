"""
Error integration and monitoring utilities for enhanced error handling.
"""
import streamlit as st
import traceback
import time
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import logging

# Global error tracking
_error_history = []
_performance_metrics = {
    'operations': 0,
    'errors': 0,
    'total_time': 0,
    'average_time': 0
}

class ErrorBoundary:
    """Context manager for error boundaries."""
    
    def __init__(self, operation_name: str = "operation"):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration = end_time - self.start_time
        
        _performance_metrics['operations'] += 1
        _performance_metrics['total_time'] += duration
        _performance_metrics['average_time'] = _performance_metrics['total_time'] / _performance_metrics['operations']
        
        if exc_type is not None:
            _performance_metrics['errors'] += 1
            _error_history.append({
                'timestamp': datetime.now(),
                'operation': self.operation_name,
                'error_type': exc_type.__name__,
                'error_message': str(exc_val),
                'duration': duration,
                'traceback': traceback.format_exc()
            })
            return False  # Don't suppress the exception
        return True

def create_error_boundary(operation_name: str = "operation"):
    """Create an error boundary context manager."""
    return ErrorBoundary(operation_name)

def safe_operation(operation_name: str = "operation"):
    """Decorator for safe operations with error tracking."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with create_error_boundary(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def log_user_action(action: str, details: Dict[str, Any] = None):
    """Log user actions for analytics."""
    if details is None:
        details = {}
    
    # Store in session state for persistence
    if 'user_actions' not in st.session_state:
        st.session_state.user_actions = []
    
    st.session_state.user_actions.append({
        'timestamp': datetime.now(),
        'action': action,
        'details': details
    })
    
    # Keep only last 100 actions
    if len(st.session_state.user_actions) > 100:
        st.session_state.user_actions = st.session_state.user_actions[-100:]

def get_error_summary() -> Dict[str, Any]:
    """Get summary of recent errors."""
    recent_cutoff = datetime.now() - timedelta(hours=1)
    recent_errors = [e for e in _error_history if e['timestamp'] > recent_cutoff]
    
    return {
        'total_errors': len(_error_history),
        'recent_errors': len(recent_errors),
        'error_rate': _performance_metrics['errors'] / max(1, _performance_metrics['operations']),
        'average_operation_time': _performance_metrics['average_time'],
        'last_error': _error_history[-1] if _error_history else None
    }

def clear_error_history():
    """Clear the error history."""
    global _error_history, _performance_metrics
    _error_history.clear()
    _performance_metrics = {
        'operations': 0,
        'errors': 0,
        'total_time': 0,
        'average_time': 0
    }

def display_error_dashboard():
    """Display error dashboard in Streamlit."""
    error_summary = get_error_summary()
    
    st.subheader("🚨 Error Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Errors", error_summary['total_errors'])
    
    with col2:
        st.metric("Recent Errors (1h)", error_summary['recent_errors'])
    
    with col3:
        error_rate_pct = error_summary['error_rate'] * 100
        st.metric("Error Rate", f"{error_rate_pct:.1f}%")
    
    if error_summary['last_error']:
        st.subheader("Last Error")
        error = error_summary['last_error']
        st.error(f"**{error['error_type']}** in {error['operation']}: {error['error_message']}")
        
        with st.expander("Error Details"):
            st.text(f"Timestamp: {error['timestamp']}")
            st.text(f"Duration: {error['duration']:.3f}s")
            st.code(error['traceback'], language='python')

def display_performance_metrics():
    """Display performance metrics in Streamlit."""
    st.subheader("⚡ Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Operations", _performance_metrics['operations'])
    
    with col2:
        avg_time_ms = _performance_metrics['average_time'] * 1000
        st.metric("Avg Operation Time", f"{avg_time_ms:.1f}ms")
    
    # User actions if available
    if 'user_actions' in st.session_state:
        actions = st.session_state.user_actions
        if actions:
            st.subheader("Recent User Actions")
            for action in actions[-5:]:  # Show last 5 actions
                st.text(f"{action['timestamp'].strftime('%H:%M:%S')} - {action['action']}")

# Exception handler for Streamlit
def streamlit_exception_handler(func: Callable):
    """Exception handler specifically for Streamlit operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            
            # Log the error
            _error_history.append({
                'timestamp': datetime.now(),
                'operation': func.__name__,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'duration': 0,
                'traceback': traceback.format_exc()
            })
            
            # Show error details in expander
            with st.expander("Error Details"):
                st.code(traceback.format_exc(), language='python')
            
            return None
    return wrapper

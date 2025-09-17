"""
Enhanced modules for Resume Customizer application.

This package contains all enhanced versions of core functionality
including analytics, monitoring, error handling, and processing enhancements.
"""

# Enhanced modules imports for easier access
try:
    from .metrics_analytics_enhanced import *
    from .health_monitor_enhanced import *
    from .email_templates_enhanced import *
    from .enhanced_error_recovery import *
    from .batch_processor_enhanced import *
    from .progress_tracker_enhanced import *
    from .error_handling_enhanced import *
except ImportError as e:
    # Handle missing dependencies gracefully
    pass

__version__ = "2.1.0"
__author__ = "Resume Customizer Team"




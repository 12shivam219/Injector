"""
Core package for Resume Customizer application.
Provides shared types, constants, configuration, and error handling.
"""

# Import key modules for easy access
from .config import *
from .types import *
from .constants import *
from .errors import *

__version__ = "2.0.0"
__all__ = ["config", "types", "constants", "errors"]
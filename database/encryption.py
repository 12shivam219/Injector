"""
DEPRECATED: This module has been moved to database.utils.encryption
This file exists for backward compatibility and will be removed in a future version.
"""

import warnings
from database.utils.encryption import *

# Issue deprecation warning
warnings.warn(
    "Importing from database.encryption is deprecated. Use database.utils.encryption instead.",
    DeprecationWarning,
    stacklevel=2
)
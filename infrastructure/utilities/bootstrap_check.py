"""
Bootstrap status checker utility
"""

import streamlit as st
from typing import Tuple, Dict, Any

def check_bootstrap_status() -> Tuple[bool, Dict[str, Any]]:
    """
    Check if required services and components are initialized.
    Returns:
        Tuple[bool, Dict[str, Any]]: (is_ready, status_details)
    """
    services = st.session_state.get('services', {})
    
    status = {
        'session_initialized': 'initialized' in st.session_state,
        'services_available': bool(services),
        'async_ready': st.session_state.get('async_initialized', False),
        'ui_components': services.get('ui_components') is not None,
        'resume_processor': services.get('resume_processor') is not None,
        'requirements_manager': services.get('requirements_manager') is not None,
        'analytics': services.get('analytics') is not None
    }
    
    # Required components for basic functionality
    required_components = [
        'session_initialized',
        'services_available',
        'ui_components'
    ]
    
    # Optional components (nice to have but not required for basic functionality)
    optional_components = [
        'async_ready',
        'resume_processor', 
        'requirements_manager',
        'analytics'
    ]
    
    # Check if required components are ready
    required_ready = all(status[comp] for comp in required_components)
    
    # Count optional components that are ready
    optional_ready_count = sum(status[comp] for comp in optional_components)
    
    # Consider bootstrap successful if required components + at least one optional component is ready
    is_ready = required_ready and optional_ready_count >= 1
    
    return is_ready, status

def display_bootstrap_status():
    """Display bootstrap status in the UI."""
    is_ready, status = check_bootstrap_status()
    
    if not is_ready:
        st.error("⚠️ Application not fully initialized")
        st.write("Status:")
        for component, ready in status.items():
            icon = "✅" if ready else "❌"
            st.write(f"{icon} {component.replace('_', ' ').title()}")
    else:
        st.success("✅ Application ready")
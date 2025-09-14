"""
Bootstrap status checker utility
"""

import streamlit as st
from typing import Tuple, Dict, Any

def check_bootstrap_status() -> Tuple[bool, Dict[str, Any]]:
    """
    Check if all required services and components are initialized.
    Returns:
        Tuple[bool, Dict[str, Any]]: (is_ready, status_details)
    """
    status = {
        'session_initialized': 'initialized' in st.session_state,
        'services_available': bool(st.session_state.get('services', {})),
        'async_ready': st.session_state.get('async_initialized', False),
        'ui_components': 'ui_components' in st.session_state.get('services', {}),
        'resume_processor': 'resume_processor' in st.session_state.get('services', {}),
        'requirements_manager': 'requirements_manager' in st.session_state.get('services', {}),
        'analytics': 'analytics' in st.session_state.get('services', {})
    }
    
    is_ready = all(status.values())
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
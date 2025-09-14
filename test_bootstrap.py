"""
Test suite for application bootstrap functionality
"""

import unittest
import streamlit as st
from app_bootstrap import initialize_app, get_cached_services, APP_CONFIG
from infrastructure.utilities.bootstrap_check import check_bootstrap_status

class TestApplicationBootstrap(unittest.TestCase):
    def setUp(self):
        # Reset session state before each test
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def test_app_config(self):
        """Test if APP_CONFIG contains all required keys"""
        required_keys = [
            "title", "layout", "version", "services_enabled",
            "async_enabled", "monitoring_enabled", "debug_mode"
        ]
        for key in required_keys:
            self.assertIn(key, APP_CONFIG)

    def test_service_initialization(self):
        """Test if all required services are initialized"""
        services = get_cached_services()
        required_services = [
            'ui_components',
            'resume_processor',
            'requirements_manager',
            'analytics',
            'bulk_processor'
        ]
        for service in required_services:
            self.assertIn(service, services)

    def test_bootstrap_status(self):
        """Test bootstrap status checker"""
        initialize_app()
        is_ready, status = check_bootstrap_status()
        self.assertTrue(is_ready, f"Bootstrap failed: {status}")
        for component, ready in status.items():
            self.assertTrue(ready, f"Component {component} failed to initialize")

if __name__ == '__main__':
    unittest.main()
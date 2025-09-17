"""
Login Page - User authentication for Resume Customizer
"""

import streamlit as st
from typing import Dict, Any, Optional

# Import the shared bootstrap
try:
    from infrastructure.app.app_bootstrap import initialize_app, get_cached_services
    app_initialized = True
except ImportError:
    app_initialized = False

# Import authentication manager
from infrastructure.security.auth import auth_manager
from infrastructure.monitoring.audit_logger import audit_logger
from infrastructure.utilities.logger import get_logger

logger = get_logger()

def main():
    """Main login page function."""
    
    # Initialize the application
    if app_initialized:
        initialize_app()
    
    # Set page title
    st.title("🔐 User Authentication")
    
    # Check if already logged in
    if st.session_state.get('authenticated', False):
        st.success(f"✅ You are logged in as {st.session_state.get('auth_username', 'User')}")
        
        if st.button("📋 Go to Dashboard"):
            st.switch_page("app.py")
            
        if st.button("🚪 Logout"):
            success, message = auth_manager.logout()
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        
        return
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### 🔑 Login to your account")
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit_login = st.form_submit_button("🔓 Login")
        
        if submit_login:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                success, message = auth_manager.login(username, password)
                if success:
                    st.success(message)
                    # Log successful login
                    audit_logger.log_security_event(
                        "login_success",
                        username,
                        {"source": "login_page"}
                    )
                    # Redirect to main page
                    st.rerun()
                else:
                    st.error(message)
                    # Log failed login attempt
                    audit_logger.log_security_event(
                        "login_failure",
                        username,
                        {"source": "login_page", "reason": message}
                    )
    
    with tab2:
        st.markdown("### 📝 Create a new account")
        
        # Registration form
        with st.form("register_form"):
            new_username = st.text_input("Username", key="register_username")
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            submit_register = st.form_submit_button("✅ Register")
        
        if submit_register:
            if not new_username or not new_email or not new_password or not confirm_password:
                st.error("⚠️ Please fill in all fields")
            elif new_password != confirm_password:
                st.error("⚠️ Passwords do not match")
            else:
                success, message = auth_manager.register_user(new_username, new_password, new_email)
                if success:
                    st.success(message)
                    st.info("Please log in with your new account")
                    # Log successful registration
                    audit_logger.log_security_event(
                        "registration_success",
                        new_username,
                        {"source": "login_page", "email": new_email}
                    )
                else:
                    st.error(message)
                    # Log failed registration
                    audit_logger.log_security_event(
                        "registration_failure",
                        new_username,
                        {"source": "login_page", "reason": message, "email": new_email}
                    )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Resume Customizer - Secure Authentication</p>
        <p>🔒 Your data is encrypted and securely stored</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
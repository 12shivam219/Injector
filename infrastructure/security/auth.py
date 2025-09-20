"""
Authentication module for Resume Customizer application.
Provides user registration, login, and session management.
"""

import streamlit as st
import uuid
import hashlib
import secrets
import datetime
from typing import Dict, Any, Optional, Tuple

from infrastructure.utilities.logger import get_logger
from infrastructure.monitoring.audit_logger import audit_logger
from infrastructure.security.security_enhancements import SecurePasswordManager
from database.models import User
from database.connection import get_db_session

logger = get_logger()
password_manager = SecurePasswordManager()

class AuthenticationManager:
    """Manages user authentication, registration, and session handling."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize authentication-related session state variables."""
        if 'user_id' not in st.session_state:
            st.session_state.user_id = "anonymous"
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'auth_username' not in st.session_state:
            st.session_state.auth_username = None
        if 'auth_expiry' not in st.session_state:
            st.session_state.auth_expiry = None
    
    def register_user(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Args:
            username: Desired username
            password: User password
            email: User email
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if username already exists
            with get_db_session() as session:
                from database.models import User
                existing_user = session.query(User).filter_by(username=username).first()
                if existing_user:
                    return False, "Username already exists"
                
                # Hash the password
                password_hash = password_manager.hash_password(password)
                
                # Create new user
                new_user = User(
                    username=username,
                    password_hash=password_hash,  # Now returns bytes directly
                    email=email,
                    created_at=datetime.datetime.now(),
                    is_active=True
                )
                session.add(new_user)
                session.commit()
                
                # Log the registration
                audit_logger.log_security_event(
                    "user_registration",
                    username,
                    {"email": email}
                )
                
                return True, "Registration successful"
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False, f"Registration failed: {str(e)}"
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                from database.models import User, UserSession
                user = session.query(User).filter_by(username=username, is_active=True).first()
                
                if not user:
                    # Log failed login attempt
                    audit_logger.log_security_event(
                        "failed_login",
                        username,
                        {"reason": "user_not_found"}
                    )
                    return False, "Invalid username or password"
                
                # Verify password
                if not password_manager.verify_password(password, user.password_hash):
                    # Log failed login attempt
                    audit_logger.log_security_event(
                        "failed_login",
                        username,
                        {"reason": "invalid_password"}
                    )
                    return False, "Invalid username or password"
                
                # Generate session
                user_id = str(user.id)
                session_id = str(uuid.uuid4())
                expiry = datetime.datetime.now() + datetime.timedelta(hours=24)
                
                # Store session in database
                user_session = UserSession(
                    session_id=session_id,
                    user_id=user_id,
                    ip_address=self._get_client_ip(),
                    user_agent=self._get_user_agent(),
                    last_activity=datetime.datetime.now(),
                    is_active=True
                )
                session.add(user_session)
                session.commit()
                
                # Update session state
                st.session_state.user_id = user_id
                st.session_state.authenticated = True
                st.session_state.auth_username = username
                st.session_state.auth_expiry = expiry
                st.session_state.session_id = session_id
                
                # Log successful login
                audit_logger.log_security_event(
                    "successful_login",
                    username,
                    {"user_id": user_id}
                )
                
                return True, "Login successful"
        except Exception as e:
            # If this is a connection error, provide a clearer message for UI
            logger.error("Login error encountered", exception=e)
            if 'Database not initialized' in str(e) or 'not initialized' in str(e).lower():
                return False, "Login failed: Database not available. Please check database configuration."
            return False, f"Login failed: {str(e)}"
    
    def logout(self):
        """Log out the current user."""
        try:
            username = st.session_state.get('auth_username', 'anonymous')
            user_id = st.session_state.get('user_id', 'anonymous')
            session_id = st.session_state.get('session_id')
            
            # Update session in database
            if session_id:
                with get_db_session() as session:
                    # Ensure UserSession is available in this scope
                    from database.models import UserSession
                    user_session = session.query(UserSession).filter_by(session_id=session_id).first()
                    if user_session:
                        user_session.is_active = False
                        user_session.ended_at = datetime.datetime.now()
                        session.commit()
            
            # Reset session state
            st.session_state.user_id = "anonymous"
            st.session_state.authenticated = False
            st.session_state.auth_username = None
            st.session_state.auth_expiry = None
            st.session_state.session_id = None
            
            # Log logout
            audit_logger.log_security_event(
                "logout",
                username,
                {"user_id": user_id}
            )
            
            return True, "Logout successful"
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False, f"Logout failed: {str(e)}"
    
    def check_session(self) -> bool:
        """
        Check if the current session is valid.
        
        Returns:
            bool: True if session is valid, False otherwise
        """
        if not st.session_state.get('authenticated', False):
            return False
        
        expiry = st.session_state.get('auth_expiry')
        if not expiry or datetime.datetime.now() > expiry:
            self.logout()
            return False
        
        # Update last activity in database
        session_id = st.session_state.get('session_id')
        if session_id:
            try:
                with get_db_session() as session:
                    user_session = session.query(UserSession).filter_by(session_id=session_id).first()
                    if user_session:
                        user_session.last_activity = datetime.datetime.now()
                        user_session.actions_performed = user_session.actions_performed + 1
                        session.commit()
            except Exception as e:
                logger.error(f"Error updating session activity: {str(e)}")
        
        return True
    
    def require_login(self):
        """
        Require user to be logged in. Redirects to login page if not authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if not self.check_session():
            st.warning("⚠️ Please log in to access this feature")
            return False
        return True
    
    def _get_client_ip(self) -> str:
        """Get client IP address from Streamlit context."""
        # In a real deployment, you would get this from request headers
        return "127.0.0.1"
    
    def _get_user_agent(self) -> str:
        """Get user agent from Streamlit context."""
        # In a real deployment, you would get this from request headers
        return "Streamlit Client"


# Global authentication manager instance
auth_manager = AuthenticationManager()
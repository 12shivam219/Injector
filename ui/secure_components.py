"""
Secure UI components for Resume Customizer application.
Integrates security enhancements with user interface elements.
"""

import streamlit as st
import base64
from typing import Dict, Any, Optional, Tuple
from infrastructure.security.security_enhancements import (
    SecurePasswordManager, 
    InputSanitizer, 
    RateLimiter,
    SessionSecurityManager,
    rate_limit
)
from infrastructure.utilities.logger import get_logger

logger = get_logger()


class SecureUIComponents:
    """UI components with integrated security features."""
    
    def __init__(self):
        self.password_manager = SecurePasswordManager()
        self.sanitizer = InputSanitizer()
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionSecurityManager()

    def render_logout_button(self):
        """Render a logout button in the sidebar with user info."""
        # Only show if user is authenticated
        if st.session_state.get('authenticated', False):
            with st.sidebar:
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"👤 Logged in as: **{st.session_state.get('auth_username', 'User')}**")
                with col2:
                    if st.button("🚪 Logout", key="sidebar_logout"):
                        from infrastructure.security.auth import auth_manager
                        success, message = auth_manager.logout()
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
    
    @rate_limit("file_upload")  # Using configured limits from RateLimiter
    def render_secure_file_upload(self, key: str = "secure_file_upload", allowed_types=None):
        """Render secure file upload with rate limiting and validation."""
        
        # Check session timeout
        if self.session_manager.session_timeout_check():
            st.warning("⚠️ Your session has timed out for security. Please refresh the page.")
            return None
            
        # Get rate limit info for user feedback
        user_id = st.session_state.get('user_id', 'anonymous')
        remaining, time_until_reset = self.rate_limiter.get_remaining_attempts(user_id, "file_upload")
        
        # Get file size limit from config
        size_limit = st.session_state.rate_limit_config.get('file_upload', {}).get('size_limit_mb', 50)
        
        # Default to DOCX if not specified
        if allowed_types is None:
            allowed_types = ["docx", "pdf"]
        
        # Show rate limit status
        if remaining > 0:
            help_text = f"Maximum {remaining} more uploads allowed. Files up to {size_limit}MB each. Formats: {', '.join(allowed_types).upper()}"
        else:
            minutes_left = max(1, time_until_reset // 60)
            help_text = f"⚠️ Upload limit reached. Please wait ~{minutes_left} minutes before uploading more files."
            st.warning(help_text)
        
        # File upload with security checks
        uploaded_files = st.file_uploader(
            "📁 Upload Resume Files",
            type=allowed_types,
            accept_multiple_files=True,
            key=key,
            help=help_text
        )
        
        if uploaded_files:
            # Rate limiting check
            if not self.rate_limiter.check_rate_limit(user_id, "file_upload"):
                st.error("🚫 Upload rate limit exceeded. Please wait before uploading more files.")
                return None
            
            # Validate and sanitize filenames
            secure_files = []
            for file in uploaded_files:
                # Check file size
                file_size_mb = len(file.getvalue()) / (1024 * 1024) if hasattr(file, 'getvalue') else 0
                if not self.rate_limiter.check_size_limit("file_upload", file_size_mb):
                    st.error(f"🚫 File '{file.name}' exceeds the maximum size limit of {size_limit}MB.")
                    continue
                
                sanitized_name = self.sanitizer.sanitize_filename(file.name)
                if sanitized_name != file.name:
                    st.warning(f"⚠️ Filename '{file.name}' was sanitized to '{sanitized_name}'")
                
                # Create a secure file wrapper
                secure_files.append({
                    'file': file,
                    'original_name': file.name,
                    'secure_name': sanitized_name,
                    'size_mb': file_size_mb
                })
            
            # Show remaining uploads after this batch
            remaining, _ = self.rate_limiter.get_remaining_attempts(user_id, "file_upload")
            if remaining <= 3:  # Low on remaining uploads
                st.info(f"ℹ️ You have {remaining} uploads remaining before reaching the rate limit.")
            
            return secure_files
        
        return None
    
    def render_secure_email_form(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Render secure email form with CSRF protection and encryption."""
        
        # Generate CSRF token if not exists
        csrf_key = f"csrf_token_{file_name}"
        if csrf_key not in st.session_state:
            st.session_state[csrf_key] = self.session_manager.generate_csrf_token()
        
        with st.form(f"secure_email_form_{file_name}"):
            st.markdown("#### 📧 Email Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                recipient_email = st.text_input(
                    f"📬 Recipient Email for {file_name}",
                    placeholder="recruiter@company.com",
                    help="Email address where the resume will be sent"
                )
                
                sender_email = st.text_input(
                    f"📤 Sender Email for {file_name}",
                    placeholder="your.email@gmail.com",
                    help="Your email address"
                )
            
            with col2:
                sender_password = st.text_input(
                    f"🔑 Email Password for {file_name}",
                    type="password",
                    placeholder="Use app-specific password",
                    help="For Gmail/Office365, use app-specific passwords"
                )
                
                smtp_server = st.selectbox(
                    f"🌐 SMTP Server for {file_name}",
                    ["smtp.gmail.com", "smtp.office365.com", "smtp.mail.yahoo.com"],
                    help="Email server configuration"
                )
            
            # Email customization
            with st.expander("✉️ Customize Email Content"):
                email_subject = st.text_input(
                    "Subject",
                    value="Resume Application",
                    max_chars=200
                )
                
                email_body = st.text_area(
                    "Message",
                    value="Dear Hiring Manager,\n\nI am pleased to attach my resume for your consideration.\n\nBest regards",
                    height=100,
                    max_chars=2000
                )
            
            # Hidden CSRF token
            csrf_token = st.text_input(
                "", 
                value=st.session_state[csrf_key], 
                type="password", 
                label_visibility="hidden",
                key=f"csrf_{file_name}"
            )
            
            # Security notice
            st.info("🔐 **Security Notice**: Your password is encrypted and never stored. We recommend using app-specific passwords.")
            
            submitted = st.form_submit_button("🚀 Send Secure Email")
            
            if submitted:
                return self._process_secure_email_form(
                    file_name, recipient_email, sender_email, sender_password,
                    smtp_server, email_subject, email_body, csrf_token, csrf_key
                )
        
        return None
    
    def _process_secure_email_form(
        self, file_name: str, recipient_email: str, sender_email: str,
        sender_password: str, smtp_server: str, email_subject: str,
        email_body: str, csrf_token: str, csrf_key: str
    ) -> Optional[Dict[str, Any]]:
        """Process secure email form submission."""
        
        # Validate CSRF token
        expected_token = st.session_state.get(csrf_key)
        if not expected_token or not self.session_manager.validate_csrf_token(csrf_token, expected_token):
            st.error("🚫 Security validation failed. Please refresh and try again.")
            logger.warning(f"CSRF token validation failed for {file_name}")
            return None
        
        # Sanitize all inputs
        clean_recipient = self.sanitizer.sanitize_email(recipient_email)
        clean_sender = self.sanitizer.sanitize_email(sender_email)
        clean_subject = self.sanitizer.sanitize_text_input(email_subject, max_length=200)
        clean_body = self.sanitizer.sanitize_text_input(email_body, max_length=2000)
        
        # Validate inputs
        if not clean_recipient or not clean_sender or not sender_password:
            st.error("❌ Please fill in all required email fields")
            return None
        
        # Basic email validation
        if '@' not in clean_recipient or '@' not in clean_sender:
            st.error("❌ Please enter valid email addresses")
            return None
        
        # Encrypt password for temporary storage
        try:
            encrypted_password = self.password_manager.encrypt_password(sender_password)
            encrypted_password_b64 = base64.b64encode(encrypted_password).decode('utf-8')
        except Exception as e:
            st.error("❌ Failed to secure password. Please try again.")
            logger.error(f"Password encryption failed: {e}")
            return None
        
        # Generate new CSRF token for next use
        st.session_state[csrf_key] = self.session_manager.generate_csrf_token()
        
        # Return sanitized and secured data
        return {
            'recipient_email': clean_recipient,
            'sender_email': clean_sender,
            'encrypted_password': encrypted_password_b64,
            'smtp_server': smtp_server,
            'smtp_port': 465 if smtp_server == "smtp.gmail.com" else 587,
            'email_subject': clean_subject,
            'email_body': clean_body,
            'security_validated': True
        }
    
    def render_secure_text_input(
        self, label: str, file_name: str, 
        placeholder: str = "", max_length: int = 10000
    ) -> Optional[str]:
        """Render secure text input with sanitization."""
        
        raw_input = st.text_area(
            label,
            placeholder=placeholder,
            height=200,
            max_chars=max_length,
            key=f"secure_text_{file_name}",
            help=f"Maximum {max_length} characters. Content will be sanitized for security."
        )
        
        if raw_input:
            # Sanitize input
            sanitized_input = self.sanitizer.sanitize_text_input(raw_input, max_length)
            
            if len(sanitized_input) != len(raw_input):
                st.info(f"ℹ️ Input was sanitized for security ({len(raw_input) - len(sanitized_input)} characters removed)")
            
            return sanitized_input
        
        return None
    
    def display_security_status(self):
        """Display current security status and recommendations."""
        
        with st.sidebar:
            st.markdown("### 🔐 Security Status")
            
            # Session security
            if 'user_id' in st.session_state:
                st.success("✅ Session secured")
            else:
                st.warning("⚠️ Session not initialized")
            
            # Rate limiting status
            user_id = st.session_state.get('user_id', 'anonymous')
            rate_limits = st.session_state.get('rate_limits', {})
            
            if rate_limits:
                active_limits = len([k for k in rate_limits.keys() if user_id in k])
                if active_limits > 0:
                    st.info(f"ℹ️ {active_limits} rate limits active")
                else:
                    st.success("✅ No rate limits active")
            
            # Security recommendations
            with st.expander("🛡️ Security Tips"):
                st.markdown("""
                - Use app-specific passwords for email
                - Keep your browser updated
                - Don't share your session with others
                - Log out when finished
                - Report suspicious activity
                """)
    
    def render_security_metrics(self):
        """Render security metrics for admin users."""
        
        if st.session_state.get('user_role') == 'admin':
            st.subheader("🔒 Security Metrics")
            
            rate_limits = st.session_state.get('rate_limits', {})
            
            if rate_limits:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Active Rate Limits", len(rate_limits))
                
                with col2:
                    total_requests = sum(len(timestamps) for timestamps in rate_limits.values())
                    st.metric("Total Requests", total_requests)
                
                with col3:
                    blocked_requests = sum(
                        1 for timestamps in rate_limits.values() 
                        if len(timestamps) >= 10  # Assuming 10 is a common limit
                    )
                    st.metric("Blocked Requests", blocked_requests)
                
                # Rate limit details
                if st.checkbox("Show Rate Limit Details", key="show_rate_limit_details"):
                    for limit_key, timestamps in rate_limits.items():
                        if len(timestamps) > 0:
                            st.write(f"**{limit_key}**: {len(timestamps)} requests")


# Global instance
_secure_ui_components = None

def get_secure_ui_components() -> SecureUIComponents:
    """Get singleton secure UI components instance."""
    global _secure_ui_components
    if _secure_ui_components is None:
        _secure_ui_components = SecureUIComponents()
    return _secure_ui_components




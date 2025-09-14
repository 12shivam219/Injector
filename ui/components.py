import streamlit as st
import time
from typing import List, Dict, Any, Optional
from database.config import get_smtp_servers, get_default_email_subject, get_default_email_body
from infrastructure.security.validators import get_file_validator, EmailValidator, TextValidator
from resume_customizer.parsers.text_parser import LegacyParser
from infrastructure.utilities.logger import get_logger
from infrastructure.security.security_enhancements import SecurePasswordManager, InputSanitizer, rate_limit

# Try to import enhanced error handling
try:
    from infrastructure.utilities.error_integration import (
        safe_operation, log_user_action, create_error_boundary
    )
    ENHANCED_UI_AVAILABLE = True
except ImportError:
    ENHANCED_UI_AVAILABLE = False

file_validator = get_file_validator()
logger = get_logger()

class UIComponents:
    """Handles UI component rendering and interactions with enhanced UX."""
    
    def render_sidebar(self):
        """Render the sidebar components."""
        with st.sidebar:
            st.markdown("### 🛠️ Quick Actions")
            
            # Settings section
            st.markdown("#### ⚙️ Settings")
            theme = st.selectbox(
                "🎨 Theme:",
                ["Light", "Dark"],
                key="theme_selector",
                help="Choose the application theme"
            )
            
            # Performance options
            st.markdown("#### 🚀 Performance")
            st.checkbox(
                "Enable async processing",
                value=st.session_state.get('async_initialized', False),
                key="async_enabled",
                help="Enable asynchronous file processing"
            )
            
            # Display options
            st.markdown("#### 👁️ Display")
            st.checkbox(
                "Show debug info",
                value=st.session_state.get('show_debug', False),
                key="show_debug",
                help="Show additional debugging information"
            )
            
            # Help section
            st.markdown("#### ℹ️ Help")
            if st.button("📚 View Documentation"):
                st.session_state.current_page = "guide"
                st.rerun()
    
    def render_file_upload(self, key: str, allowed_types: Optional[List[str]] = None) -> List[Any]:
        """Render a file upload component with improved UX."""
        if allowed_types is None:
            allowed_types = ['docx']
            
        help_text = f"Allowed file types: {', '.join(allowed_types)}"
        file_types = [f".{ext}" for ext in allowed_types]
        
        uploaded_files = st.file_uploader(
            "Choose resume file(s)",
            type=file_types,
            accept_multiple_files=True,
            help=help_text,
            key=key
        )
        
        # Show upload status
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
            
            # Show file details
            for file in uploaded_files:
                st.info(f"📄 {file.name} ({file.size} bytes)")
        
        return uploaded_files or []
    
    @staticmethod
    @st.cache_data
    def get_sidebar_config():
        """Get cached sidebar configuration."""
        return {
            "quick_actions": [
                {"icon": "🧹", "label": "Clear Cache", "help": "Clear application cache"}
            ]
        }
    
    @staticmethod
    def render_enhanced_sidebar():
        """Enhanced sidebar with optimized performance."""
        with st.sidebar:
            # Simplified header for faster rendering
            st.markdown("### 🚀 System Status")
            
            with st.container():
                st.metric("⚡", "Active")
            
            st.markdown("---")
            
            # Simplified quick actions
            st.markdown("### ⚡ Quick Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Session", help="Reset session data", use_container_width=True):
                    # Fast session clear
                    keys_to_delete = [k for k in st.session_state.keys() if not k.startswith('_')]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.toast("Session cleared!", icon="✅")
                    st.rerun()
            
            with col2:
                if st.button("🧹 Clear Cache", help="Clear cache", use_container_width=True):
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.toast("Cache cleared!", icon="✅")
                    st.rerun()
    
    @staticmethod
    def render_sidebar():
        """Backward compatible sidebar renderer."""
        UIComponents.render_enhanced_sidebar()

    @staticmethod
    def render_gdrive_picker(key="gdrive_picker_customizer"):
        """Render Google Drive picker UI and return selected files."""
        from ui.gdrive_picker import gdrive_picker_ui
        st.markdown("---")
        st.markdown("### 📁 Google Drive File Picker")
        results = gdrive_picker_ui()
        # Return list of (filename, BytesIO) tuples
        return results

    @staticmethod
    def render_file_upload_with_progress(key="file_upload"):
        """Enhanced file upload with progress indicators and better feedback."""
        # Enhanced file upload with drag and drop styling
        st.markdown("""
        <style>
        .uploadedFile {
            background-color: #f0f2f6;
            border: 2px dashed #cccccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin: 10px 0;
        }
        .file-upload-success {
            background: linear-gradient(90deg, #4CAF50, #45a049);
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "📁 Drop your resume files here or click to browse",
            type=["docx"],
            accept_multiple_files=True,
            key=key,
            help="Upload one or more .docx resume files. Maximum 50MB per file."
        )
        
        if uploaded_files:
            # Show upload progress
            progress_container = st.container()
            with progress_container:
                st.markdown("### 📊 Processing Files...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Validate files with progress (removed artificial delay)
                for i, file in enumerate(uploaded_files):
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Validating {file.name}... ({i+1}/{len(uploaded_files)})")
                
                # Perform actual validation
                validation_result = file_validator.validate_batch(uploaded_files)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Protect against None validation result
                if validation_result is None:
                    st.error("🚨 File validation failed - validator returned no result")
                    return None
                
                # Show results with enhanced styling
                if not validation_result.get('valid', False):
                    st.error("🚫 File Validation Issues")
                    with st.expander("📋 See Details", expanded=True):
                        for error in validation_result['summary']['errors']:
                            st.error(f"❌ {error}")
                    return None
                
                # Show warnings if any
                if validation_result.get('summary', {}).get('warnings'):
                    with st.expander("⚠️ Warnings", expanded=False):
                        for warning in validation_result['summary']['warnings']:
                            st.warning(f"⚠️ {warning}")
                
                # Success message with metrics
                summary = validation_result.get('summary', {})
                if summary.get('valid_files', 0) > 0:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Valid Files", summary.get('valid_files', 0))
                    with col2:
                        st.metric("📁 Total Size", f"{summary.get('total_size_mb', 0):.1f}MB")
                    with col3:
                        st.metric("⚡ Status", "Ready")
                    
                    # Log the action if enhanced logging is available
                    if ENHANCED_UI_AVAILABLE:
                        log_user_action("file_upload", {
                            "files_count": summary.get('valid_files', 0), 
                            "total_size_mb": summary.get('total_size_mb', 0)
                        })
                    
                    # Success notification (removed balloon animation for better performance)
        
        return uploaded_files
    
    @staticmethod
    def render_file_upload(key="file_upload"):
        """Backward compatible file upload renderer."""
        return UIComponents.render_file_upload_with_progress(key)

    @staticmethod
    def render_example_format():
        """Render the example format section."""
        with st.expander("💡 Example Input Format"):
            st.code(UI_CONFIG["example_format"])

    @staticmethod
    def render_email_fields(file_name):
        """Render email configuration fields for a file with validation."""
        col1, col2 = st.columns(2)
        
        with col1:
            email_to = st.text_input(f"Recipient email for {file_name}", key=f"to_{file_name}")
            if email_to:
                validation = EmailValidator.validate_email(email_to)
                if validation and not validation.get('valid', True):
                    st.error(f"Invalid recipient email: {', '.join(validation.get('errors', ['Validation failed']))}")
            
            sender_email = st.text_input(f"Sender email for {file_name}", key=f"from_{file_name}")
            if sender_email:
                validation = EmailValidator.validate_email(sender_email)
                if validation and not validation.get('valid', True):
                    st.error(f"Invalid sender email: {', '.join(validation.get('errors', ['Validation failed']))}")
        
        with col2:
            sender_password = st.text_input(
                f"Sender email password for {file_name}", 
                type="password",
                help="For Gmail, use an app-specific password",
                key=f"pwd_{file_name}"
            )
            smtp_server = st.selectbox(
                f"SMTP Server for {file_name}",
                get_smtp_servers(),
                key=f"smtp_{file_name}"
            )
            smtp_port = st.number_input(
                f"SMTP Port for {file_name}",
                value=465,
                min_value=1,
                max_value=65535,
                key=f"port_{file_name}"
            )
        
        return email_to, sender_email, sender_password, smtp_server, smtp_port

    @staticmethod
    def render_email_customization(file_name):
        """Render email customization fields."""
        st.markdown("#### 📧 Email Customization (Optional)")
        
        email_subject = st.text_input(
            f"Email Subject for {file_name}",
            value=get_default_email_subject(),
            help="Customize the email subject line",
            key=f"subject_{file_name}"
        )
        
        email_body = st.text_area(
            f"Email Body for {file_name}",
            value=get_default_email_body(),
            height=120,
            help="Customize the email message content",
            key=f"body_{file_name}"
        )
        
        return email_subject, email_body

    @staticmethod
    def render_manual_points_editor(file_name, user_input):
        """Render the manual points editor section."""
        with st.expander("✏️ Optional: Edit points before preview", expanded=False):
            edit_enable_key = f"edit_points_enable_{file_name}"
            edit_text_key = f"edit_points_text_{file_name}"
            
            edit_points_enabled = st.checkbox(
                "Enable manual edit of points (one point per line)",
                key=edit_enable_key
            )
            
            if edit_points_enabled:
                if edit_text_key not in st.session_state:
                    legacy_parser = LegacyParser()
                    default_points, _ = legacy_parser.extract_points_from_legacy_format(user_input or "")
                    st.session_state[edit_text_key] = "\n".join(default_points)
                
                st.text_area(
                    "Points to add (one per line)",
                    key=edit_text_key,
                    height=200,
                    help="These points will be used instead of the auto-parsed ones when previewing or generating."
                )
                
                if st.button("Reset edited points to parsed defaults", key=f"reset_points_{file_name}"):
                    legacy_parser = LegacyParser()
                    default_points, _ = legacy_parser.extract_points_from_legacy_format(user_input or "")
                    st.session_state[edit_text_key] = "\n".join(default_points)
                    st.success("✅ Points reset to parsed defaults.")
                    st.rerun()
        
        return edit_points_enabled

    @staticmethod
    def render_bulk_settings(num_files):
        """Render bulk processing settings."""
        with st.expander("⚡ Bulk Mode Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                max_workers = st.slider(
                    "🔄 Parallel Workers (Higher = Faster)",
                    min_value=2,
                    max_value=min(8, num_files),
                    value=min(4, num_files),
                    help="Number of parallel processes. More workers = faster processing but higher CPU usage"
                )
                
                bulk_email_mode = st.selectbox(
                    "📧 Email Sending Mode",
                    ["Send emails in parallel", "Process resumes only (no emails)", "Download all as ZIP"],
                    help="Choose how to handle email sending for optimal speed"
                )
            
            with col2:
                show_progress = st.checkbox(
                    "📊 Show Real-time Progress",
                    value=True,
                    help="Display progress updates (may slow down slightly)"
                )
        
        return max_workers, bulk_email_mode, show_progress, False
    
    @staticmethod
    def render_processing_status(operation_name: str, current_step: str, progress: float = None):
        """Render a processing status component with progress."""
        status_container = st.container()
        
        with status_container:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**🔄 {operation_name}**")
                st.text(current_step)
            
            with col2:
                if progress is not None:
                    st.metric("Progress", f"{progress:.0%}")
            
            if progress is not None:
                st.progress(progress)
    
    @staticmethod
    def render_success_message(title: str, details: Dict[str, Any] = None):
        """Render an enhanced success message with details."""
        st.success(f"✅ {title}")
        
        if details:
            with st.expander("📋 Details", expanded=False):
                for key, value in details.items():
                    st.write(f"**{key}:** {value}")
    
    @staticmethod
    def render_error_message(title: str, error: str, suggestions: List[str] = None):
        """Render an enhanced error message with suggestions."""
        st.error(f"🚨 {title}")
        
        with st.expander("🔍 Error Details", expanded=True):
            st.write(f"**Error:** {error}")
            
            if suggestions:
                st.write("**💡 Suggestions:**")
                for i, suggestion in enumerate(suggestions, 1):
                    st.write(f"{i}. {suggestion}")
    
    @staticmethod
    def render_operation_timer():
        """Render a timer component for long-running operations."""
        if 'operation_start_time' not in st.session_state:
            st.session_state.operation_start_time = time.time()
        
        elapsed = time.time() - st.session_state.operation_start_time
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("⏱️ Elapsed Time", f"{elapsed:.1f}s")
        with col2:
            if elapsed > 10:
                st.warning("Operation taking longer than expected...")
            else:
                st.info("Processing...")
    
    @staticmethod
    def render_enhanced_metrics_panel():
        """Render enhanced metrics and performance panel."""
        if ENHANCED_UI_AVAILABLE:
            display_performance_metrics()
        else:
            # Fallback simple metrics
            if 'session_metrics' not in st.session_state:
                st.session_state.session_metrics = {
                    'files_processed': 0,
                    'operations_completed': 0,
                    'session_start': time.time()
                }
            
            metrics = st.session_state.session_metrics
            session_time = time.time() - metrics['session_start']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Files Processed", metrics['files_processed'])
            with col2:
                st.metric("Operations", metrics['operations_completed'])
            with col3:
                st.metric("Session Time", f"{session_time/60:.1f}m")


def create_loading_spinner(message: str = "Processing..."):
    """Create a context manager for loading spinners."""
    return st.spinner(message)


def show_toast_message(message: str, message_type: str = "success"):
    """Show a toast-style message (using Streamlit's built-in methods)."""
    if message_type == "success":
        st.success(message)
        # Removed balloon animation for better performance
    elif message_type == "error":
        st.error(message)
    elif message_type == "warning":
        st.warning(message)
    else:
        st.info(message)


def create_collapsible_section(title: str, content_func, expanded: bool = False):
    """Create a collapsible section with custom content."""
    with st.expander(title, expanded=expanded):
        content_func()


def admin_resource_panel():
    """Display real-time resource stats for admins."""
    from resource_monitor import get_resource_stats
    st.markdown("## 🖥️ Resource Monitor")
    try:
        stats = get_resource_stats()
        st.metric("CPU Usage (%)", stats['cpu_percent'])
        st.metric("Memory Usage (%)", stats['mem_percent'])
        st.metric("Celery Queue Length", stats['celery_queue_length'])
        if stats['cpu_percent'] > 85 or stats['mem_percent'] > 90:
            st.error("⚠️ High resource usage! Consider scaling up workers or hardware.")
    except Exception as e:
        st.error(f"Failed to load resource stats: {e}")




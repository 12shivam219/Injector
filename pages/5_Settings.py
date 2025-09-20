"""
Settings Page - Application configuration and preferences
"""

import streamlit as st
import json
from typing import Dict, Any
import os
import time

# Import the shared bootstrap
try:
    from infrastructure.app.app_bootstrap import initialize_app, get_cached_services, check_feature_availability, APP_CONFIG
    app_initialized = True
except ImportError:
    app_initialized = False

if app_initialized:
    # Initialize the application
    initialize_app()
    services = get_cached_services()
    features = check_feature_availability()
    
    # Add logout button
    from ui.secure_components import SecureUIComponents
    secure_ui = SecureUIComponents()
    secure_ui.render_logout_button()
    
    # Set page title
    st.title("⚙️ Settings")
    st.markdown("🔧 **Configure application preferences and system settings**")
    
    # Settings tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎨 UI Preferences", "⚡ Performance", "🔒 Security", "📊 System Info"])
    
    with tab1:
        st.markdown("### 🎨 User Interface Preferences")
        
        # UI preferences from session state
        ui_prefs = st.session_state.get('ui_preferences', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Theme selection
            theme = st.selectbox(
                "🌓 Theme",
                ["light", "dark", "auto"],
                index=["light", "dark", "auto"].index(ui_prefs.get('theme', 'light')),
                help="Choose your preferred color theme"
            )
            ui_prefs['theme'] = theme
            
            # Debug mode
            show_debug = st.checkbox(
                "🐛 Show Debug Information",
                value=ui_prefs.get('show_debug', False),
                key="settings_show_debug",
                help="Display additional debug information in the interface"
            )
            ui_prefs['show_debug'] = show_debug
            
            # Auto-save
            auto_save = st.checkbox(
                "💾 Auto-save Form Data",
                value=ui_prefs.get('auto_save', True),
                key="settings_auto_save",
                help="Automatically save form data as you type"
            )
            ui_prefs['auto_save'] = auto_save
        
        with col2:
            # File upload preferences
            max_files = st.number_input(
                "📁 Max Files per Upload",
                min_value=1,
                max_value=20,
                value=ui_prefs.get('max_files', 5),
                help="Maximum number of files to upload at once"
            )
            ui_prefs['max_files'] = max_files
            
            # Progress display
            show_progress = st.checkbox(
                "📊 Show Detailed Progress",
                value=ui_prefs.get('show_progress', True),
                key="settings_show_progress",
                help="Display detailed progress information during processing"
            )
            ui_prefs['show_progress'] = show_progress
            
            # Email notifications
            email_notifications = st.checkbox(
                "📧 Email Notifications",
                value=ui_prefs.get('email_notifications', True),
                key="settings_email_notifications",
                help="Receive email notifications for completed operations"
            )
            ui_prefs['email_notifications'] = email_notifications
        
        # Save preferences
        if st.button("💾 Save UI Preferences", key="save_ui_prefs"):
            st.session_state.ui_preferences = ui_prefs
            st.success("✅ UI preferences saved successfully!")
            st.balloons()
    
    with tab2:
        st.markdown("### ⚡ Performance Settings")
        
        # Performance configuration
        perf_settings = st.session_state.get('performance_settings', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Async processing
            if features.get('async_processing', False):
                use_async = st.checkbox(
                    "⚡ Enable Async Processing",
                    value=perf_settings.get('use_async', True),
                    key="settings_use_async",
                    help="Use asynchronous processing for better performance"
                )
                perf_settings['use_async'] = use_async
                
                if use_async:
                    max_workers = st.slider(
                        "👥 Max Parallel Workers",
                        min_value=1,
                        max_value=8,
                        value=perf_settings.get('max_workers', 3),
                        help="Number of parallel workers for processing"
                    )
                    perf_settings['max_workers'] = max_workers
            else:
                st.warning("⚠️ Async processing not available")
            
            # Caching settings
            enable_cache = st.checkbox(
                "💾 Enable Caching",
                value=perf_settings.get('enable_cache', True),
                key="settings_enable_cache",
                help="Cache processed data for faster subsequent operations"
            )
            perf_settings['enable_cache'] = enable_cache
        
        with col2:
            # Memory management
            memory_optimization = st.checkbox(
                "🧹 Memory Optimization",
                value=perf_settings.get('memory_optimization', True),
                key="settings_memory_optimization",
                help="Automatically clean up memory during processing"
            )
            perf_settings['memory_optimization'] = memory_optimization
            
            # Batch size
            batch_size = st.number_input(
                "📦 Processing Batch Size",
                min_value=1,
                max_value=20,
                value=perf_settings.get('batch_size', 5),
                help="Number of items to process in each batch"
            )
            perf_settings['batch_size'] = batch_size
            
            # Timeout settings
            timeout_seconds = st.number_input(
                "⏱️ Operation Timeout (seconds)",
                min_value=30,
                max_value=600,
                value=perf_settings.get('timeout_seconds', 300),
                help="Maximum time to wait for operations to complete"
            )
            perf_settings['timeout_seconds'] = timeout_seconds
        
        # Current performance metrics
        st.markdown("---")
        st.markdown("### 📊 Current Performance Status")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            async_status = "✅ Available" if st.session_state.get('async_initialized') else "❌ Unavailable"
            st.metric("Async Processing", async_status)
        with col2:
            memory_status = "🧹 Optimized" if memory_optimization else "📈 Standard"
            st.metric("Memory Mode", memory_status)
        with col3:
            cache_status = "💾 Enabled" if enable_cache else "🚫 Disabled"
            st.metric("Caching", cache_status)
        
        if st.button("💾 Save Performance Settings", key="save_perf_settings"):
            st.session_state.performance_settings = perf_settings
            st.success("✅ Performance settings saved successfully!")
    
    with tab3:
        st.markdown("### 🔒 Security Settings")
        
        # Security configuration
        security_settings = st.session_state.get('security_settings', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Rate limiting
            rate_limiting = st.checkbox(
                "🛡️ Enable Rate Limiting",
                value=security_settings.get('rate_limiting', True),
                key="settings_rate_limiting",
                help="Limit the number of requests per time window"
            )
            security_settings['rate_limiting'] = rate_limiting
            
            if rate_limiting:
                rate_limit_requests = st.number_input(
                    "📊 Max Requests per Minute",
                    min_value=1,
                    max_value=100,
                    value=security_settings.get('rate_limit_requests', 20),
                    help="Maximum number of requests allowed per minute"
                )
                security_settings['rate_limit_requests'] = rate_limit_requests
            
            # Input validation
            strict_validation = st.checkbox(
                "✅ Strict Input Validation",
                value=security_settings.get('strict_validation', True),
                key="settings_strict_validation",
                help="Enable strict validation of all user inputs"
            )
            security_settings['strict_validation'] = strict_validation
        
        with col2:
            # Session security
            session_timeout = st.number_input(
                "⏰ Session Timeout (minutes)",
                min_value=5,
                max_value=480,
                value=security_settings.get('session_timeout', 60),
                help="Time before user sessions expire"
            )
            security_settings['session_timeout'] = session_timeout
            
            # File security
            scan_uploads = st.checkbox(
                "🔍 Scan File Uploads",
                value=security_settings.get('scan_uploads', True),
                key="settings_scan_uploads",
                help="Scan uploaded files for security threats"
            )
            security_settings['scan_uploads'] = scan_uploads
            
            # Password security
            require_strong_passwords = st.checkbox(
                "🔐 Require Strong Passwords",
                value=security_settings.get('require_strong_passwords', True),
                key="settings_require_strong_passwords",
                help="Enforce strong password requirements for email accounts"
            )
            security_settings['require_strong_passwords'] = require_strong_passwords
        
        # Security status display
        if st.session_state.get('user_id'):
            st.success(f"🔐 Session secured for user: {st.session_state.user_id[:8]}...")
        
        if st.button("💾 Save Security Settings", key="save_security_settings"):
            st.session_state.security_settings = security_settings
            st.success("✅ Security settings saved successfully!")
    
    with tab4:
        st.markdown("### 📊 System Information")
        
        # Application info
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📱 Application Information**")
            st.info(f"""
            **Name:** {APP_CONFIG.get('title', 'Resume Customizer')}
            **Version:** {APP_CONFIG.get('version', '2.0.0')}
            **Layout:** {APP_CONFIG.get('layout', 'wide')}
            """)
            
            st.markdown("**🔧 Feature Availability**")
            for feature, available in features.items():
                status = "✅" if available else "❌"
                st.write(f"{status} {feature.replace('_', ' ').title()}")
        
        with col2:
            st.markdown("**💾 Session Information**")
            session_info = {
                "User ID": st.session_state.get('user_id', 'Not set')[:12] + "...",
                "Async Initialized": "✅" if st.session_state.get('async_initialized') else "❌",
                "Uploaded Files": len(st.session_state.get('uploaded_files', [])),
                "Resume Inputs": len(st.session_state.get('resume_inputs', {})),
            }
            
            for key, value in session_info.items():
                st.write(f"**{key}:** {value}")
        
        # Export/Import settings
        st.markdown("---")
        st.markdown("### 🔄 Settings Backup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export Settings", key="export_settings"):
                settings_data = {
                    'ui_preferences': st.session_state.get('ui_preferences', {}),
                    'performance_settings': st.session_state.get('performance_settings', {}),
                    'security_settings': st.session_state.get('security_settings', {}),
                }
                
                settings_json = json.dumps(settings_data, indent=2)
                st.download_button(
                    "💾 Download Settings File",
                    data=settings_json,
                    file_name="resume_customizer_settings.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_settings = st.file_uploader(
                "📤 Import Settings",
                type=["json"],
                help="Upload a previously exported settings file"
            )
            
            if uploaded_settings:
                try:
                    settings_data = json.loads(uploaded_settings.read().decode())
                    
                    if st.button("✅ Apply Imported Settings", key="apply_settings"):
                        st.session_state.ui_preferences = settings_data.get('ui_preferences', {})
                        st.session_state.performance_settings = settings_data.get('performance_settings', {})
                        st.session_state.security_settings = settings_data.get('security_settings', {})
                        
                        st.success("✅ Settings imported successfully!")
                        st.balloons()
                except Exception as e:
                    st.error(f"❌ Error importing settings: {str(e)}")

        # Database configuration quick panel
        st.markdown("---")
        st.markdown("### 🗄️ Database Configuration")
        current_db_url = os.getenv('DATABASE_URL', '')
        db_input = st.text_input(
            "DATABASE_URL",
            value=current_db_url,
            placeholder="postgresql://user:password@host:5432/dbname",
            help="Full SQLAlchemy-style DATABASE_URL (e.g. postgresql://user:pass@host:5432/db)"
        )

        col_test, col_save = st.columns(2)
        with col_test:
            if st.button("🔎 Test Connection", key="test_db_conn"):
                if not db_input:
                    st.error("Please enter a DATABASE_URL to test")
                else:
                    try:
                        from database.connection import DatabaseConnectionManager
                        dbm = DatabaseConnectionManager()
                        ok = dbm.initialize(database_url=db_input)
                        if ok:
                            st.success("✅ Connection test succeeded")
                        else:
                            st.error("❌ Connection test failed — check credentials and network access")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")

        with col_save:
            if st.button("💾 Test & Save to .env", key="save_db_conn"):
                if not db_input:
                    st.error("Please enter a DATABASE_URL before saving")
                else:
                    try:
                        from database.connection import DatabaseConnectionManager
                        dbm = DatabaseConnectionManager()
                        ok = dbm.initialize(database_url=db_input)
                        if ok:
                            # Persist to .env
                            try:
                                with open('.env', 'w', encoding='utf-8') as f:
                                    f.write(f"DATABASE_URL={db_input}\n")
                                st.success("✅ DATABASE_URL saved to .env")
                                # Attempt to rerun the Streamlit script if API is available.
                                rerun = getattr(st, "experimental_rerun", None)
                                if callable(rerun):
                                    try:
                                        rerun()
                                    except Exception:
                                        st.info("Please restart the Streamlit app to apply changes.")
                                else:
                                    st.info("Please restart the Streamlit app to apply changes.")
                                    st.code('.\\.venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8501', language='powershell')
                            except Exception as e:
                                st.error(f"❌ Could not write .env: {e}")
                        else:
                            st.error("❌ Connection test failed — not saving .env")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")

else:
    # Fallback display when bootstrap not available
    st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")
    st.info("📝 This page requires the main application to be properly configured.")
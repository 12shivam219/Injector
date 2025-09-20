"""
Resume Customizer - Main Landing Page
Modern Streamlit multi-page application for resume customization
"""

import streamlit as st

# Import the shared bootstrap and cloud config
from infrastructure.app.app_bootstrap import initialize_app, get_cached_services, APP_CONFIG
from infrastructure.app.streamlit_config import setup_streamlit_env

# Set up Streamlit environment for cloud deployment
setup_streamlit_env()

# Startup key sanity check: ensure encryption keys are present in production
import os
def _check_encryption_keys():
    env_mode = os.getenv('ENV', os.getenv('ENVIRONMENT', 'development')).lower()
    missing = [k for k in ('DB_ENCRYPTION_KEY', 'USER_DATA_ENCRYPTION_KEY') if not os.getenv(k)]
    if missing:
        if env_mode in ('dev', 'development', ''):
            # In development warn but continue
            import streamlit as _st
            _st.warning(f"Missing encryption keys: {', '.join(missing)} — generated temporary keys will be used. Set environment variables for production.")
        else:
            import streamlit as _st
            _st.error(f"Missing required encryption keys: {', '.join(missing)}. Set these in your environment before starting the app.")
            raise SystemExit(1)

_check_encryption_keys()

def main():
    """Main application entry point."""
    
    # Initialize the application
    initialize_app()

    # Perform a startup health check (database availability, etc.) and fail fast
    from infrastructure.app.app_bootstrap import perform_startup_health_check, get_cached_services
    services = get_cached_services()
    if not perform_startup_health_check(services):
        st.error("Critical: Database health check failed on startup. Check your DATABASE_URL and database accessibility.")
        st.stop()
    
    # Welcome page content
    st.title("📝 Resume Customizer")
    st.markdown(f"### 🎯 **Welcome to Resume Customizer v{APP_CONFIG['version']}**")
    
    # Check if formats exist
    from database.models import ResumeFormat
    from database.session import get_session
    
    try:
        with get_session() as session:
            formats_exist = session.query(ResumeFormat).first() is not None
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        formats_exist = False
        
        if not formats_exist:
            st.warning("""
            ⚠️ **Important:** No resume formats are configured yet. 
            Please go to the **Format Manager** tab first to upload some resume formats.
            This helps the system better understand and process your resumes.
            """)
            
            if st.button("🔄 Go to Format Manager"):
                st.switch_page("pages/0_Format_Manager.py")
    
    st.markdown("""
    **Transform your resume with AI-powered customization!**
    
    This application helps you tailor your resume for specific job requirements by intelligently 
    distributing tech stack points across your projects and experiences.
    """)
    
    # Feature highlights
    st.markdown("---")
    st.markdown("## ✨ Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📄 Smart Resume Processing**
        - Upload DOCX resume files
        - Format pattern matching
        - Intelligent point distribution
        - Preserve original formatting
        """)
    
    with col2:
        st.markdown("""
        **⚡ Bulk Operations**
        - Process multiple resumes
        - Parallel processing support
        - Batch email sending
        - Real-time progress tracking
        """)
    
    with col3:
        st.markdown("""
        **📋 Requirements Management**
        - Store job requirements
        - Match skills to positions
        - Database-backed storage
        - Reusable configurations
        """)
    
    # Quick start guide
    st.markdown("---")
    st.markdown("## 🚀 Quick Start")
    
    st.info("""
    **Ready to get started?** Use the navigation in the sidebar to access different features:
    
    1. **📄 Resume Customizer** - Upload and customize individual resumes
    2. **📤 Bulk Processor** - Process multiple resumes at once  
    3. **📋 Requirements** - Manage job requirements and customize for specific positions
    4. **📚 App Guide** - Complete documentation and help
    5. **⚙️ Settings** - Configure preferences and performance options
    """)
    
    # Action buttons
    st.markdown("---")
    st.markdown("## 🎯 Get Started")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Start Customizing", key="start_customizing", type="primary"):
            st.switch_page("pages/0_Format_Manager.py")
    
    with col2:
        if st.button("📋 Manage Requirements", key="manage_requirements"):
            st.switch_page("pages/3_Requirements.py")
    
    with col3:
        if st.button("📚 View Guide", key="view_guide"):
            st.switch_page("pages/4_App_Guide.py")
    
    # Status and information
    st.markdown("---")
    st.markdown("## 📊 System Status")
    
    # Get services to check availability
    services = get_cached_services()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ui_status = "✅ Available" if services.get('ui_components') else "❌ Unavailable"
        st.metric("UI Components", ui_status)
    
    with col2:
        processor_status = "✅ Available" if services.get('resume_tab_handler') else "❌ Unavailable"
        st.metric("Resume Processor", processor_status)
    
    with col3:
        bulk_status = "✅ Available" if services.get('bulk_processor') else "❌ Unavailable"
        st.metric("Bulk Processor", bulk_status)
    
    with col4:
        requirements_status = "✅ Available" if services.get('requirements_manager') else "❌ Unavailable" 
        st.metric("Requirements Manager", requirements_status)
    
    # Additional information
    st.markdown("---")
    
    with st.expander("ℹ️ About Resume Customizer"):
        st.markdown(f"""
        **Application Version:** {APP_CONFIG['version']}
        
        **Features:**
        - Multi-page Streamlit application
        - PostgreSQL database integration
        - Async processing support
        - Advanced error handling
        - Structured logging
        - Email integration
        - Security features
        
        **Supported Formats:**
        - Input: DOCX resume files
        - Output: Customized DOCX files
        - Tech Stack: Specific format required (see guide)
        
        **Navigation:**
        Use the sidebar to navigate between different pages and features of the application.
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Resume Customizer v{} - Streamlit Multi-Page Application</p>
        <p>🚀 Powered by Python, Streamlit, and PostgreSQL</p>
    </div>
    """.format(APP_CONFIG['version']), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
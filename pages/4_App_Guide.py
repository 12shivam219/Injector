"""
Application Guide Page - Help and documentation
"""

import streamlit as st

# Import the shared bootstrap
try:
    from infrastructure.app.app_bootstrap import initialize_app, get_cached_services
    app_initialized = True
except ImportError:
    app_initialized = False

if app_initialized:
    # Initialize the application
    initialize_app()
    services = get_cached_services()
    
    # Add logout button
    from ui.secure_components import SecureUIComponents
    secure_ui = SecureUIComponents()
    secure_ui.render_logout_button()
    
    # Get application guide
    app_guide = services.get('app_guide')
    
    # Set page title
    st.title("📚 Application Guide")
    st.markdown("🎯 **Complete guide to using the Resume Customizer effectively**")
    
    # Return button for better navigation
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔙 Back to Resume Customizer", key="back_to_main"):
            st.switch_page("pages/1_Resume_Customizer.py")
    with col2:
        st.success("📚 Comprehensive Application Guide")
    
    st.info("💡 **Navigation Tip:** Use the sidebar to navigate between different sections of the application.")
    
    # Render application guide content
    if app_guide:
        try:
            # Use the main tab render method from application guide
            app_guide.render_main_tab()
        except Exception as e:
            st.error(f"❌ Error loading application guide: {str(e)}")
            # Provide fallback content
            render_fallback_guide()
    else:
        st.warning("⚠️ Application guide not available. Showing basic help content.")
        render_fallback_guide()

else:
    # Fallback display when bootstrap not available
    st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")
    render_fallback_guide()

def render_fallback_guide():
    """Render basic help content when full guide is not available."""
    
    st.markdown("---")
    
    # Basic usage guide
    st.markdown("## 🚀 Getting Started")
    
    with st.expander("📄 Step 1: Upload Resume Files", expanded=True):
        st.markdown("""
        **Supported Formats:** DOCX files only
        
        1. Go to the **Resume Customizer** page
        2. Choose **Local Upload** or **Google Drive**
        3. Select one or more resume files
        4. Files will be processed and ready for customization
        """)
    
    with st.expander("⚙️ Step 2: Configure Tech Stacks", expanded=True):
        st.markdown("""
        **Supported Input Formats:**
        
        ```
        Format 1: Tech Stack + tabbed bullets
        Python
        •	Developed web applications using Django
        •	Created APIs with Flask
        
        Format 2: Tech Stack: + tabbed bullets  
        JavaScript:
        •	Built interactive UIs with React
        •	Implemented Node.js backends
        
        Format 3: Tech Stack + regular bullets
        AWS
        • Deployed applications on EC2
        • Managed databases with RDS
        ```
        
        **Important:** Only these 3 formats are accepted!
        """)
    
    with st.expander("📧 Step 3: Email Configuration (Optional)", expanded=True):
        st.markdown("""
        **Email Settings:**
        - **Recipient Email:** Where to send the resume
        - **Sender Email:** Your email address  
        - **App Password:** Use app-specific passwords for Gmail/Office365
        - **SMTP Server:** Pre-configured options available
        
        **Security Note:** Passwords are encrypted and never stored permanently.
        """)
    
    with st.expander("🚀 Step 4: Process & Send", expanded=True):
        st.markdown("""
        **Single Resume:**
        1. Click **🔍 Preview Changes** to see modifications
        2. Click **✅ Generate & Send** to process and email
        
        **Bulk Processing:**
        1. Go to **Bulk Processor** page
        2. Select multiple configured resumes
        3. Choose processing options (parallel workers, async mode)
        4. Click **🚀 Generate ALL** or **📤 Send ALL**
        """)
    
    # Features overview
    st.markdown("---")
    st.markdown("## ✨ Key Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🎯 Smart Customization**
        - Automatically distributes tech points across top 3 projects
        - Preserves original document formatting
        - Supports multiple resume formats
        
        **⚡ High Performance**
        - Async processing for multiple resumes
        - Background processing with Celery
        - Real-time progress tracking
        """)
    
    with col2:
        st.markdown("""
        **📧 Email Integration**
        - Direct email sending with SMTP
        - Batch email operations
        - Secure password handling
        
        **🔒 Security Features**
        - Rate limiting and validation
        - Encrypted password storage
        - Input sanitization
        """)
    
    # Troubleshooting
    st.markdown("---")
    st.markdown("## 🛠️ Troubleshooting")
    
    with st.expander("❌ Common Issues"):
        st.markdown("""
        **Resume Not Recognized:**
        - Ensure clear "Responsibilities:" sections in your resume
        - Check that projects have proper headings
        - Verify DOCX format (not DOC or PDF)
        
        **Email Not Sending:**
        - Use app-specific passwords for Gmail/Office365
        - Check firewall settings
        - Verify SMTP server and port settings
        
        **Tech Stack Format Rejected:**
        - Use only the 3 supported formats shown above
        - Ensure proper tabbing with bullets (•\t)
        - Check for extra spaces or formatting
        """)
    
    with st.expander("🔧 Performance Tips"):
        st.markdown("""
        **For Better Performance:**
        - Use async processing for multiple resumes
        - Reduce worker count on lower-spec machines
        - Close unused browser tabs
        - Enable background processing with Celery
        
        **File Size Optimization:**
        - Keep resume files under 10MB
        - Remove unnecessary images or graphics
        - Use standard fonts and formatting
        """)
    
    # Contact and support
    st.markdown("---")
    st.markdown("## 📞 Support")
    
    st.info("""
    **Need Help?**
    - Check the troubleshooting section above
    - Review error messages carefully - they provide specific guidance
    - Ensure all dependencies are properly installed
    """)
    
    # Version information
    st.markdown("---")
    st.markdown("## ℹ️ Version Information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("App Version", "2.0.0")
    with col2:
        st.metric("Python Version", "3.11+")
    with col3:
        st.metric("Streamlit Framework", "1.28.0+")
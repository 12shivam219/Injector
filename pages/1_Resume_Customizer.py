"""
Resume Customizer Page - Individual resume processing
"""

import streamlit as st
from io import BytesIO
from typing import Dict, Any, Optional

# Import required components
from app_bootstrap import initialize_app, get_cached_services
from ui.components import UIComponents

def main():
    # Initialize the application
    initialize_app()

    # Get or create UI components
    services = get_cached_services()
    ui = services.get('ui_components')
    if ui is None:
        ui = UIComponents()
    services['ui_components'] = ui

    secure_ui = services.get('secure_ui_components')
    tab_handler = services.get('resume_tab_handler')
        
    # Set page title
    st.title("📄 Resume Customizer")
    st.markdown("🎯 **Customize individual resumes with tech stack data**")

    # Render sidebar components
    if ui:
        ui.render_sidebar()
    if secure_ui:
        secure_ui.display_security_status()
        
        # Add About button in sidebar
        with st.sidebar:
            st.markdown("---")
            if st.button("ℹ️ About This Application", key="about_app_button", help="Learn more about the application"):
                st.session_state.redirect_to_about = True
                st.rerun()
            
            st.info("📚 **Tip:** You can also access the full guide by clicking the '📚 Know About The Application' tab above.")
        
        # Main content area
        st.markdown("### 📁 File Upload & Processing")
        
    # File upload section
        file_source = st.radio("📂 File Source:", ["Local Upload", "Google Drive"], horizontal=True)
        all_files = []
        
        if file_source == "Local Upload":
            with st.spinner("🔄 Initializing file upload interface..."):
                uploaded_files = ui.render_file_upload(key="file_upload_customizer")
            
            if uploaded_files:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, file in enumerate(uploaded_files):
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {file.name}... ({i+1}/{len(uploaded_files)})")
                    all_files.append((file.name, file))
                
                progress_bar.empty()
                status_text.empty()
                st.toast(f"✅ {len(uploaded_files)} files uploaded successfully!", icon="📁")
        else:
            if st.button("🔗 Open Google Drive Picker", key="open_gdrive_picker"):
                with st.spinner("🌐 Connecting to Google Drive..."):
                    gdrive_files = ui.render_gdrive_picker(key="gdrive_picker_customizer")
                
                if gdrive_files:
                    st.toast(f"✅ {len(gdrive_files)} files selected from Google Drive!", icon="☁️")
                    all_files.extend(gdrive_files)
        
        # Process files if uploaded
        if all_files:
            st.markdown("### 🔍 File Processing")
            
            # File metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Files Uploaded", len(all_files))
            with col2:
                total_size = sum(getattr(f[1], 'size', 0) for f in all_files) / (1024*1024)
                st.metric("📊 Total Size", f"{total_size:.1f} MB")
            with col3:
                processing_mode = "⚡ Async" if st.session_state.get('async_initialized') else "🔄 Standard"
                st.metric("🚀 Processing Mode", processing_mode)
            
            # Render individual tabs for each file
            if tab_handler is None:
                st.error("⚠️ Resume processing functionality is not available. Please check the application configuration.")
                return
                
            if len(all_files) == 1:
                # Single file - render directly
                file = all_files[0][1]
                tab_handler.render_tab(file)
            else:
                # Multiple files - create tabs
                tab_names = [f"📄 {file[0]}" for file in all_files]
                tabs = st.tabs(tab_names)
                
                for i, (file_name, file) in enumerate(all_files):
                    with tabs[i]:
                        tab_handler.render_tab(file)
        
        else:
            st.info("👆 Please upload resume files to get started")
            
            with st.expander("ℹ️ How to Use Resume Customizer"):
                st.markdown("""
                **Step 1:** Upload your resume files (DOCX format)
                
                **Step 2:** Add tech stack data in the supported format:
                ```
                Python
                • Developed web applications using Django
                • Built APIs with Flask framework
                
                JavaScript
                • Created interactive UI with React
                • Implemented Node.js backends
                ```
                
                **Step 3:** Configure email settings (optional)
                
                **Step 4:** Generate and download your customized resume
                """)

    else:
        # Fallback display when bootstrap not available
        st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")
    # Fallback display when bootstrap not available
    st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")

if __name__ == "__main__":
    main()
    st.info("📝 This page requires the main application to be properly configured.")
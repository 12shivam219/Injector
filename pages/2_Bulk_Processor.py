"""
Bulk Processor Page - Batch resume processing
"""

import streamlit as st
from typing import List, Dict, Any

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
    
    # Get services
    ui = services['ui_components']
    secure_ui = services['secure_ui_components'] 
    bulk_processor = services['bulk_processor']
    
    # Set page title
    st.title("📤 Bulk Processor")
    st.markdown("🚀 **Process multiple resumes simultaneously for maximum efficiency**")
    
    # Render sidebar components
    if ui:
        ui.render_sidebar()
    if secure_ui:
        secure_ui.display_security_status()
    
    # Check for uploaded files from session state
    uploaded_files = st.session_state.get('uploaded_files', [])
    
    if not uploaded_files:
        st.warning("📁 No files uploaded yet. Please upload files in the Resume Customizer page first.")
        
        if st.button("🔗 Go to Resume Customizer", key="goto_resume_customizer"):
            st.switch_page("pages/1_Resume_Customizer.py")
        
        st.markdown("---")
        st.markdown("### 📋 How Bulk Processing Works")
        st.info("""
        **Bulk processing allows you to:**
        
        1. **Upload multiple resumes** in the Resume Customizer page
        2. **Configure tech stacks** for each resume individually  
        3. **Process all resumes** simultaneously using parallel processing
        4. **Send batch emails** to multiple recipients at once
        
        **Performance Benefits:**
        - ⚡ Up to 8x faster with async processing
        - 📊 Real-time progress tracking
        - 🔄 Background processing with Celery (if available)
        - 📈 Detailed performance metrics
        """)
        
    else:
        # File readiness check
        from ui.utils import check_file_readiness, prepare_bulk_data
        
        ready_files, missing_data_files = check_file_readiness(uploaded_files)
        
        # Display file status
        st.markdown("### 📊 File Status Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📁 Total Files", len(uploaded_files))
        with col2:
            st.metric("✅ Ready for Processing", len(ready_files))
        with col3:
            st.metric("⚠️ Missing Data", len(missing_data_files))
        
        # Show file details
        if missing_data_files:
            with st.expander("⚠️ Files Missing Tech Stack Data", expanded=True):
                for filename in missing_data_files:
                    st.warning(f"📄 **{filename}** - Please add tech stack data in Resume Customizer")
                    
                if st.button("🔧 Configure Missing Files", key="configure_missing"):
                    st.switch_page("pages/1_Resume_Customizer.py")
        
        if ready_files:
            with st.expander("✅ Files Ready for Processing", expanded=len(missing_data_files) == 0):
                for filename in ready_files:
                    st.success(f"📄 **{filename}** - Ready to process")
        
        # Bulk processing options
        if ready_files:
            st.markdown("---")
            st.markdown("### 🚀 Bulk Processing Options")
            
            # Performance settings
            col1, col2 = st.columns(2)
            
            with col1:
                max_workers = st.slider(
                    "🔧 Parallel Workers", 
                    min_value=1, 
                    max_value=8, 
                    value=3,
                    help="Number of parallel workers for processing"
                )
                
                show_progress = st.checkbox(
                    "📊 Show Detailed Progress", 
                    value=True,
                    key="bulk_page_show_progress",
                    help="Display real-time progress updates"
                )
            
            with col2:
                performance_stats = st.checkbox(
                    "📈 Performance Statistics", 
                    value=False,
                    key="bulk_page_performance_stats",
                    help="Show detailed performance metrics"
                )
                
                bulk_email_mode = st.selectbox(
                    "📧 Email Mode",
                    ["No emails", "Send emails in parallel", "Generate only"],
                    index=1,
                    help="Choose how to handle email sending"
                )
            
            # Action buttons
            st.markdown("### ⚡ Bulk Actions")
            
            # Render bulk action buttons from the bulk processor
            if bulk_processor:
                bulk_processor.render_bulk_actions(uploaded_files)
            else:
                st.error("❌ Bulk processor not available")
            
            # Manual bulk processing trigger
            st.markdown("---")
            st.markdown("### 🎛️ Manual Bulk Processing")
            
            if st.button("🚀 Start Bulk Processing", key="manual_bulk_processing", type="primary"):
                if ready_files and bulk_processor:
                    files_data = prepare_bulk_data(uploaded_files, ready_files)
                    
                    if files_data:
                        with st.spinner("🔄 Starting bulk processing..."):
                            bulk_processor.process_bulk_resumes(
                                ready_files=ready_files,
                                files_data=files_data,
                                max_workers=max_workers,
                                show_progress=show_progress,
                                performance_stats=performance_stats,
                                bulk_email_mode=bulk_email_mode
                            )
                    else:
                        st.error("❌ Could not prepare file data for bulk processing")
                else:
                    st.error("❌ No files ready or bulk processor unavailable")
            
            # Show bulk results if available
            if st.session_state.get('bulk_results'):
                st.markdown("---")
                st.markdown("### 📊 Recent Bulk Processing Results")
                
                results = st.session_state.bulk_results
                if isinstance(results, list) and results:
                    for i, result in enumerate(results[-5:]):  # Show last 5 results
                        with st.expander(f"📋 Result {i+1}: {result.get('filename', 'Unknown')}"):
                            if result.get('success'):
                                st.success(f"✅ Processed successfully - {result.get('points_added', 0)} points added")
                            else:
                                st.error(f"❌ Failed: {result.get('error', 'Unknown error')}")
        
        else:
            st.info("👆 Configure tech stack data for your files to enable bulk processing")

else:
    # Fallback display when bootstrap not available
    st.error("❌ Application bootstrap not available. Please ensure app_bootstrap.py is configured correctly.")
    st.info("📝 This page requires the main application to be properly configured.")
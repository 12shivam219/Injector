import streamlit as st
from io import BytesIO
import base64
import hashlib

from infrastructure.security.validators import TextValidator
import logging
from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger

# Initialize logger with fallback
try:
    logger = get_logger()
    structured_logger = get_structured_logger("resume_tab_handler")
except Exception:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    structured_logger = logger

class ResumeTabHandler:
    """Handles individual resume tab functionality."""
    
    def __init__(self, resume_manager=None):
        self.resume_manager = resume_manager

    def render_tab(self, file):
        """Render the tab content for a single resume file."""
        if self.resume_manager is None:
            st.error("⚠️ Resume processing is not available. Please check the application configuration.")
            return
            
        from config import get_default_email_subject, get_default_email_body, get_smtp_servers
        
        # Create unique identifier for this file instance
        file_content = file.read()
        file.seek(0)  # Reset file pointer
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        unique_key = f"{file.name}_{file_hash}"
        
        # Defensive: check for resume_inputs existence
        if 'resume_inputs' not in st.session_state:
            st.session_state['resume_inputs'] = {}
        if unique_key not in st.session_state.resume_inputs:
            st.session_state.resume_inputs[unique_key] = {}
        file_data = st.session_state.resume_inputs[unique_key]

        # Automatic format matching on upload: analyze and store match info in session
        try:
            from resume_customizer.analyzers.format_analyzer import FormatAnalyzer
            from infrastructure.storage.local_format_store import LocalFormatStore
            analyzer = FormatAnalyzer()
            # Load document for analysis
            try:
                doc = Document(BytesIO(file_content))
            except Exception:
                doc = None

            match_info = None
            if doc is not None:
                # Try DB first
                services = None
                try:
                    from infrastructure.app.app_bootstrap import get_cached_services
                    services = get_cached_services()
                except Exception:
                    services = None

                stored_formats = []
                if services and services.get('db_session'):
                    try:
                        Session = services.get('db_session')
                        session = Session()
                        from database.format_models import ResumeFormat
                        stored_formats = session.query(ResumeFormat).all()
                        session.close()
                    except Exception:
                        stored_formats = []

                if not stored_formats:
                    # Fallback to local formats
                    try:
                        local_store = LocalFormatStore()
                        stored_formats = local_store.list_formats() or []
                    except Exception:
                        stored_formats = []

                # If stored_formats are dicts (local store), adapt to a common interface
                best_score = 0
                best_fmt = None
                best_matched = None
                for fmt in stored_formats:
                    try:
                        if isinstance(fmt, dict):
                            # adapt dict -> simple object with attributes used by analyzer
                            class _Tmp:
                                pass
                            tmp = _Tmp()
                            for k, v in fmt.items():
                                setattr(tmp, k, v)
                            fmt_obj = tmp
                        else:
                            fmt_obj = fmt

                        score, matched = analyzer.match_format(Document(BytesIO(file_content)), fmt_obj)
                        if score > best_score:
                            best_score = score
                            best_fmt = fmt_obj
                            best_matched = matched
                    except Exception:
                        continue

                if best_fmt:
                    match_info = {
                        'matched_format': getattr(best_fmt, 'name', getattr(best_fmt, 'id', None)),
                        'match_score': best_score,
                        'matched_elements': best_matched,
                        'matched_companies': []
                    }
                    # try to extract company names from matched format or matched_elements
                    try:
                        if isinstance(best_fmt, dict):
                            cp = best_fmt.get('company_patterns') or []
                        else:
                            cp = getattr(best_fmt, 'company_patterns', None) or []
                        # company_patterns may be list of dicts with 'pattern'
                        for c in cp:
                            if isinstance(c, dict) and 'pattern' in c:
                                match_info['matched_companies'].append(c['pattern'])
                            elif isinstance(c, str):
                                match_info['matched_companies'].append(c)
                    except Exception:
                        pass

            # Store match info in session state for this file
            if match_info:
                st.session_state.resume_inputs[unique_key]['format_match'] = match_info
            else:
                st.session_state.resume_inputs[unique_key]['format_match'] = None
        except Exception:
            # Non-fatal; ensure no crash during upload
            st.session_state.resume_inputs[unique_key]['format_match'] = None
        
        # Tech stack input
        st.markdown("#### 📝 Tech Stack & Points")
        
        # Show supported formats (cached for performance)
        if st.checkbox("📋 Show Input Format Guide", key=f"show_input_format_guide_{unique_key}", help="View supported formats"):
            st.info("""
**3 Supported Formats:**
1. **Tech Stack** + tabbed bullets (•\tpoint)
2. **Tech Stack:** + tabbed bullets (•\tpoint)  
3. **Tech Stack** + regular bullets (• point)
            """)
        
        st.warning("⚠️ Only the 3 formats above are accepted. Other formats will be rejected with detailed error messages.")
        
        # Text input for tech stacks
        text_input = st.text_area(
            "Paste your tech stack data here:",
            value=file_data.get('text', ''),
            height=150,
            help="Use only the 3 supported formats shown above. Example:\n\nJava\n•\tSpring Boot development\n•\tREST API implementation",
            key=f"tech_stack_{unique_key}"
        )
        file_data['text'] = text_input
        
        # Simplified manual points input
        if st.checkbox("🔧 Manual Points Override", key=f"show_manual_{unique_key}"):
            manual_text = st.text_area(
                "Manual points (one per line):",
                value=file_data.get('manual_text', ''),
                height=80,
                key=f"manual_points_{unique_key}"
            )
            file_data['manual_text'] = manual_text
        else:
            file_data['manual_text'] = file_data.get('manual_text', '')
        
        # Email configuration
        st.markdown("#### 📧 Email Configuration (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            recipient_email = st.text_input(
                "Recipient Email:",
                value=file_data.get('recipient_email', ''),
                help="Email address to send the customized resume to",
                key=f"recipient_email_{unique_key}"
            )
            file_data['recipient_email'] = recipient_email
            
            sender_email = st.text_input(
                "Sender Email:",
                value=file_data.get('sender_email', ''),
                help="Your email address",
                key=f"sender_email_{unique_key}"
            )
            file_data['sender_email'] = sender_email
            
            sender_password = st.text_input(
                "App Password:",
                value=file_data.get('sender_password', ''),
                type="password",
                help="App-specific password for your email account",
                key=f"sender_password_{unique_key}"
            )
            file_data['sender_password'] = sender_password
        
        with col2:
            smtp_server = st.selectbox(
                "SMTP Server:",
                options=get_smtp_servers(),
                index=0,
                help="Select your email provider's SMTP server",
                key=f"smtp_server_{unique_key}"
            )
            file_data['smtp_server'] = smtp_server
            
            smtp_port = st.number_input(
                "SMTP Port:",
                value=file_data.get('smtp_port', 465),
                min_value=1,
                max_value=65535,
                help="SMTP port (usually 465 for SSL or 587 for TLS)",
                key=f"smtp_port_{unique_key}"
            )
            file_data['smtp_port'] = smtp_port
            
            email_subject = st.text_input(
                "Email Subject:",
                value=file_data.get('email_subject', get_default_email_subject()),
                help="Subject line for the email",
                key=f"email_subject_{unique_key}"
            )
            file_data['email_subject'] = email_subject
        
        email_body = st.text_area(
            "Email Body:",
            value=file_data.get('email_body', get_default_email_body()),
            height=100,
            help="Email body text",
            key=f"email_body_{unique_key}"
        )
        file_data['email_body'] = email_body
        
        # Action buttons
        st.markdown("#### 🚀 Actions")
        col1, col2 = st.columns(2)
        
        # Define manual_text here so it's available in both button scopes
        manual_text = file_data.get('manual_text', '')
        
        with col1:
            # Optimized preview button (no throttling for better UX)
            preview_key = f"preview_{unique_key}"
            if st.button("🔍 Preview Changes", key=preview_key):
                    # Determine whether to use format-aware injection (user can override)
                    match_info = st.session_state.resume_inputs[unique_key].get('format_match')
                    use_format = False
                    if match_info and match_info.get('match_score', 0) >= 70:
                        use_format = True

                    # Offer toggle to user before preview
                    if match_info:
                        st.info(f"Format matched: {match_info.get('matched_format')} ({match_info.get('match_score')}%)")
                        use_format = st.checkbox("Use format-aware injection for this file", value=use_format, key=f"use_format_{unique_key}")

                    file_data_for_preview = {
                        'filename': file.name,
                        'file': file,
                        'text': text_input,
                        'manual_text': manual_text,
                    }
                    if match_info and use_format:
                        file_data_for_preview['matched_companies'] = match_info.get('matched_companies', [])

                    self.handle_preview(file, file_data_for_preview['text'], file_data_for_preview.get('manual_text', ''), matched_companies=file_data_for_preview.get('matched_companies'))
        
        with col2:
            # Check if async processing is potentially available
            async_available = True
            try:
                # Quick check if tasks module exists
                import importlib
                spec = importlib.util.find_spec('tasks')
                async_available = spec is not None
            except Exception:
                async_available = False
            
            if async_available:
                async_mode = st.checkbox("⚡ Process in background (Celery)", 
                                       key=f"async_mode_{unique_key}",
                                       help="Process resume using Celery for background execution")
            else:
                async_mode = False
                st.info("📋 Background processing unavailable (Celery not configured)")

            # Generate button
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🚀 Generate Resume", key=f"generate_{unique_key}"):
                    # Validate input before processing
                    if not text_input.strip() and not manual_text.strip():
                        st.error(f"⚠️ Please enter tech stack data for {file.name} before generating.")
                        return
                     
                    # Prepare file data for processing (without email)
                    file_data_for_processing = {
                        'filename': file.name,
                        'file': file,
                        'text': text_input,
                        'manual_text': manual_text
                    }
                    # Pass matched companies if format-aware is enabled for this file
                    match_info = st.session_state.resume_inputs[unique_key].get('format_match')
                    if match_info and st.session_state.get(f"use_format_{unique_key}"):
                        file_data_for_processing['matched_companies'] = match_info.get('matched_companies', [])
                    
                    if async_mode:
                        try:
                            task = self.resume_manager.process_single_resume_async(file_data_for_processing)
                            # Store task ID in session state for status checking
                            task_id = getattr(task, 'id', getattr(task, 'task_id', str(task)))
                            st.session_state[f'async_task_{unique_key}'] = task_id
                            st.success(f"🎫 Submitted to background queue. Task ID: {task_id}")
                            st.info("📋 Use the 'Check Status' button below to monitor progress.")
                        except Exception as e:
                            st.error(f"❌ Failed to submit async task: {e}")
                            st.warning("Falling back to synchronous processing...")
                            self.handle_generation(file, file_data_for_processing)
                    else:
                        self.handle_generation(file, file_data_for_processing)
                
                # Email sending button
                with col2:
                    # Only show the Send Email button if a resume has been generated
                    if st.button("📧 Send Generated Resume", key=f"send_email_{unique_key}"):
                        # Check if resume has been generated
                        generated_resume = st.session_state.get(f'last_generated_resume_{unique_key}')
                        if not generated_resume:
                            st.error("❌ Please generate a resume first before sending an email.")
                            return
                            
                        # Validate email configuration
                        validation_result = self.resume_manager.validate_email_config({
                            'recipient': recipient_email,
                            'sender': sender_email,
                            'password': sender_password,
                            'smtp_server': smtp_server,
                            'smtp_port': smtp_port
                        })
                        
                        if not validation_result['valid']:
                            missing = validation_result['missing_fields']
                            st.error(f"❌ Email configuration incomplete. Missing: {', '.join(missing)}")
                        elif not recipient_email:
                            st.error("❌ Recipient email is required to send the resume.")
                        else:
                            # Prepare email data for sending
                            email_data = {
                                'recipient': recipient_email,
                                'sender': sender_email,
                                'password': sender_password,
                                'smtp_server': smtp_server,
                                'smtp_port': smtp_port,
                                'subject': email_subject,
                                'body': email_body,
                                'attachment': generated_resume.get('modified_content'),
                                'filename': file.name
                            }
                            # Call email sending function
                            self.handle_email_sending(email_data)
        
        # Separate status check button outside the main generate button
        if async_mode and st.session_state.get(f'async_task_{unique_key}'):
            if st.button("🔄 Check Async Status", key=f"check_status_{unique_key}"):
                task_id = st.session_state[f'async_task_{unique_key}']
                try:
                    status = self.resume_manager.get_async_result(task_id)
                    
                    # Display task status
                    state = status.get('state', 'UNKNOWN')
                    st.info(f"📝 Task {task_id[:8]}... status: **{state}**")
                    
                    # Handle different states
                    if state == 'SUCCESS':
                        result = status.get('result', {})
                        if result and result.get('success'):
                            st.success(f"✅ Resume processed with {result.get('points_added', 0)} points added!")
                            # Download link
                            if 'buffer' in result:
                                b64 = base64.b64encode(result['buffer']).decode()
                                link = f'<a href="data:application/octet-stream;base64,{b64}" download="{file.name}">📥 Download</a>'
                                st.markdown(link, unsafe_allow_html=True)
                                # Clear the task from session state since it's complete
                                del st.session_state[f'async_task_{unique_key}']
                        else:
                            st.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                            
                    elif state == 'PROGRESS':
                        st.info("⏳ Task is currently being processed...")
                        # Show progress info if available
                        if 'info' in status and status['info']:
                            progress_info = status['info']
                            if isinstance(progress_info, dict):
                                if 'status' in progress_info:
                                    st.info(f"📋 {progress_info['status']}")
                                if 'progress' in progress_info:
                                    st.progress(progress_info['progress'] / 100.0)
                                    
                    elif state in ['PENDING', 'STARTED']:
                        st.info("⏳ Task is queued and waiting to be processed...")
                        st.info("📋 Make sure the Celery worker is running: `python start_celery_worker.py`")
                        
                    elif state == 'FAILURE':
                        result = status.get('result', {})
                        error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                        st.error(f"❌ Task failed: {error_msg}")
                        
                        # Provide helpful suggestions
                        if 'not registered' in error_msg.lower():
                            st.warning("🛠️ Make sure the Celery worker is running with the updated task definitions.")
                        elif 'redis' in error_msg.lower():
                            st.warning("🛠️ Check if Redis server is running: `redis-cli ping` should return PONG")
                            
                    else:
                        st.warning(f"❓ Unknown task state: {state}")
                        if status.get('result'):
                            st.json(status['result'])
                            
                except Exception as e:
                    st.error(f"❌ Error checking task status: {str(e)}")
                    st.info("🛠️ Try restarting the Celery worker and Streamlit app")

    def handle_preview(self, file, user_input, manual_text="", matched_companies=None):
        """Handle preview generation for a single file."""
        if not user_input.strip() and not manual_text:
            st.warning(f"⚠️ Please enter tech stack data for {file.name} before previewing.")
            return

        from infrastructure.security.validators import get_rate_limiter
        user_id = st.session_state.get('user_id', 'anonymous')
        rate_limiter = get_rate_limiter()
        if rate_limiter.is_rate_limited(user_id, 'preview', max_requests=10, time_window=60):
            st.error("⚠️ Too many preview requests. Please wait a moment before trying again.")
            return

        st.markdown("---")
        st.markdown(f"### 👀 Preview of Changes for {file.name}")
        
        with st.expander(f"📄 Preview for {file.name}", expanded=True):
            try:
                result = self.resume_manager.generate_preview(file, user_input, manual_text, matched_companies=matched_companies)
                if not result['success']:
                    st.error(f"❌ {result['error']}")
                    if 'errors' in result and result['errors']:
                        for err in result['errors']:
                            st.error(f"❌ {err}")
                    return

                # Clear success message with breakdown
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🎯 Points Added", result['points_added'])
                with col2:
                    st.metric("📊 Tech Stacks", len(result['tech_stacks_used']))
                with col3:
                    st.metric("📁 Projects Found", result['projects_count'])
                
                st.success(f"✅ Preview generated successfully! {result['points_added']} new bullet points will be added to your resume.")
                
                # Highlighted section showing what will be added
                st.markdown("### 🆕 NEW POINTS THAT WILL BE ADDED")
                st.markdown("**These bullet points will be added to your resume:**")
                
                # Show each new point with clear highlighting
                for project, mapping in result['project_points_mapping'].items():
                    st.markdown(f"**📋 {project}:**")
                    # Use a colored container to make new points stand out
                    with st.container():
                        for point in mapping['points']:
                            # Remove bullet marker if present and add our own styling
                            clean_point = point.lstrip('• ').strip()
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🆕 **{clean_point}**", unsafe_allow_html=True)
                    st.markdown("---")
                
                # Also show tech stacks used
                st.info(f"📚 **Tech stacks processed:** {', '.join(result['tech_stacks_used'])}")

                # Display document preview with better highlighting
                st.markdown("### 📄 FULL RESUME PREVIEW (WITH NEW POINTS)")
                st.markdown("**Your complete resume with the new bullet points added:**")
                
                try:
                    import mammoth
                    buffer = BytesIO()
                    result['preview_doc'].save(buffer)
                    buffer.seek(0)
                    html = mammoth.convert_to_html(buffer).value
                    
                    # Try to highlight new points in the HTML (basic approach)
                    for project, mapping in result['project_points_mapping'].items():
                        for point in mapping['points']:
                            clean_point = point.lstrip('• ').strip()
                            # Add highlighting to new points
                            if clean_point in html:
                                highlighted = f'<span style="background-color: #90EE90; padding: 2px; border-radius: 3px;">• {clean_point}</span>'
                                html = html.replace(f'• {clean_point}', highlighted)
                    
                    st.markdown(html, unsafe_allow_html=True)
                    st.info("💡 **Green highlighted bullet points** are the new points that were added.")
                    
                except ImportError:
                    st.markdown("📝 **Updated Resume Content:**")
                    st.info("💡 Install 'mammoth' for better Word format display: `pip install mammoth`")
                    
                    # Create highlighted text version with improved formatting
                    preview_text = result['preview_content']
                    
                    # Add visual markers to new points with color coding
                    for project, mapping in result['project_points_mapping'].items():
                        for point in mapping['points']:
                            clean_point = point.lstrip('• ').strip()
                            if clean_point in preview_text:
                                preview_text = preview_text.replace(clean_point, f"🆕 {clean_point} 🆕")
                    
                    # Create tabs for different preview views
                    preview_tabs = st.tabs(["📄 Full Preview", "✨ New Points Only", "📊 Visual Diff", "⚖️ Before/After"])
                    
                    with preview_tabs[0]:
                        st.text_area("Complete Resume Content (🆕 = newly added points)", value=preview_text, height=500)
                    
                    with preview_tabs[1]:
                        # Show only the new points organized by project
                        st.markdown("### 📌 New Points by Project")
                        for project, mapping in result['project_points_mapping'].items():
                            if mapping['points']:
                                st.markdown(f"**{project}**")
                                for point in mapping['points']:
                                    st.markdown(f"• {point.lstrip('• ').strip()}")
                                st.markdown("---")
                    
                    with preview_tabs[2]:
                        # Create a visual diff representation
                        st.markdown("### 📊 Visual Difference")
                        st.markdown("This view highlights the changes that will be made to your resume.")
                        
                        # Create a styled version of the preview text
                        styled_text = preview_text.replace("== ", "<h4>").replace(" ==", "</h4>")
                        styled_text = styled_text.replace("🆕 ", "<span style='background-color: #CCFFCC; padding: 2px 4px; border-radius: 3px;'>").replace(" 🆕", "</span>")
                        st.markdown(styled_text, unsafe_allow_html=True)
                        
                    with preview_tabs[3]:
                        # Show before/after comparison
                        st.markdown("### ⚖️ Before vs After Comparison")
                        st.markdown(f"Last updated: {result.get('last_updated', 'N/A')}")
                        
                        # Create two columns for side-by-side comparison
                        before_col, after_col = st.columns(2)
                        
                        with before_col:
                            st.markdown("#### 📄 Original Resume")
                            st.text_area("Before changes", value=result.get('original_content', 'Original content not available'), height=400)
                            
                        with after_col:
                            st.markdown("#### 📝 Updated Resume")
                            st.text_area("After changes", value=preview_text, height=400)

                # Enhanced summary section
                st.markdown("---")
                st.markdown("### 🎯 PREVIEW SUMMARY")
                
                # Use 3 columns for more detailed information
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.markdown("**What will happen:**")
                    st.markdown(f"• **{result['points_added']} new bullet points** will be added")
                    st.markdown(f"• Points across **{result['projects_count']} projects**")
                    st.markdown(f"• Tech stacks: **{', '.join(result['tech_stacks_used'])}**")
                
                with summary_col2:
                    st.markdown("**Distribution Details:**")
                    for project, mapping in result['project_points_mapping'].items():
                        if mapping['points']:
                            st.markdown(f"• **{project}**: {len(mapping['points'])} points")
                
                with summary_col3:
                    st.markdown("**Preview Guide:**")
                    st.markdown("• 📄 **Full Preview** - Complete resume")
                    st.markdown("• ✨ **New Points** - Only additions")
                    st.markdown("• 📊 **Visual Diff** - Highlighted changes")
                
                st.success("✅ Preview completed! If everything looks good, click 'Generate & Send' to create your customized resume.")
            except Exception as e:
                st.error(f"❌ Error generating preview: {e}")

    def handle_generation(self, file, file_data):
        """Handle the resume generation process and display results"""
        from infrastructure.security.validators import get_rate_limiter
        user_id = st.session_state.get('user_id', 'anonymous')
        rate_limiter = get_rate_limiter()
        if rate_limiter.is_rate_limited(user_id, 'generation', max_requests=20, time_window=300):
            st.error("⚠️ Too many generation requests. Please wait before trying again.")
            return

        st.markdown("---")
        st.markdown(f"### ✅ Generating Customized Resume: {file.name}")
        structured_logger.user_action("resume_generation", details={"file_name": file.name})

        status_placeholder = st.empty()
        def progress_callback(msg):
            status_placeholder.info(msg)

        with st.spinner(f"Processing {file.name}…"):
            result = self.resume_manager.process_single_resume(file_data, progress_callback=progress_callback)
            if not result['success']:
                error_msg = f"❌ {result['error']}"
                
                # Display detailed error information if available
                if 'error_details' in result:
                    with st.expander("📋 Error Details", expanded=True):
                        st.markdown("**Error Information:**")
                        st.code(result['error_details'])
                        
                        # Show diagnostics if available
                        if 'diagnostics' in result:
                            st.markdown("**Diagnostics:**")
                            for key, value in result['diagnostics'].items():
                                st.markdown(f"- **{key}**: {value}")
                        
                        # Show troubleshooting tips based on error type
                        st.markdown("**Troubleshooting Tips:**")
                        if "parser" in result['error'].lower():
                            st.markdown("- Check your input text format")
                            st.markdown("- Ensure there are no special characters causing issues")
                        elif "document" in result['error'].lower():
                            st.markdown("- Verify your document is not corrupted")
                            st.markdown("- Try saving your document in a different format")
                        elif "permission" in result['error'].lower():
                            st.markdown("- The file might be locked by another application")
                            st.markdown("- Try closing other applications that might be using this file")
                
                st.error(error_msg)
                return

            st.success(f"✅ Resume processed with {result['points_added']} points added!")
            
            # Provide download link
            if 'buffer' in result:
                b64 = base64.b64encode(result['buffer']).decode()
                link = f'<a href="data:application/octet-stream;base64,{b64}" download="{file.name}">📥 Download</a>'
                st.markdown(link, unsafe_allow_html=True)
                # Store buffer as modified_content if it doesn't exist
                if not 'modified_content' in result:
                    result['modified_content'] = result['buffer']
            elif 'modified_content' in result:
                b64 = base64.b64encode(result['modified_content']).decode()
                link = f'<a href="data:application/octet-stream;base64,{b64}" download="{file.name}">📥 Download</a>'
                st.markdown(link, unsafe_allow_html=True)
            else:
                st.warning("⚠️ No downloadable content available.")
                
            st.success(f"🎉 {file.name} processed successfully!")
            
            # Store the result in session state for email sending
            unique_key = f"{file.name}_{hashlib.md5(file.read()).hexdigest()[:8]}"
            file.seek(0)  # Reset file pointer
            # Ensure result has modified_content for email attachment
            if 'buffer' in result and not 'modified_content' in result:
                result['modified_content'] = result['buffer']
            st.session_state[f'last_generated_resume_{unique_key}'] = result
            
            # Display info message about downloading or sending
            st.info("📋 You can download your resume or use the 'Send Generated Resume' button to email it.")
            
            # Show audit log if available
            if hasattr(self.resume_manager, '_audit_log'):
                with st.expander("🔍 Audit Log", expanded=False):
                    for entry in self.resume_manager._audit_log[-5:]:
                        st.code(str(entry))
                        
    def handle_email_sending(self, email_data):
        """Handle the email sending process and display results"""
        try:
            # Validate that we have a generated resume
            if not email_data.get('attachment'):
                st.error("❌ No resume content available to send. Please generate a resume first.")
                return
            
            structured_logger.user_action("email_sending", details={"recipient": email_data.get('recipient')})
            
            with st.spinner("📧 Sending email..."):
                # Send the email with attachment
                result = self.resume_manager.send_single_email(
                    email_data['smtp_server'], 
                    email_data['smtp_port'],
                    email_data['sender'], 
                    email_data['password'],
                    email_data['recipient'], 
                    email_data['subject'],
                    email_data['body'], 
                    email_data['attachment'], 
                    email_data['filename']
                )
                
                if result and result.get('success'):
                    st.success(f"✅ Email sent successfully to {email_data['recipient']}!")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    st.error(f"❌ Failed to send email: {error_msg}")
        except Exception as e:
            st.error(f"❌ Error sending email: {str(e)}")
            logging.error(f"Error in handle_email_sending: {str(e)}", exc_info=True)



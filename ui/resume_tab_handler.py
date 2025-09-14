import streamlit as st
from io import BytesIO
import base64
import hashlib

from infrastructure.security.validators import TextValidator
from infrastructure.utilities.logger import get_logger

logger = get_logger()

class ResumeTabHandler:
    """Handles individual resume tab functionality."""
    
    def __init__(self, resume_manager):
        self.resume_manager = resume_manager

    def render_tab(self, file):
        """Render the tab content for a single resume file."""
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
        
        # Tech stack input
        st.markdown("#### 📝 Tech Stack & Points")
        
        # Show supported formats (cached for performance)
        if st.checkbox("📋 Show Input Format Guide", help="View supported formats"):
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
        
        with col1:
            # Optimized preview button (no throttling for better UX)
            preview_key = f"preview_{unique_key}"
            if st.button("🔍 Preview Changes", key=preview_key):
                manual_text = file_data.get('manual_text', '')
                self.handle_preview(file, text_input, manual_text)
        
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
            
            if st.button("✅ Generate & Send", key=f"generate_{unique_key}"):
                # Validate input before processing
                if not text_input.strip() and not manual_text.strip():
                    st.error(f"⚠️ Please enter tech stack data for {file.name} before generating.")
                    return
                    
                # Prepare file data for processing
                file_data_for_processing = {
                    'filename': file.name,
                    'file': file,
                    'text': text_input,
                    'manual_text': manual_text,
                    'recipient_email': recipient_email,
                    'sender_email': sender_email,
                    'sender_password': sender_password,
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'email_subject': email_subject,
                    'email_body': email_body
                }
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

    def handle_preview(self, file, user_input, manual_text=""):
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
                result = self.resume_manager.generate_preview(file, user_input, manual_text)
                if not result['success']:
                    st.error(f"❌ {result['error']}")
                    if 'errors' in result and result['errors']:
                        for err in result['errors']:
                            st.error(f"❌ {err}")
                    return

                st.success(f"✅ Preview generated with {result['points_added']} points added!")
                st.info(f"Tech stacks highlighted: {', '.join(result['tech_stacks_used'])}")
                st.info(f"📂 Number of projects in resume: {result['projects_count']}")

                st.markdown("### 📊 Points Distribution by Project")
                for project, mapping in result['project_points_mapping'].items():
                    with st.expander(f"Project: {project}"):
                        for tech, points in mapping.items():
                            st.markdown(f"**{tech}**")
                            for p in points:
                                st.markdown(f"- {p}")
                            st.markdown("")

                # Display document preview
                try:
                    import mammoth
                    buffer = BytesIO()
                    result['preview_doc'].save(buffer)
                    buffer.seek(0)
                    html = mammoth.convert_to_html(buffer).value
                    st.markdown("### 📝 Your Updated Resume (Word Format):", unsafe_allow_html=True)
                    st.markdown(html, unsafe_allow_html=True)
                except ImportError:
                    st.markdown("### 📝 Your Updated Resume Content:")
                    st.info("Install 'mammoth' for better Word format display: pip install mammoth")
                    st.text_area("Updated Resume Content", value=result['preview_content'], height=600)

                st.success("✅ Preview completed! Review changes above.")
            except Exception as e:
                st.error(f"❌ Error generating preview: {e}")

    def handle_generation(self, file, file_data):
        """Handle resume generation and email sending with async/caching integration."""
        from infrastructure.security.validators import get_rate_limiter
        user_id = st.session_state.get('user_id', 'anonymous')
        rate_limiter = get_rate_limiter()
        if rate_limiter.is_rate_limited(user_id, 'generation', max_requests=20, time_window=300):
            st.error("⚠️ Too many generation requests. Please wait before trying again.")
            return

        st.markdown("---")
        st.markdown(f"### ✅ Generating Customized Resume: {file.name}")
        logger.log_user_action("resume_generation", file_name=file.name)

        status_placeholder = st.empty()
        def progress_callback(msg):
            status_placeholder.info(msg)

        with st.spinner(f"Processing {file.name}…"):
            result = self.resume_manager.process_single_resume(file_data, progress_callback=progress_callback)
            if not result['success']:
                st.error(f"❌ {result['error']}")
                return

            st.success(f"✅ Resume processed with {result['points_added']} points added!")
            email_data = result['email_data']
            valid = self.resume_manager.validate_email_config(email_data)['valid']

            if valid:
                try:
                    email_res = self.resume_manager.send_single_email(
                        email_data['smtp_server'], email_data['smtp_port'],
                        email_data['sender'], email_data['password'],
                        email_data['recipient'], email_data['subject'],
                        email_data['body'], result['buffer'], file.name
                    )
                    if email_res['success']:
                        st.success(f"📤 Email sent to {email_data['recipient']}")
                    else:
                        st.error(f"❌ Email failed: {email_res['error']}")
                except Exception as e:
                    st.error(f"❌ Email sending failed: {e}")
            else:
                missing = self.resume_manager.validate_email_config(email_data)['missing_fields']
                st.warning(f"⚠️ Email skipped—Missing: {', '.join(missing)}")

            # Provide download link regardless of email status
            b64 = base64.b64encode(result['buffer']).decode()
            link = f'<a href="data:application/octet-stream;base64,{b64}" download="{file.name}">📥 Download</a>'
            st.markdown(link, unsafe_allow_html=True)
            st.success(f"🎉 {file.name} processed successfully!")
            
            # Show audit log if available
            if hasattr(self.resume_manager, '_audit_log'):
                with st.expander("🔍 Audit Log", expanded=False):
                    for entry in self.resume_manager._audit_log[-5:]:
                        st.code(str(entry))



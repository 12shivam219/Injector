import streamlit as st
import time
from typing import List, Dict, Any, Optional

# Removed performance monitor import - monitoring disabled
from utilities.logger import get_logger
from infrastructure.async_processing.async_integration import process_documents_async, get_async_results

logger = get_logger()

class BulkProcessor:
    def generate_all_resumes(self, uploaded_files, use_async=False):
        """Process and generate all resumes in one go (no emails)."""
        tasks = []
        for file in uploaded_files:
            data = st.session_state.resume_inputs.get(file.name, {})
            tasks.append({
                'file': file,
                'data': data
            })
        if not tasks:
            st.error("❌ No resumes are ready for generation. Please add tech stack data for at least one resume.")
            return

        if use_async and st.session_state.get('async_initialized'):
            # Use async processing
            st.info("⚡ Using high-performance async processing...")
            
            # Prepare documents for async processing
            documents = []
            for task in tasks:
                documents.append({
                    'filename': task['file'].name,
                    'text': getattr(task['file'], 'content', ''),
                    'tech_stacks': task['data'].get('tech_stacks', {}),
                    'user_data': task['data']
                })
            
            # Submit for async processing
            async_result = process_documents_async(documents)
            if async_result['success']:
                st.success(async_result['message'])
                # Removed balloon animation for better performance
                
                # Store task IDs for tracking
                st.session_state['bulk_generation_tasks'] = async_result['task_ids']
                
                # Create a polling mechanism to check results
                self._render_async_progress_monitor(async_result['task_ids'], "generation")
            else:
                st.error(async_result['message'])
                # Fallback to standard processing
                self._generate_standard(tasks)
        else:
            # Standard processing
            self._generate_standard(tasks)
    
    def _generate_standard(self, tasks):
        """Standard (synchronous) resume generation."""
        with st.spinner(f"Generating {len(tasks)} resumes..."):
            try:
                results = self.resume_manager.process_all_resumes([t['file'] for t in tasks])
                # Store previews in session state for Preview ALL
                st.session_state['all_resume_previews'] = results
                st.session_state['all_resumes_generated'] = True
                st.success(f"🎉 Bulk generation completed! {len(results)}/{len(tasks)} resumes processed successfully.")
            except Exception as e:
                st.error(f"❌ Error during bulk resume generation: {e}")
                logger.error(f"Bulk generation error: {e}")
    
    def _render_async_progress_monitor(self, task_ids: List[str], operation_type: str):
        """Render real-time progress monitor for async operations."""
        progress_container = st.empty()
        status_container = st.empty()
        
        # Create polling mechanism
        poll_interval = 0.5  # seconds
        max_polls = 120  # 60 seconds max wait
        poll_count = 0
        
        completed_results = []
        
        while poll_count < max_polls:
            # Get current results
            async_status = get_async_results(task_ids, timeout=0.01)
            
            if async_status['success']:
                completed_count = len(async_status['completed'])
                total_count = len(task_ids)
                pending_count = len(async_status['pending'])
                
                # Update progress bar
                progress = completed_count / total_count if total_count > 0 else 0
                progress_container.progress(progress, text=f"Processed: {completed_count}/{total_count}")
                
                # Update status
                if pending_count > 0:
                    status_container.info(f"⚡ Processing {pending_count} documents asynchronously... ({progress*100:.1f}% complete)")
                else:
                    status_container.success(f"✅ All {total_count} documents processed successfully!")
                    
                    # Store results
                    completed_results = list(async_status['results'].values())
                    st.session_state['all_resume_previews'] = completed_results
                    st.session_state['all_resumes_generated'] = True
                    break
            
            time.sleep(poll_interval)
            poll_count += 1
        
        if poll_count >= max_polls:
            status_container.warning("⏱️ Async processing is taking longer than expected. Check the sidebar for background task progress.")

    """Handles bulk processing operations."""

    def __init__(self, resume_manager):
        self.resume_manager = resume_manager
        self.ui = __import__("ui.components", fromlist=["UIComponents"]).UIComponents()

    # Removed performance decorator - monitoring disabled
    def process_bulk_resumes(self, ready_files, files_data, max_workers, show_progress, performance_stats, bulk_email_mode):
        """Process multiple resumes in bulk mode."""
        from infrastructure.security.validators import get_rate_limiter
        if 'user_id' not in st.session_state:
            st.session_state['user_id'] = 'anonymous'
        user_id = st.session_state.get('user_id', 'anonymous')
        rate_limiter = get_rate_limiter()
        if rate_limiter.is_rate_limited(user_id, 'bulk_processing', max_requests=5, time_window=600):
            st.error("⚠️ Bulk processing rate limit reached. Please wait before trying again.")
            return

        start_time = time.time()
        logger.log_user_action("bulk_processing", files_count=len(ready_files), max_workers=max_workers)

        st.markdown("---")
        st.markdown(f"### 🚀 Bulk Processing {len(ready_files)} Resumes...")

        # Batch status tracking
        batch_status = {f['filename']: 'pending' for f in files_data}
        batch_errors = {}
        progress_bar = st.progress(0)
        status_table = st.empty()
        processed_resumes = []
        failed_resumes = []
        def update_status():
            status_rows = []
            for fname, status in batch_status.items():
                color = {'pending': 'gray', 'processing': 'blue', 'done': 'green', 'error': 'red'}.get(status, 'gray')
                msg = f"<span style='color:{color}'><b>{fname}</b>: {status.upper()}</span>"
                if status == 'error' and fname in batch_errors:
                    msg += f"<br><span style='color:red'>Error: {batch_errors[fname]}</span>"
                status_rows.append(msg)
            status_table.markdown("<br>".join(status_rows), unsafe_allow_html=True)

        total_files = len(files_data)
        async_mode = st.checkbox("Process all in background (Celery)", key="bulk_async_mode")
        task_ids = {}
        for idx, file_data in enumerate(files_data):
            fname = file_data['filename']
            batch_status[fname] = 'processing'
            update_status()
            def progress_callback(msg, fname=fname):
                status_table.info(f"{fname}: {msg}")
            try:
                if async_mode:
                    task = self.resume_manager.process_single_resume_async(file_data)
                    task_ids[fname] = task.id
                    batch_status[fname] = 'queued'
                else:
                    result = self.resume_manager.process_single_resume(file_data, progress_callback=progress_callback)
                    if result['success']:
                        processed_resumes.append(result)
                        batch_status[fname] = 'done'
                    else:
                        failed_resumes.append(result)
                        batch_status[fname] = 'error'
                        batch_errors[fname] = result.get('error', 'Unknown error')
            except Exception as e:
                failed_resumes.append({'success': False, 'filename': fname, 'error': str(e)})
                batch_status[fname] = 'error'
                batch_errors[fname] = str(e)
            progress_bar.progress((idx + 1) / total_files)
            update_status()
        if async_mode and task_ids:
            st.info("All jobs submitted to background queue. Use the table below to check status.")
            for fname, tid in task_ids.items():
                st.write(f"{fname}: Task ID {tid}")
            if st.button("🔄 Check All Statuses", key="check_all_statuses"):
                for fname, tid in task_ids.items():
                    status = self.resume_manager.get_async_result(tid)
                    st.info(f"{fname}: {status['state']}")
                    if status['result']:
                        result = status['result']
                        if result.get('success'):
                            st.success(f"{fname}: ✅ Resume processed with {result['points_added']} points added!")
                        else:
                            st.error(f"{fname}: ❌ {result.get('error','Unknown error')}")
        # Show audit log if available
        if hasattr(self.resume_manager, '_audit_log'):
            with st.expander("🔍 Audit Log", expanded=False):
                for entry in self.resume_manager._audit_log[-10:]:
                    st.code(str(entry))

        processing_time = time.time() - start_time

        email_results = []
        if bulk_email_mode == "Send emails in parallel" and processed_resumes:
            st.markdown("---")
            st.markdown("### 📤 Sending Emails in Batch...")
            email_status = {r['filename']: 'pending' for r in processed_resumes}
            email_errors = {}
            email_progress = st.progress(0)
            email_table = st.empty()
            def update_email_status():
                rows = []
                for fname, status in email_status.items():
                    color = {'pending': 'gray', 'processing': 'blue', 'done': 'green', 'error': 'red'}.get(status, 'gray')
                    msg = f"<span style='color:{color}'><b>{fname}</b>: {status.upper()}</span>"
                    if status == 'error' and fname in email_errors:
                        msg += f"<br><span style='color:red'>Error: {email_errors[fname]}</span>"
                    rows.append(msg)
                email_table.markdown("<br>".join(rows), unsafe_allow_html=True)

            total_emails = len(processed_resumes)
            for idx, resume in enumerate(processed_resumes):
                fname = resume['filename']
                email_status[fname] = 'processing'
                update_email_status()
                try:
                    results = self.resume_manager.send_batch_emails([resume])
                    res = results[0] if results else {'success': False, 'filename': fname, 'error': 'Unknown error'}
                    email_results.append(res)
                    if res['success']:
                        email_status[fname] = 'done'
                    else:
                        email_status[fname] = 'error'
                        email_errors[fname] = res.get('error', 'Unknown error')
                except Exception as e:
                    email_results.append({'success': False, 'filename': fname, 'error': str(e)})
                    email_status[fname] = 'error'
                    email_errors[fname] = str(e)
                email_progress.progress((idx + 1) / total_emails)
                update_email_status()

        total_time = time.time() - start_time

        if show_progress:
            progress_bar.progress(1.0)
            st.success("✅ Bulk processing completed!")

        self.display_bulk_results(processed_resumes, failed_resumes, email_results, start_time, processing_time, max_workers)
        if performance_stats:
            self.display_performance_stats(total_time, processing_time, max_workers, len(processed_resumes))

    def display_bulk_results(self, processed_resumes, failed_resumes, email_results, start_time, processing_time, max_workers):
        """Display bulk processing results."""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Processed", len(processed_resumes))
        with col2:
            st.metric("Failed", len(failed_resumes))
        with col3:
            st.metric("Emails Sent", len([r for r in email_results if r['success']]))

        if failed_resumes:
            st.error(f"❌ Failed resumes: {', '.join(failed_resumes)}")
        if email_results:
            self.display_email_results(email_results)

    def display_performance_stats(self, total_time, processing_time, max_workers, num_processed):
        """Display detailed performance statistics."""
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Time (s)", f"{total_time:.2f}")
        col2.metric("Processing Time (s)", f"{processing_time:.2f}")
        col3.metric("Workers", max_workers)

    def display_email_results(self, email_results):
        """Display email sending results."""
        for result in email_results:
            status = "✅" if result['success'] else "❌"
            st.write(f"{status} {result['recipient']}: {result.get('error', 'Sent')}")

    def send_all_resumes_via_email(self, uploaded_files, use_async=False):
        """Process and send all resumes via email in one go."""
        tasks = []
        for file in uploaded_files:
            data = st.session_state.resume_inputs.get(file.name, {})
            tasks.append({
                'file': file,
                'data': data
            })
        if not tasks:
            st.error("❌ No resumes are ready for email sending. Please configure email settings and add tech stack data for at least one resume.")
            return

        if use_async and st.session_state.get('async_initialized'):
            st.info("⚡ Using high-performance async processing for email operations...")
            
            # First generate resumes asynchronously, then send emails
            documents = []
            for task in tasks:
                documents.append({
                    'filename': task['file'].name,
                    'text': getattr(task['file'], 'content', ''),
                    'tech_stacks': task['data'].get('tech_stacks', {}),
                    'user_data': task['data'],
                    'send_email': True
                })
            
            # Submit for async processing with email
            async_result = process_documents_async(documents)
            if async_result['success']:
                st.success(f"{async_result['message']} with email delivery")
                self._render_async_progress_monitor(async_result['task_ids'], "email_sending")
            else:
                st.error(async_result['message'])
                # Fallback to standard processing
                self._send_emails_standard(tasks)
        else:
            # Standard processing
            self._send_emails_standard(tasks)
    
    def _send_emails_standard(self, tasks):
        """Standard (synchronous) email sending."""
        with st.spinner(f"Sending {len(tasks)} emails..."):
            successful_emails = self.resume_manager.send_all_resumes_via_email([t['file'] for t in tasks])
        st.success(f"🎉 Bulk email operation completed! {len(successful_emails)}/{len(tasks)} emails sent successfully.")

    def render_bulk_actions(self, uploaded_files):
        """Render both bulk action buttons in the UI, and Preview ALL if available."""
        
        # Performance mode selection
        if st.session_state.get('async_initialized'):
            st.markdown("**⚡ Performance Mode:**")
            use_async = st.checkbox("Use High-Performance Async Processing (6x faster)", 
                                  value=True, key="bulk_use_async",
                                  help="Process documents simultaneously using async workers")
        else:
            use_async = False
            st.warning("Async processing not available - using standard processing")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            button_text = "⚡ Generate ALL (Async)" if use_async else "🚀 Generate ALL Resumes"
            if st.button(button_text, key="generate_all_resumes"):
                self.generate_all_resumes(uploaded_files, use_async=use_async)
        
        with col2:
            if st.button("📤 Send ALL resumes Via Email", key="send_all_resumes_email"):
                self.send_all_resumes_via_email(uploaded_files, use_async=use_async)
        
        with col3:
            if st.session_state.get('all_resumes_generated') and st.session_state.get('all_resume_previews'):
                if st.button("👁️ Preview ALL", key="preview_all_resumes"):
                    st.session_state['show_preview_all_tab'] = True




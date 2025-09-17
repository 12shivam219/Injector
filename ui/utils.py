"""
Utility functions for bulk processing checks and data preparation.
"""
import streamlit as st
from typing import List, Tuple, Dict, Any
from infrastructure.utilities.logger import get_logger

logger = get_logger()

def check_file_readiness(uploaded_files) -> Tuple[List[str], List[str]]:
    """
    Check which files are ready for bulk processing.
    Returns a tuple: (ready_files: List[str], missing_data_files: List[str]).
    """
    try:
        ready_files = []
        missing_data_files = []

        for file in uploaded_files:
            if not hasattr(file, 'name'):
                logger.warning(f"File object missing name attribute: {file}")
                continue
            # Defensive: check for resume_inputs existence
            if 'resume_inputs' not in st.session_state:
                st.session_state['resume_inputs'] = {}
            data = st.session_state.resume_inputs.get(file.name, {})
            if data.get('text', '').strip():
                ready_files.append(file.name)
            else:
                missing_data_files.append(file.name)
        
        logger.info(f"File readiness check: {len(ready_files)} ready, {len(missing_data_files)} missing data")
        return ready_files, missing_data_files
        
    except Exception as e:
        logger.error(f"Error checking file readiness: {e}")
        return [], [f.name for f in uploaded_files if hasattr(f, 'name')]

def prepare_bulk_data(uploaded_files, ready_files) -> List[Dict[str, Any]]:
    """
    Prepare a list of file data dicts for bulk processing.
    Each dict contains filename, file object, text, and email configuration.
    """
    try:
        files_data = []
        for file in uploaded_files:
            if not hasattr(file, 'name'):
                logger.warning(f"File object missing name attribute: {file}")
                continue
            if 'resume_inputs' not in st.session_state:
                st.session_state['resume_inputs'] = {}
            if file.name in ready_files:
                data = st.session_state.resume_inputs.get(file.name, {})
                files_data.append({
                    'filename': file.name,
                    'file': file,
                    'text': data.get('text', ''),
                    'recipient_email': data.get('recipient_email', ''),
                    'sender_email': data.get('sender_email', ''),
                    'sender_password': data.get('sender_password', ''),
                    'smtp_server': data.get('smtp_server', ''),
                    'smtp_port': data.get('smtp_port', 465),
                    'email_subject': data.get('email_subject', ''),
                    'email_body': data.get('email_body', '')
                })
        
        logger.info(f"Prepared bulk data for {len(files_data)} files")
        return files_data
        
    except Exception as e:
        logger.error(f"Error preparing bulk data: {e}")
        return []



"""
Streamlit cloud configuration handler
"""
import os
import streamlit as st

def setup_streamlit_env():
    """Configure Streamlit environment variables for cloud deployment"""
    # Prefer DATABASE_URL from environment; otherwise, try Streamlit secrets.
    if 'DATABASE_URL' not in os.environ:
        secret_url = st.secrets.get('DATABASE_URL', '')
        if secret_url:
            os.environ['DATABASE_URL'] = secret_url
    
    # Set encryption keys (these should be set in Streamlit Cloud Secrets)
    if 'DB_ENCRYPTION_KEY' not in os.environ:
        os.environ['DB_ENCRYPTION_KEY'] = st.secrets.get('DB_ENCRYPTION_KEY', '')
    if 'USER_DATA_ENCRYPTION_KEY' not in os.environ:
        os.environ['USER_DATA_ENCRYPTION_KEY'] = st.secrets.get('USER_DATA_ENCRYPTION_KEY', '')
    
    # Configure Streamlit server settings
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'

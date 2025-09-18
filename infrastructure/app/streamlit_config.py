"""
Streamlit cloud configuration handler
"""
import os
import streamlit as st

def setup_streamlit_env():
    """Configure Streamlit environment variables for cloud deployment"""
    # Set environment variables for database connection
    if 'DATABASE_URL' in os.environ:
        # Using provided DATABASE_URL from Streamlit Cloud
        database_url = os.environ['DATABASE_URL']
    else:
        # Fallback to local configuration
        database_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    
    # Set the database URL
    os.environ['DATABASE_URL'] = database_url
    
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
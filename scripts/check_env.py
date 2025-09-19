"""
Check environment variables in production
"""
import streamlit as st
import os
from dotenv import load_dotenv

def main():
    # Load local env for development comparison
    load_dotenv()
    
    st.title("Environment Variables Check")
    
    # Check important environment variables
    env_vars = {
        'ENVIRONMENT': os.getenv('ENVIRONMENT'),
        'DATABASE_URL': os.getenv('DATABASE_URL', '').replace(
            os.getenv('DB_PASSWORD', ''), '***' # Mask password
        ) if os.getenv('DATABASE_URL') else None,
        'DB_ENCRYPTION_KEY': 'Present' if os.getenv('DB_ENCRYPTION_KEY') else 'Missing',
        'USER_DATA_ENCRYPTION_KEY': 'Present' if os.getenv('USER_DATA_ENCRYPTION_KEY') else 'Missing',
    }
    
    st.write("### Current Environment Settings")
    for key, value in env_vars.items():
        if value:
            st.success(f"{key}: {value}")
        else:
            st.error(f"{key}: Missing")
    
    # Show running environment
    st.write("### Server Information")
    st.info(f"Running on: {os.getenv('RENDER', 'Local')}")
    st.info(f"Python Path: {os.getenv('PYTHONPATH', 'Not Set')}")

if __name__ == "__main__":
    main()
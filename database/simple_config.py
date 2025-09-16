"""
Simple database configuration for initial setup
"""
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_simple_connection_string() -> str:
    """Get a basic PostgreSQL connection string without extra parameters"""
    # Get credentials from environment variables with fallbacks
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'resume_customizer'),
        'username': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    # URL encode password to handle special characters
    password = quote_plus(config['password'])
    
    return (
        f"postgresql://{config['username']}:{password}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )
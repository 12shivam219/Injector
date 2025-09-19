"""
Fix for database password handling and URL encoding
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def fix_db_connection():
    load_dotenv()
    
    # Get credentials from environment
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'resume_customizer')
    
    # Properly encode the password for URL
    encoded_password = quote_plus(password) if password else ''
    
    # Construct database URL with properly encoded password
    db_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
    
    try:
        # Create engine and test connection
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Successfully connected to PostgreSQL!")
            print(f"Version: {version}")
            
        # Update the .env file to use the correct URL encoding
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update or add the DATABASE_URL
        database_url_line = f'DATABASE_URL=postgresql://{user}:{encoded_password}@{host}:{port}/{database}\n'
        database_url_found = False
        
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                lines[i] = database_url_line
                database_url_found = True
                break
        
        if not database_url_found:
            lines.append(database_url_line)
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
            
        print("\n✅ Updated DATABASE_URL in .env with properly encoded credentials")
        print("Connection is now working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    fix_db_connection()
"""
Fix for database password handling and URL encoding
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def fix_db_connection():
    load_dotenv()
    
# Use DATABASE_URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL environment variable is not set')
        return False
    
    try:
        # Create engine and test connection
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Successfully connected to PostgreSQL!")
            print(f"Version: {version}")
        
        print("\n✅ DATABASE_URL appears valid and reachable")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection error: {str(e)}")
        print("💡 Ensure your Neon DATABASE_URL is correct and reachable (SSL required)")
        return False
    
    return True

if __name__ == "__main__":
    fix_db_connection()
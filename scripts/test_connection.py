import os
import sys
from dotenv import load_dotenv
import psycopg2

def test_connection():
    load_dotenv()
    
    # Get Neon database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("Testing connection to Neon PostgreSQL...")
    
    try:
        # Try to connect using the connection URL
        conn = psycopg2.connect(database_url)
        print("\n✅ Successfully connected to PostgreSQL!")
        print(f"Server version: {conn.server_version}")
        
        # Run simple checks
        cur = conn.cursor()
        cur.execute('SELECT current_user, current_database();')
        user, db = cur.fetchone()
        print(f"Authenticated as: {user} | Database: {db}")
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
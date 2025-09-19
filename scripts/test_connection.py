import os
import sys
from dotenv import load_dotenv
import psycopg2

def test_connection():
    load_dotenv()
    
    # Get credentials from environment
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'resume_customizer')
    
    print(f"Testing connection with:")
    print(f"User: {user}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    
    try:
        # Try to connect
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database='postgres'  # First try connecting to default database
        )
        
        print("\n✅ Successfully connected to PostgreSQL!")
        print(f"Server version: {conn.server_version}")
        
        # Try to create our database if it doesn't exist
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if our target database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (database,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"\nCreating database '{database}'...")
            cur.execute(f'CREATE DATABASE {database};')
            print("✅ Database created successfully!")
        else:
            print(f"\nDatabase '{database}' already exists!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
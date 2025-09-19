"""Test PostgreSQL authentication methods and connection parameters."""
import subprocess
import os
import sys
from urllib.parse import quote

def get_db_settings():
    """Get database settings from .env"""
    settings = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'resume_customizer')
    }
    return settings

def test_psql_connection(settings):
    """Test connection using psql with PGPASSWORD."""
    os.environ['PGPASSWORD'] = settings['password']
    try:
        cmd = [
            'psql',
            '-h', settings['host'],
            '-p', settings['port'],
            '-U', settings['user'],
            '-d', settings['database'],
            '-c', 'SELECT current_user, inet_server_addr(), inet_server_port(), version();'
        ]
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        print("Connection successful!")
        print(result)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Connection failed: {e.output}")
        return False
    finally:
        os.environ['PGPASSWORD'] = ''

def main():
    print("Testing PostgreSQL connection...")
    print("=" * 60)
    
    settings = get_db_settings()
    masked = settings.copy()
    if settings['password']:
        masked['password'] = '***'
    print("\nConnection settings (from .env):")
    for k, v in masked.items():
        print(f"- {k}: {v}")
    
    print("\nTesting connection with psql...")
    success = test_psql_connection(settings)
    
    if not success:
        print("\nTroubleshooting steps:")
        print("1. Check if password is correct")
        print("2. Verify pg_hba.conf allows password authentication:")
        print("   - Look for a line like: host all all 127.0.0.1/32 md5")
        print("3. Try connecting with psql manually:")
        print(f"   psql -h {settings['host']} -p {settings['port']} -U {settings['user']} -d {settings['database']}")
        print("4. Check PostgreSQL logs for auth failure details")

if __name__ == '__main__':
    main()
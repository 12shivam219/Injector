"""Test PostgreSQL authentication methods and connection parameters."""
import subprocess
import os
import sys
from urllib.parse import quote

def get_db_settings():
    """Get Neon database settings from environment"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    return {'database_url': database_url}

def test_psql_connection(settings):
    """Test connection using psql with Neon connection URL."""
    try:
        cmd = [
            'psql',
            settings['database_url'],
            '-c', 'SELECT current_user, version();'
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
    print("\nTesting connection with psql...")
    success = test_psql_connection(settings)
    
    if not success:
        print("\nTroubleshooting steps:")
        print("1. Verify your Neon database URL is correct (copy from Neon dashboard)")
        print("2. Ensure your IP/project can access Neon (if access controls are configured)")
        print("3. Try connecting with psql manually using the same URL:")
        print(f"   psql {settings['database_url']}")

if __name__ == '__main__':
    main()
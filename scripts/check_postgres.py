"""Check PostgreSQL connection using the application's DatabaseConfig and health checker."""
import sys, os
sys.path.insert(0, os.getcwd())

from database.config import (
    load_env_file,
    get_database_config,
    DatabaseHealthChecker,
    get_connection_string,
)

# Load .env if present (this will reload the global config inside the module)
load_env_file('.env')

# Get a fresh DatabaseConfig instance after loading env
db_config = get_database_config()

# Build connection string
conn_str = get_connection_string()
masked = conn_str
pw = os.getenv('DB_PASSWORD') or ''
if pw:
    masked = conn_str.replace(pw, '***')
print('Connection string (masked):', masked)

# Validate config using the fresh instance
validation = db_config.validate_config()
print('Validation:', validation)

# Run health check
result = DatabaseHealthChecker.check_connection_health(conn_str)
print('\nHealth check result:')
for k, v in result.items():
    print(' ', k, ':', v)

# Additionally, attempt an authenticated query to show current DB user if reachable
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        cur_user = conn.execute(text('SELECT current_user')).scalar()
        print('\nAuthenticated as DB user:', cur_user)
    engine.dispose()
except Exception as e:
    print('\nAuthenticated user check failed:', e)

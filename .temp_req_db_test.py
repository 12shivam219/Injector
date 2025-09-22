import os
import sys
from pathlib import Path
# Ensure repo root on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Load secrets.toml values for DATABASE_URL into env if present
secrets = Path('.streamlit/secrets.toml')
if secrets.exists():
    with open(secrets, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == 'DATABASE_URL':
                    os.environ['DATABASE_URL'] = val

print('DATABASE_URL set?', 'DATABASE_URL' in os.environ)

# Try to create RequirementsManager with auto-detect
try:
    from ui.requirements_manager import RequirementsManager
    rm = RequirementsManager(use_database=None)
    print('use_database:', rm.use_database)
except Exception as e:
    print('Error instantiating RequirementsManager:', type(e).__name__, e)
    import traceback
    traceback.print_exc()

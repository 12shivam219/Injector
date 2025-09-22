import os
from pathlib import Path
# Load DATABASE_URL from .streamlit/secrets.toml
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

print('DATABASE_URL present?', 'DATABASE_URL' in os.environ)

from ui.requirements_manager import RequirementsManager
rm = RequirementsManager(use_database=None)
print('Backend in use:', 'DB' if rm.use_database else 'JSON')

if not rm.use_database:
    print('DB backend not active; stopping test')
else:
    data = {
        'job_requirement_info': {'job_title': 'DB Test Job'},
        'client_company': 'DBTestCo'
    }
    try:
        rid = rm.create_requirement(data)
        print('Created:', rid)
        # Try read back
        item = rm.get_requirement(rid)
        print('Retrieved:', item and item.get('job_requirement_info', {}).get('job_title'))
    except Exception as e:
        print('Error during DB create/get:', e)

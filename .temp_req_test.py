import os
os.chdir(os.path.dirname(__file__))
from ui.requirements_manager import RequirementsManager

# Force file-based backend
rm = RequirementsManager(use_database=False)
print('Using database?', rm.use_database)

test_data = {
    'job_requirement_info': {'job_title':'Test Job'},
    'client_company': 'Acme'
}

try:
    rid = rm.create_requirement(test_data)
    print('Created', rid)
except Exception as e:
    print('Error creating requirement:', type(e).__name__, e)

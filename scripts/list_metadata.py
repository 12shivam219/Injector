import importlib, os, sys
sys.path.insert(0, os.getcwd())
from database.base import Base

modules = [
    'database.models',
    'database.base_model',
    'database.user_models',
    'database.resume_models',
    'database.format_models',
    'database.rbac',
]
print('Importing modules:')
for m in modules:
    try:
        importlib.import_module(m)
        print('  imported', m)
    except Exception as e:
        print('  failed', m, e)

print('\nTables in shared Base metadata:')
for t in sorted(Base.metadata.tables.keys()):
    print(' -', t)

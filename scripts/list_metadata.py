import importlib, os, sys
sys.path.insert(0, os.getcwd())
from database.base import Base

modules = [
    'database.models.user',
    'database.models.resume', 
    'database.models.requirements',
    'database.models.format',
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

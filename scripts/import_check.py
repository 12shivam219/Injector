import importlib
import os, sys
# Ensure project root is on sys.path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

mods = [
    'resume_customizer.processors.point_distributor',
    'resume_customizer.processors.document_processor',
    'resume_customizer.processors.resume_processor',
    'ui.resume_tab_handler'
]
for m in mods:
    try:
        importlib.import_module(m)
        print('OK', m)
    except Exception as e:
        print('ERR', m, e)

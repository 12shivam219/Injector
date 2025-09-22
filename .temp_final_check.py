import os
os.chdir(os.path.dirname(__file__))
# Simulate running app.py import to trigger early checks
try:
    import app
    print('app imported')
except SystemExit as e:
    print('SystemExit raised as expected:', e)
except Exception as e:
    print('Import error:', type(e).__name__, e)

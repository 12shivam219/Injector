"""Validate Fernet encryption keys used by the application.

Usage:
  python scripts/validate_keys.py
"""
import os
import sys
import base64
from dotenv import load_dotenv


def is_valid_fernet_key(key: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(key.encode())
        return len(decoded) == 32
    except Exception:
        return False


def main():
    # Load local .env if present so keys stored there are validated
    load_dotenv()
    keys = ['DB_ENCRYPTION_KEY', 'USER_DATA_ENCRYPTION_KEY']
    missing = [k for k in keys if not os.getenv(k)]
    invalid = [k for k in keys if os.getenv(k) and not is_valid_fernet_key(os.getenv(k))]

    if missing:
        print('Missing keys:', ', '.join(missing))
    if invalid:
        print('Invalid keys:', ', '.join(invalid))

    if not missing and not invalid:
        print('All encryption keys present and valid.')
        return 0

    print('\nGuidance:')
    print('- Generate keys with: python scripts/generate_keys.py')
    print('- For local development, copy into .env (do not commit) or use the setup script: python scripts/setup_env.py')
    print('- For production, set these keys using your platform secret manager (Streamlit secrets, Vault, environment variables)')

    return 2


if __name__ == '__main__':
    sys.exit(main())

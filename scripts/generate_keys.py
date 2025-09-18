"""
Generate proper Fernet encryption keys
"""
import base64
import os
from cryptography.fernet import Fernet

def generate_key():
    """Generate a proper Fernet key"""
    return Fernet.generate_key().decode()

def main():
    # Generate two different keys
    db_key = generate_key()
    user_key = generate_key()
    
    print("Generated Fernet keys:")
    print(f"DB_ENCRYPTION_KEY: {db_key}")
    print(f"USER_DATA_ENCRYPTION_KEY: {user_key}")

if __name__ == "__main__":
    main()
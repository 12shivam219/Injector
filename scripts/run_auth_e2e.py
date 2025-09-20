#!/usr/bin/env python3
"""
Simple E2E check for auth register/login flows using the app's real database config.
This script:
- Loads .env (if present)
- Initializes DB connection (and schema if needed)
- Registers a random user
- Attempts login with correct and incorrect passwords
- Prints a concise summary and returns non-zero exit code on failure
"""
import sys
import uuid
import traceback

from database.config import setup_database_environment
from database.connection import initialize_database, db_manager
from infrastructure.security.auth import auth_manager


def main() -> int:
    print("[auth-e2e] Setting up database environment...")
    env = setup_database_environment()
    if not env.get("config_loaded"):
        print("[auth-e2e] Warning: .env not loaded; relying on environment variables.")
    if not env.get("config_valid"):
        print("[auth-e2e] ERROR: Database configuration is invalid:")
        for err in env.get("validation_result", {}).get("errors", []):
            print(f"  - {err}")
        return 2

    print("[auth-e2e] Initializing database connection...")
    if not initialize_database():
        print("[auth-e2e] ERROR: Failed to initialize database connection.")
        return 3

    # Best-effort schema init (safe if already exists)
    try:
        db_manager.initialize_schema()
    except Exception:
        # Schema init is best-effort; continue and let auth fail if schema truly missing
        pass

    # Use random credentials to avoid collisions
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    good_pw = "TestPass!123"
    bad_pw = "WrongPass!123"

    print(f"[auth-e2e] Registering user: {username}")
    ok, msg = auth_manager.register_user(username, good_pw, email)
    print(f"[auth-e2e] register_user -> ok={ok}, msg='{msg}'")
    if not ok:
        print("[auth-e2e] ERROR: Registration failed.")
        return 4

    print("[auth-e2e] Attempt login with correct password...")
    ok, msg = auth_manager.login(username, good_pw)
    print(f"[auth-e2e] login(correct) -> ok={ok}, msg='{msg}'")
    if not ok:
        print("[auth-e2e] ERROR: Login with correct password failed.")
        return 5

    print("[auth-e2e] Attempt login with incorrect password...")
    ok, msg = auth_manager.login(username, bad_pw)
    print(f"[auth-e2e] login(incorrect) -> ok={ok}, msg='{msg}'")
    if ok:
        print("[auth-e2e] ERROR: Login with incorrect password unexpectedly succeeded.")
        return 6

    print("[auth-e2e] Attempt logout...")
    ok, msg = auth_manager.logout()
    print(f"[auth-e2e] logout -> ok={ok}, msg='{msg}'")
    if not ok:
        print("[auth-e2e] ERROR: Logout failed.")
        return 7

    print("[auth-e2e] SUCCESS: Register/Login/Logout E2E checks passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("[auth-e2e] UNCAUGHT ERROR:\n" + traceback.format_exc())
        sys.exit(1)

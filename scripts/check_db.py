"""
Simple script to verify database configuration and connectivity.
"""
import os
import logging
from sqlalchemy import text
import sys

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.config import get_database_config, get_connection_string, validate_database_config, setup_database_environment
from database.connection import DatabaseConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Load .env if present
    env_loaded = setup_database_environment()
    logger.info(f"Environment loaded: {env_loaded['config_loaded']}, env file exists: {env_loaded['env_file_exists']}")

    # Show masked config
    from database.config import db_config
    display = db_config.get_display_config()
    display['password'] = '***' if display.get('password') else '(not set)'
    logger.info(f"Database config (masked): {display}")

    # Validate config
    validation = db_config.validate_config()
    logger.info(f"Validation result: {validation}")

    if not validation['valid']:
        logger.error("Configuration invalid. Aborting connectivity check.")
        return 1

    # Attempt to initialize connection manager
    dbm = DatabaseConnectionManager()
    success = dbm.initialize()
    if not success:
        logger.error("Failed to initialize DatabaseConnectionManager")
        return 2

    # Test a simple query
    try:
        with dbm.get_connection() as conn:
            result = conn.execute(text('SELECT version()'))
            version = result.fetchone()
            logger.info(f"Database server version: {version}")
    except Exception as e:
        logger.exception("Error executing test query: %s", e)
        return 3

    logger.info("Database connectivity check passed")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

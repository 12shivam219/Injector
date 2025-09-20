"""
Alembic migration helper for programmatic migrations on startup.

Provides a simple function `run_alembic_migrations` which will locate the
`alembic.ini` in the repository root, set the SQLAlchemy URL from the
application configuration, and run `alembic upgrade head`.
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_alembic_migrations(connection_string: Optional[str] = None) -> bool:
    """Run Alembic migrations (upgrade to head).

    Args:
        connection_string: Optional SQLAlchemy URL to set for Alembic. If not
            provided, the function will rely on alembic.ini.

    Returns:
        bool: True if migrations ran successfully (or nothing to do), False on error.
    """
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError:
        logger.warning("Alembic not installed; skipping migrations")
        return False

    try:
        # Determine repo root (two parents up from this file)
        repo_root = Path(__file__).resolve().parents[2]
        alembic_cfg_path = repo_root / 'alembic.ini'

        if not alembic_cfg_path.exists():
            logger.info("No alembic.ini found; skipping migrations")
            return True

        cfg = Config(str(alembic_cfg_path))

        if connection_string:
            cfg.set_main_option('sqlalchemy.url', connection_string)

        logger.info("Running Alembic migrations (upgrade head)")
        command.upgrade(cfg, 'head')
        logger.info("Alembic migrations applied successfully")
        # After migrations, ensure any critical columns that may be missing
        try:
            from sqlalchemy import create_engine, text
            if connection_string:
                engine = create_engine(connection_string)
            else:
                # Use URL from alembic config if present
                engine_url = cfg.get_main_option('sqlalchemy.url')
                engine = create_engine(engine_url) if engine_url else None

            if engine is not None:
                _ensure_critical_columns(engine)
                engine.dispose()
        except Exception as e:
            logger.warning(f"Could not run post-migration column checks: {e}")
        return True
    except Exception as e:
        logger.error(f"Failed to run Alembic migrations: {e}")
        return False


def _ensure_critical_columns(engine):
    """Ensure critical columns exist; add them if missing.

    This is a safety fallback for environments where migrations didn't
    add new columns but the application models expect them.
    Currently ensures `user_sessions.session_id` exists.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'user_sessions' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('user_sessions')]
        with engine.connect() as conn:
            if 'session_id' not in cols:
                try:
                    logger.info('Adding missing column user_sessions.session_id')
                    conn.execute(text("ALTER TABLE user_sessions ADD COLUMN session_id VARCHAR(255);"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_user_sessions_session_id ON user_sessions (session_id);"))
                    logger.info('Added user_sessions.session_id successfully')
                except Exception as e:
                    logger.error(f'Failed to add user_sessions.session_id: {e}')
    else:
        logger.info('user_sessions table not present; skipping critical column checks')

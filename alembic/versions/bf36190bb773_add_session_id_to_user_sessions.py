"""add_session_id_to_user_sessions

Revision ID: bf36190bb773
Revises: 40afbb358e14
Create Date: 2025-09-20 09:39:33.050333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bf36190bb773'
down_revision: Union[str, Sequence[str], None] = '40afbb358e14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure user_sessions.session_id exists and is indexed/unique."""
    # Add column if it doesn't exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='user_sessions' AND column_name='session_id'
            ) THEN
                ALTER TABLE user_sessions ADD COLUMN session_id VARCHAR(255);
            END IF;
        END$$;
        """
    )

    # Backfill any NULLs with generated UUIDs to satisfy NOT NULL
    op.execute(
        """
        UPDATE user_sessions
        SET session_id = gen_random_uuid()::text
        WHERE session_id IS NULL;
        """
    )

    # Add unique constraint if not exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'user_sessions' AND c.conname = 'uq_user_sessions_session_id'
            ) THEN
                ALTER TABLE user_sessions ADD CONSTRAINT uq_user_sessions_session_id UNIQUE (session_id);
            END IF;
        END$$;
        """
    )

    # Add index on session_id if not exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'ix_user_sessions_session_id'
            ) THEN
                CREATE INDEX ix_user_sessions_session_id ON user_sessions (session_id);
            END IF;
        END$$;
        """
    )

    # Ensure last_activity index exists (used in code)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'ix_user_sessions_last_activity'
            ) THEN
                CREATE INDEX ix_user_sessions_last_activity ON user_sessions (last_activity);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """Best-effort downgrade: drop unique/index, keep column to avoid data loss."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'user_sessions' AND c.conname = 'uq_user_sessions_session_id'
            ) THEN
                ALTER TABLE user_sessions DROP CONSTRAINT uq_user_sessions_session_id;
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_user_sessions_session_id') THEN
                DROP INDEX ix_user_sessions_session_id;
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_user_sessions_last_activity') THEN
                DROP INDEX ix_user_sessions_last_activity;
            END IF;
        END$$;
        """
    )

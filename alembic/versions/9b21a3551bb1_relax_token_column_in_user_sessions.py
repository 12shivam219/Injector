"""relax_token_column_in_user_sessions

Revision ID: 9b21a3551bb1
Revises: bf36190bb773
Create Date: 2025-09-20 09:40:58.247911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b21a3551bb1'
down_revision: Union[str, Sequence[str], None] = 'bf36190bb773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Relax NOT NULL on user_sessions.token if present; set default for future inserts."""
    # Drop NOT NULL if column exists and is NOT NULL
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='user_sessions' AND column_name='token'
            ) THEN
                -- Drop NOT NULL constraint
                BEGIN
                    ALTER TABLE user_sessions ALTER COLUMN token DROP NOT NULL;
                EXCEPTION WHEN others THEN
                    -- ignore if already nullable
                    NULL;
                END;
                -- Set default if none exists
                BEGIN
                    ALTER TABLE user_sessions ALTER COLUMN token SET DEFAULT gen_random_uuid()::text;
                EXCEPTION WHEN others THEN
                    -- If gen_random_uuid is not available, set empty string default
                    ALTER TABLE user_sessions ALTER COLUMN token SET DEFAULT '';
                END;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """No-op downgrade to avoid reintroducing NOT NULL constraints."""
    pass
    """Downgrade schema."""
    pass

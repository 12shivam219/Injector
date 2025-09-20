"""drop_token_from_user_sessions

Revision ID: e77481e47db0
Revises: 9b21a3551bb1
Create Date: 2025-09-20 09:44:55.515995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e77481e47db0'
down_revision: Union[str, Sequence[str], None] = '9b21a3551bb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop legacy token column from user_sessions if it exists."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='user_sessions' AND column_name='token'
            ) THEN
                ALTER TABLE user_sessions DROP COLUMN token;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """Recreate token column as nullable (no default) for compatibility."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='user_sessions' AND column_name='token'
            ) THEN
                ALTER TABLE user_sessions ADD COLUMN token VARCHAR(255);
            END IF;
        END$$;
        """
    )

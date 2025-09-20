"""Add version column to resume_formats table

Revision ID: 2023_09_21_add_version_column
Create Date: 2023-09-21 02:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2023_09_21_add_version_column'
down_revision = '2023_09_21_add_version_default'
branch_labels = None
depends_on = None

def upgrade():
    # Add version column with default value
    op.execute("""
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE resume_formats ADD COLUMN version VARCHAR(10) NOT NULL DEFAULT '1.0';
            EXCEPTION
                WHEN duplicate_column THEN
                    NULL;
            END;
        END $$;
    """)

def downgrade():
    op.drop_column('resume_formats', 'version')
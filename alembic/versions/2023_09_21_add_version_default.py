"""Add default version to resume_formats table

Revision ID: 2023_09_21_add_version_default
Create Date: 2023-09-21 02:44:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2023_09_21_add_version_default'
down_revision = '2023_09_21_fix_format_id'
branch_labels = None
depends_on = None

def upgrade():
    # First set a default value for existing rows
    op.execute("UPDATE resume_formats SET version = '1.0' WHERE version IS NULL")
    
    # Then add the not-null constraint with default
    op.alter_column('resume_formats', 'version',
        existing_type=sa.String(10),
        nullable=False,
        server_default=sa.text("'1.0'")
    )

def downgrade():
    op.alter_column('resume_formats', 'version',
        existing_type=sa.String(10),
        nullable=True,
        server_default=None
    )
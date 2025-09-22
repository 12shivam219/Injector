"""add is_active and version to requirements

Revision ID: 20250922_addcols01
Revises: 1ce85f765793
Create Date: 2025-09-22 06:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20250922_addcols01'
down_revision = '1ce85f765793'
branch_labels = None
depends_on = None


def upgrade():
    """Add columns and create indexes / constraints to match models.

    This migration is written defensively: it checks for existing columns
    and indexes so it can be applied safely on databases that have already
    been partially modified.
    """
    conn = op.get_bind()

    # Add is_active column if missing
    col = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='requirements' AND column_name='is_active'"
    )).fetchone()
    if not col:
        op.add_column('requirements', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))

    # Add version column if missing
    col = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='requirements' AND column_name='version'"
    )).fetchone()
    if not col:
        op.add_column('requirements', sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')))

    # Ensure existing rows have sensible values for req_status
    try:
        conn.execute(text("UPDATE requirements SET req_status = 'New' WHERE req_status IS NULL"))
    except Exception:
        # Best-effort; if table is empty or locked just continue
        pass

    # Ensure req_status has a server default
    try:
        conn.execute(text("ALTER TABLE requirements ALTER COLUMN req_status SET DEFAULT 'New'"))
    except Exception:
        pass

    # Create helpful indexes (use CONCURRENTLY to avoid locks when possible)
    # Wrap in an autocommit block because CREATE INDEX CONCURRENTLY cannot run inside a transaction
    index_sqls = [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_search ON requirements USING gin(to_tsvector('english', coalesce(job_title,'') || ' ' || coalesce(client_company,'')))",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_tech_stack ON requirements USING gin(tech_stack)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_requirements_created_status ON requirements (created_at DESC, req_status)",
    ]

    try:
        with conn.execution_options(isolation_level='AUTOCOMMIT'):
            for sql in index_sqls:
                try:
                    conn.execute(text(sql))
                except Exception:
                    # If index creation fails (permissions, existing index, etc.) keep going
                    pass
    except Exception:
        # If autocommit mode isn't available, fallback to non-concurrent creation
        for sql in index_sqls:
            try:
                conn.execute(text(sql.replace('CONCURRENTLY ', '')))
            except Exception:
                pass


def downgrade():
    conn = op.get_bind()

    # Drop indexes if they exist
    try:
        with conn.execution_options(isolation_level='AUTOCOMMIT'):
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_search"))
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_tech_stack"))
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_created_status"))
    except Exception:
        # Fallback: non-concurrent drop
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_search"))
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_tech_stack"))
            conn.execute(text("DROP INDEX IF EXISTS idx_requirements_created_status"))
        except Exception:
            pass

    # Drop columns if they exist
    col = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='requirements' AND column_name='version'"
    )).fetchone()
    if col:
        op.drop_column('requirements', 'version')

    col = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='requirements' AND column_name='is_active'"
    )).fetchone()
    if col:
        op.drop_column('requirements', 'is_active')

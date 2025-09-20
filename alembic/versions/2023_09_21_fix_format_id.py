"""Fix format_id column type in resume_format_matches table

Revision ID: 2023_09_21_fix_format_id
Create Date: 2023-09-21 02:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2023_09_21_fix_format_id'
down_revision = 'e77481e47db0'  # The latest migration ID
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Drop all foreign key constraints from all related tables
    op.execute("""
        DO $$
        DECLARE
            r record;
        BEGIN
            FOR r IN (
                SELECT conname, conrelid::regclass::text as tablename
                FROM pg_constraint
                WHERE contype = 'f'
                AND (
                    conrelid = 'resume_format_matches'::regclass
                    OR conrelid = 'format_elements'::regclass
                )
                AND confrelid = 'resume_formats'::regclass
            )
            LOOP
                EXECUTE 'ALTER TABLE ' || quote_ident(r.tablename) || ' DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$;
    """)
    
    # Update column types in all related tables
    op.execute('ALTER TABLE resume_format_matches ALTER COLUMN format_id TYPE varchar(36) USING format_id::text')
    op.execute('ALTER TABLE format_elements ALTER COLUMN format_id TYPE varchar(36) USING format_id::text')
    op.execute('ALTER TABLE resume_formats ALTER COLUMN id TYPE varchar(36) USING id::text')
    
    # Add back the foreign key constraints
    op.create_foreign_key(
        'fk_resume_format_matches_format_id_resume_formats',
        'resume_format_matches',
        'resume_formats',
        ['format_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_format_elements_format_id_resume_formats',
        'format_elements',
        'resume_formats',
        ['format_id'],
        ['id']
    )

def downgrade():
    # Create a new column with the old type
    op.add_column('resume_format_matches', sa.Column('new_format_id', sa.Integer()))
    
    # Copy data from the string column to the integer column
    op.execute('UPDATE resume_format_matches SET new_format_id = format_id::integer')
    
    # Drop the old column and rename the new one
    op.drop_column('resume_format_matches', 'format_id')
    op.alter_column('resume_format_matches', 'new_format_id', new_column_name='format_id')
    
    # Add the foreign key constraint
    op.create_foreign_key(
        'fk_resume_format_matches_format_id_resume_formats',
        'resume_format_matches',
        'resume_formats',
        ['format_id'],
        ['id']
    )
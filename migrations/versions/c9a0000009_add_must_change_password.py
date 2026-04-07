"""Add MustChangePassword column to Employees.

Revision ID: c9a0000009
Revises: c8a0000008
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c9a0000009'
down_revision = 'c8a0000008'
branch_labels = None
depends_on = None

def _column_exists(conn, table_name, column_name):
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())

def upgrade():
    conn = op.get_bind()
    if not _column_exists(conn, 'Employees', 'MustChangePassword'):
        with op.batch_alter_table('Employees') as batch_op:
            batch_op.add_column(sa.Column('MustChangePassword', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    conn = op.get_bind()
    if _column_exists(conn, 'Employees', 'MustChangePassword'):
        with op.batch_alter_table('Employees') as batch_op:
            batch_op.drop_column('MustChangePassword')

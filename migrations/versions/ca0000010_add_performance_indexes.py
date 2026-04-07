"""Add performance indexes for common query patterns.

Revision ID: ca0000010
Revises: c9a0000009
Create Date: 2026-04-07
"""
from alembic import op
from sqlalchemy import text

revision = 'ca0000010'
down_revision = 'c9a0000009'
branch_labels = None
depends_on = None

def _index_exists(conn, index_name):
    result = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"))
    return result.fetchone() is not None

def upgrade():
    conn = op.get_bind()
    if not _index_exists(conn, 'idx_absences_employee_date'):
        op.create_index('idx_absences_employee_date', 'Absences', ['EmployeeId', 'StartDate', 'EndDate'])
    if not _index_exists(conn, 'idx_shifts_date_employee'):
        op.create_index('idx_shifts_date_employee', 'ShiftAssignments', ['Date', 'EmployeeId'])
    if not _index_exists(conn, 'idx_shifts_date_type'):
        op.create_index('idx_shifts_date_type', 'ShiftAssignments', ['Date', 'ShiftTypeId'])

def downgrade():
    op.drop_index('idx_absences_employee_date', 'Absences')
    op.drop_index('idx_shifts_date_employee', 'ShiftAssignments')
    op.drop_index('idx_shifts_date_type', 'ShiftAssignments')

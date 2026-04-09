"""Ensure PlanningJobs table exists (idempotent repair migration).

This migration guarantees the PlanningJobs table is present regardless of
which path the database took through the migration history.

Background: migration cb0000011 was inserted between ca0000010 and cc0000012
after some databases had already been stamped at cc0000012 (the old head).
Those databases skipped cb0000011 and therefore never got the PlanningJobs
table.  This migration fixes that by creating the table only when it is absent.

Revision ID: cd0000013
Revises: cc0000012
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'cd0000013'
down_revision = 'cc0000012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Guard: skip if table already exists (idempotent)
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='PlanningJobs'"
        )
    )
    if result.scalar() > 0:
        return

    op.create_table(
        'PlanningJobs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.Text(), nullable=True),
        sa.Column('finished_at', sa.Text(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS PlanningJobs")

"""Add PlanningJobs table for persistent job storage.

Revision ID: cb0000011
Revises: ca0000010
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = 'cb0000011'
down_revision = 'ca0000010'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('PlanningJobs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.Text(), nullable=True),
        sa.Column('finished_at', sa.Text(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('PlanningJobs')

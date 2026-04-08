"""Add Disponent role to AspNetRoles.

Revision ID: cc0000012
Revises: cb0000011
Create Date: 2026-04-08
"""
from alembic import op
from sqlalchemy import text

revision = 'cc0000012'
down_revision = 'cb0000011'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            "INSERT OR IGNORE INTO AspNetRoles (Id, Name, NormalizedName) "
            "VALUES ('disponent-role-id', 'Disponent', 'DISPONENT')"
        )
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM AspNetRoles WHERE Id = 'disponent-role-id'")
    )

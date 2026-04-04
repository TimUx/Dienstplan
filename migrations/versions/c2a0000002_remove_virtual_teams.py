"""Remove IsVirtual column from Teams table.

Virtual teams are no longer used.  SQLite does not support DROP COLUMN directly
(before version 3.35), so the table is recreated without the column.

Revision ID: c2a0000002
Revises: c1a0000001
Create Date: 2024-01-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c2a0000002'
down_revision = 'c1a0000001'
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "Teams", "IsVirtual"):
        # Already removed – nothing to do
        return

    # Use batch mode to recreate the Teams table without IsVirtual
    with op.batch_alter_table("Teams") as batch_op:
        batch_op.drop_column("IsVirtual")


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "Teams", "IsVirtual"):
        return

    with op.batch_alter_table("Teams") as batch_op:
        batch_op.add_column(
            sa.Column("IsVirtual", sa.Integer(), nullable=False, server_default="0")
        )

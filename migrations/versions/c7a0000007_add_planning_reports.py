"""Add PlanningReports table.

Stores serialised PlanningReport JSON for each solved planning month so that
the API can retrieve and serve it later.

Revision ID: c7a0000007
Revises: c6a0000006
Create Date: 2024-01-07
"""
from alembic import op
from sqlalchemy import text

revision = 'c7a0000007'
down_revision = 'c6a0000006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Guard: skip if table already exists (idempotent)
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='PlanningReports'"
        )
    )
    if result.scalar() > 0:
        return

    conn.execute(text("""
        CREATE TABLE PlanningReports (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            year       INTEGER NOT NULL,
            month      INTEGER NOT NULL,
            status     TEXT    NOT NULL,
            created_at TEXT    NOT NULL,
            report_json TEXT   NOT NULL,
            UNIQUE (year, month)
        )
    """))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS PlanningReports")

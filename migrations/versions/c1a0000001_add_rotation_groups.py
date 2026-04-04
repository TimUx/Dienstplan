"""Add rotation groups support to Teams table.

Creates RotationGroups and RotationGroupShifts tables (if absent) and adds
RotationGroupId to Teams.  Populates a default "Standard F→N→S" rotation group
and links all existing teams to it.

Revision ID: c1a0000001
Revises: –
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c1a0000001'
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table_name},
    )
    return result.scalar() > 0


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create RotationGroups table if it does not yet exist
    if not _table_exists(conn, "RotationGroups"):
        op.create_table(
            "RotationGroups",
            sa.Column("Id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("Name", sa.Text(), nullable=False),
            sa.Column("Description", sa.Text()),
            sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "CreatedAt",
                sa.Text(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("CreatedBy", sa.Text()),
            sa.Column("ModifiedAt", sa.Text()),
            sa.Column("ModifiedBy", sa.Text()),
        )

    # 2. Create RotationGroupShifts table if it does not yet exist
    if not _table_exists(conn, "RotationGroupShifts"):
        op.create_table(
            "RotationGroupShifts",
            sa.Column("Id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("RotationGroupId", sa.Integer(), nullable=False),
            sa.Column("ShiftTypeId", sa.Integer(), nullable=False),
            sa.Column("RotationOrder", sa.Integer(), nullable=False),
            sa.Column(
                "CreatedAt",
                sa.Text(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("CreatedBy", sa.Text()),
            sa.UniqueConstraint("RotationGroupId", "ShiftTypeId"),
        )

    # 3. Add RotationGroupId column to Teams if absent
    if not _column_exists(conn, "Teams", "RotationGroupId"):
        with op.batch_alter_table("Teams") as batch_op:
            batch_op.add_column(
                sa.Column("RotationGroupId", sa.Integer(), nullable=True)
            )

    # 4. Create the default rotation group (once only)
    existing = conn.execute(
        text("SELECT COUNT(*) FROM RotationGroups WHERE Name = 'Standard F\u2192N\u2192S'")
    ).scalar()

    if existing == 0:
        conn.execute(
            text(
                "INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy) "
                "VALUES ('Standard F\u2192N\u2192S', "
                "'Standard 3-Schicht-Rotation: Fr\u00fChdienst \u2192 Nachtdienst \u2192 Sp\u00e4tdienst', "
                "1, 'System Migration')"
            )
        )

    group_id = conn.execute(
        text("SELECT Id FROM RotationGroups WHERE Name = 'Standard F\u2192N\u2192S'")
    ).scalar()

    # 5. Populate RotationGroupShifts (once per shift code)
    shift_rows = conn.execute(
        text("SELECT Id, Code FROM ShiftTypes WHERE Code IN ('F', 'N', 'S')")
    ).fetchall()
    shifts = {row[1]: row[0] for row in shift_rows}

    for code, order in [("F", 1), ("N", 2), ("S", 3)]:
        if code in shifts:
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO RotationGroupShifts "
                    "(RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy) "
                    "VALUES (:gid, :sid, :ord, 'System Migration')"
                ),
                {"gid": group_id, "sid": shifts[code], "ord": order},
            )

    # 6. Link all teams that have no rotation group yet
    conn.execute(
        text(
            "UPDATE Teams SET RotationGroupId = :gid WHERE RotationGroupId IS NULL"
        ),
        {"gid": group_id},
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    with op.batch_alter_table("Teams") as batch_op:
        batch_op.drop_column("RotationGroupId")
    op.drop_table("RotationGroupShifts")
    op.drop_table("RotationGroups")

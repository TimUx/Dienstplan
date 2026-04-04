"""Add MaxConsecutiveDays column to ShiftTypes.

Adds a per-shift-type limit for consecutive working days and seeds the values
from the GlobalSettings table (MaxConsecutiveShifts / MaxConsecutiveNightShifts).

Revision ID: c4a0000004
Revises: c3a0000003
Create Date: 2024-01-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c4a0000004'
down_revision = 'c3a0000003'
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "ShiftTypes", "MaxConsecutiveDays"):
        return  # Already applied

    # Add column with a safe default
    with op.batch_alter_table("ShiftTypes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "MaxConsecutiveDays",
                sa.Integer(),
                nullable=False,
                server_default="6",
            )
        )

    # Read GlobalSettings to seed per-shift values
    row = conn.execute(
        text(
            "SELECT MaxConsecutiveShifts, MaxConsecutiveNightShifts "
            "FROM GlobalSettings WHERE Id = 1"
        )
    ).fetchone()

    max_general = row[0] if row else 6
    max_night = row[1] if row else 3

    shift_rows = conn.execute(
        text("SELECT Id, Code FROM ShiftTypes")
    ).fetchall()

    for shift_id, shift_code in shift_rows:
        days = max_night if shift_code == "N" else max_general
        conn.execute(
            text(
                "UPDATE ShiftTypes SET MaxConsecutiveDays = :days WHERE Id = :id"
            ),
            {"days": days, "id": shift_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("ShiftTypes") as batch_op:
        batch_op.drop_column("MaxConsecutiveDays")

"""Add unique constraint on ShiftAssignments(EmployeeId, Date).

Prevents double shift assignments for the same employee on the same day.
If duplicate assignments already exist they are cleaned up first (keeping the
oldest record per employee/date pair).

Revision ID: c6a0000006
Revises: c5a0000005
Create Date: 2024-01-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c6a0000006'
down_revision = 'c5a0000005'
branch_labels = None
depends_on = None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='index' AND name=:n"
        ),
        {"n": index_name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    index_name = "idx_shiftassignments_unique_employee_date"

    if _index_exists(conn, index_name):
        return  # Already applied

    # Remove duplicate shift assignments (keep the oldest record per day)
    duplicates = conn.execute(
        text(
            "SELECT EmployeeId, Date FROM ShiftAssignments "
            "GROUP BY EmployeeId, Date HAVING COUNT(*) > 1"
        )
    ).fetchall()

    for emp_id, date in duplicates:
        # Fetch all IDs for this employee/date, ordered oldest first
        ids = conn.execute(
            text(
                "SELECT Id FROM ShiftAssignments "
                "WHERE EmployeeId = :eid AND Date = :d ORDER BY Id"
            ),
            {"eid": emp_id, "d": date},
        ).fetchall()

        # Delete all but the oldest
        for row in ids[1:]:
            conn.execute(
                text("DELETE FROM ShiftAssignments WHERE Id = :id"),
                {"id": row[0]},
            )

    # Add the unique index
    conn.execute(
        text(
            f"CREATE UNIQUE INDEX {index_name} "
            "ON ShiftAssignments(EmployeeId, Date)"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "idx_shiftassignments_unique_employee_date",
        table_name="ShiftAssignments",
    )

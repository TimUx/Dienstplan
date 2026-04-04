"""Remove IsSpringer from Employees and IsSpringerAssignment from ShiftAssignments.

Springers are not a fixed role – any team member can act as a replacement
automatically based on availability, rotation rules, and rest-time constraints.

Revision ID: c8a0000008
Revises: c7a0000007
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c8a0000008'
down_revision = 'c7a0000007'
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    conn = op.get_bind()

    # --- Employees: drop IsSpringer column ---
    if _column_exists(conn, "Employees", "IsSpringer"):
        with op.batch_alter_table("Employees") as batch_op:
            batch_op.drop_column("IsSpringer")

    # --- ShiftAssignments: drop IsSpringerAssignment column ---
    if _column_exists(conn, "ShiftAssignments", "IsSpringerAssignment"):
        with op.batch_alter_table("ShiftAssignments") as batch_op:
            batch_op.drop_column("IsSpringerAssignment")

    # --- Sample data: update former Springer employees to Techniker ---
    conn.execute(
        text("UPDATE Employees SET Funktion = 'Techniker' WHERE Funktion = 'Springer'")
    )
    conn.execute(
        text("UPDATE Employees SET Personalnummer = 'PN005' WHERE Personalnummer = 'S001'")
    )
    conn.execute(
        text("UPDATE Employees SET Personalnummer = 'PN010' WHERE Personalnummer = 'S002'")
    )
    conn.execute(
        text("UPDATE Employees SET Personalnummer = 'PN015' WHERE Personalnummer = 'S003'")
    )


def downgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "Employees", "IsSpringer"):
        with op.batch_alter_table("Employees") as batch_op:
            batch_op.add_column(
                sa.Column("IsSpringer", sa.Integer(), nullable=False, server_default="0")
            )

    if not _column_exists(conn, "ShiftAssignments", "IsSpringerAssignment"):
        with op.batch_alter_table("ShiftAssignments") as batch_op:
            batch_op.add_column(
                sa.Column("IsSpringerAssignment", sa.Integer(), nullable=False, server_default="0")
            )

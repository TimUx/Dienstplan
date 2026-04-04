"""Add custom absence types feature.

Creates the AbsenceTypes table, inserts the three standard system types
(U, AU, L), and adds an AbsenceTypeId foreign-key column to the Absences table.

Revision ID: c3a0000003
Revises: c2a0000002
Create Date: 2024-01-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c3a0000003'
down_revision = 'c2a0000002'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table_name},
    )
    return result.scalar() > 0


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create AbsenceTypes table if absent
    if not _table_exists(conn, "AbsenceTypes"):
        op.create_table(
            "AbsenceTypes",
            sa.Column("Id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("Name", sa.Text(), nullable=False),
            sa.Column("Code", sa.Text(), nullable=False, unique=True),
            sa.Column("ColorCode", sa.Text(), nullable=False, server_default="'#E0E0E0'"),
            sa.Column("IsSystemType", sa.Integer(), nullable=False, server_default="0"),
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

    # 2. Insert standard absence types (idempotent via INSERT OR IGNORE)
    standard_types = [
        ("Urlaub", "U", "#90EE90", 1),
        ("Krank / AU", "AU", "#FFB6C1", 1),
        ("Lehrgang", "L", "#87CEEB", 1),
    ]
    for name, code, color, is_system in standard_types:
        conn.execute(
            text(
                "INSERT OR IGNORE INTO AbsenceTypes (Name, Code, ColorCode, IsSystemType) "
                "VALUES (:name, :code, :color, :sys)"
            ),
            {"name": name, "code": code, "color": color, "sys": is_system},
        )

    # 3. Add AbsenceTypeId column to Absences if absent
    if not _column_exists(conn, "Absences", "AbsenceTypeId"):
        with op.batch_alter_table("Absences") as batch_op:
            batch_op.add_column(
                sa.Column("AbsenceTypeId", sa.Integer(), nullable=True)
            )

        # Migrate existing rows: map legacy Type integer to the new AbsenceTypeId
        conn.execute(
            text(
                "UPDATE Absences SET AbsenceTypeId = ("
                "  SELECT Id FROM AbsenceTypes"
                "  WHERE (AbsenceTypes.Code = 'U'  AND Absences.Type = 2)"
                "     OR (AbsenceTypes.Code = 'AU' AND Absences.Type = 1)"
                "     OR (AbsenceTypes.Code = 'L'  AND Absences.Type = 3)"
                ")"
            )
        )

    # 4. Ensure index exists
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_absences_type "
            "ON Absences(AbsenceTypeId)"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("Absences") as batch_op:
        batch_op.drop_column("AbsenceTypeId")
    op.drop_table("AbsenceTypes")

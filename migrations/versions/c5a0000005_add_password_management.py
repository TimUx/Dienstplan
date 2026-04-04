"""Add password management tables.

Creates EmailSettings (SMTP configuration) and PasswordResetTokens tables.

Revision ID: c5a0000005
Revises: c4a0000004
Create Date: 2024-01-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'c5a0000005'
down_revision = 'c4a0000004'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table_name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # EmailSettings table
    if not _table_exists(conn, "EmailSettings"):
        op.create_table(
            "EmailSettings",
            sa.Column(
                "Id",
                sa.Integer(),
                primary_key=True,
                comment="Singleton row enforced by CHECK (Id = 1)",
            ),
            sa.Column("SmtpHost", sa.Text()),
            sa.Column("SmtpPort", sa.Integer(), server_default="587"),
            sa.Column("UseSsl", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "RequiresAuthentication",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column("Username", sa.Text()),
            sa.Column("Password", sa.Text()),
            sa.Column("SenderEmail", sa.Text()),
            sa.Column("SenderName", sa.Text()),
            sa.Column("ReplyToEmail", sa.Text()),
            sa.Column("IsEnabled", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "CreatedAt",
                sa.Text(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("ModifiedAt", sa.Text()),
            sa.Column("ModifiedBy", sa.Text()),
        )

    # PasswordResetTokens table
    if not _table_exists(conn, "PasswordResetTokens"):
        op.create_table(
            "PasswordResetTokens",
            sa.Column("Id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("EmployeeId", sa.Integer(), nullable=False),
            sa.Column("Token", sa.Text(), nullable=False, unique=True),
            sa.Column("ExpiresAt", sa.Text(), nullable=False),
            sa.Column("IsUsed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("UsedAt", sa.Text()),
            sa.Column(
                "CreatedAt",
                sa.Text(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["EmployeeId"], ["Employees.Id"]),
        )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_passwordresettokens_token "
                "ON PasswordResetTokens(Token)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_passwordresettokens_employee "
                "ON PasswordResetTokens(EmployeeId, IsUsed, ExpiresAt)"
            )
        )


def downgrade() -> None:
    op.drop_table("PasswordResetTokens")
    op.drop_table("EmailSettings")

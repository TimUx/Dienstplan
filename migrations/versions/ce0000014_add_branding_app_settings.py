"""Add AppSettings table and default branding values.

Revision ID: ce0000014
Revises: cd0000013
Create Date: 2026-04-18
"""
from alembic import op
from sqlalchemy import text

revision = 'ce0000014'
down_revision = 'cd0000013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS AppSettings (
                Key TEXT PRIMARY KEY,
                Value TEXT,
                ModifiedAt TEXT,
                ModifiedBy TEXT
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO AppSettings (Key, Value, ModifiedBy)
            VALUES ('CompanyNameFooter', 'Fritz Winter Eisengießerei GmbH & Co. KG', 'system')
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO AppSettings (Key, Value, ModifiedBy)
            VALUES ('HeaderLogoUrl', '/images/fw-logo-white.svg', 'system')
            """
        )
    )

    # Update standard absence colors to neutral gray tones.
    conn.execute(
        text(
            """
            UPDATE AbsenceTypes
            SET ColorCode = '#9E9E9E'
            WHERE Code = 'U' AND IsSystemType = 1
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE AbsenceTypes
            SET ColorCode = '#BDBDBD'
            WHERE Code = 'L' AND IsSystemType = 1
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS AppSettings"))

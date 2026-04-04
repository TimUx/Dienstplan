"""
Alembic environment configuration for Dienstplan.

Uses SQLAlchemy for connection management (Alembic dependency) but no ORM models.
All migrations use raw SQL via op.execute() and op.batch_alter_table().
"""

import os
from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic Config object providing access to values in alembic.ini
config = context.config

# Allow overriding the database URL via environment variable
db_url = os.environ.get("DIENSTPLAN_DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# No ORM metadata – we use raw SQL in all revisions
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

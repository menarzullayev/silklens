"""Alembic environment.

This module sets up the migration context. ``target_metadata`` is the union of
every bounded-context's ORM metadata: importing each context's ``models`` module
registers its tables on ``Base.metadata`` which Alembic then sees.

Migrations themselves live under ``alembic/versions/`` and are generated either
by hand (preferred for SilkLens given DB-level features Alembic autogenerate
can't infer: RLS, partitions, custom check constraints, GIN/GIST/HNSW indexes)
or via ``alembic revision --autogenerate`` followed by manual review.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make ``src.*`` importable from this script.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from src.core.database import Base  # noqa: E402
from src.core.settings import get_settings  # noqa: E402

# Import every bounded context's models so its metadata is registered.
# Each domain module exposes a ``models`` package; importing it has the side
# effect of registering ORM classes on ``Base.metadata``.
import src.domain.heritage.models  # noqa: F401, E402
import src.domain.identity.models  # noqa: F401, E402
# Additional domains imported in later FAZA work.

config = context.config

# Override the alembic.ini DSN with the runtime-resolved one.
config.set_main_option("sqlalchemy.url", get_settings().database_url_sync)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj: object, name: str | None, type_: str, *_: object) -> bool:
    """Skip PostgreSQL extension-owned objects from autogenerate."""
    if type_ == "table" and name and name.startswith("pg_"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

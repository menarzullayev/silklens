"""Heritage bounded-context ORM models.

The full schema (~38 tables) is specified in
``docs/architecture/01-core-domain.md``. Models are added here as their
migrations land. This file exists at FAZA 1 only to register the module so
``alembic env.py`` can import it without crashing; concrete table definitions
land in FAZA 1 Hafta 1-2 migrations.
"""

from __future__ import annotations

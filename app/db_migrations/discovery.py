"""Load migration modules from ``app.db_migrations.migrations`` (explicit, ordered)."""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

import app.db_migrations.migrations as migrations_pkg


def iter_migration_modules() -> list[ModuleType]:
    """Return migration modules sorted by ``MIGRATION_ID`` (``YYYYMMDD_`` sorts in time order)."""
    loaded: list[ModuleType] = []
    for _finder, name, ispkg in pkgutil.iter_modules(migrations_pkg.__path__):
        # Leading underscore: templates / scratch (e.g. ``_template_example``).
        if ispkg or name.startswith("_"):
            continue
        mod = importlib.import_module(f"app.db_migrations.migrations.{name}")
        if not hasattr(mod, "MIGRATION_ID") or not hasattr(mod, "apply"):
            continue
        loaded.append(mod)
    return sorted(loaded, key=lambda m: str(m.MIGRATION_ID))

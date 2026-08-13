"""Separate development schema setup from the read-only production startup gate."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db_migrations import list_unsatisfied_db_migrations, run_all_db_migrations
from app.db_migrations.schema_alignment import list_orm_columns_missing_in_db
from app.models_db import Base


def ensure_runtime_schema(engine: Engine, *, production: bool) -> None:
    """Create/migrate only in development; production performs read-only verification."""

    if production:
        missing_schema = list_orm_columns_missing_in_db(engine)
        unsatisfied_migrations = list_unsatisfied_db_migrations(engine)
        if missing_schema or unsatisfied_migrations:
            raise RuntimeError(
                "Production database schema is not release-ready; run the separately "
                "approved migration procedure before application startup"
            )
        return

    Base.metadata.create_all(bind=engine)
    run_all_db_migrations(engine)

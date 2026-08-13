from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.secret_files import read_secret

DEFAULT_DB_URL = "sqlite+pysqlite:///./test_compliancehub.db"


def get_database_url() -> str:
    value = read_secret(
        "COMPLIANCEHUB_DB_URL",
        "COMPLIANCEHUB_DB_URL_FILE",
    )
    if len(value) > 8192:
        raise RuntimeError("COMPLIANCEHUB_DB_URL_FILE contains an invalid database URL")
    return value or DEFAULT_DB_URL


def create_db_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Register append-only enforcement for AuditLogTable (import for side effects).
from app import audit_append_only as _audit_append_only  # noqa: E402, F401


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

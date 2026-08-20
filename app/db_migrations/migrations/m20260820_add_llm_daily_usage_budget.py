"""Add the atomic per-tenant/day reservation ledger for governed LLM egress."""

from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists
from app.models_db import LLMDailyUsageBudgetDB

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260820_add_llm_daily_usage_budget"
DISPLAY_NAME = "add_llm_daily_usage_budget"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, LLMDailyUsageBudgetDB.__tablename__)


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    LLMDailyUsageBudgetDB.__table__.create(bind=engine, checkfirst=True)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True

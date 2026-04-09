"""Add Phase 5 tables: onboarding_status, subscription_plans, subscriptions, billing_events."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260415_phase5_onboarding_billing"
DISPLAY_NAME = "phase5_onboarding_billing"


def satisfied(engine: Engine) -> bool:
    return (
        table_exists(engine, "onboarding_status")
        and table_exists(engine, "subscription_plans")
        and table_exists(engine, "subscriptions")
        and table_exists(engine, "billing_events")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "onboarding_status"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS onboarding_status (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    current_step INTEGER NOT NULL DEFAULT 1,
                    total_steps INTEGER NOT NULL DEFAULT 6,
                    step_data JSON NOT NULL DEFAULT '{}',
                    completed BOOLEAN NOT NULL DEFAULT 0,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_onboarding_status_tenant"
                    " ON onboarding_status (tenant_id)"
                )
            )
        if not table_exists(engine, "subscription_plans"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(64) NOT NULL UNIQUE,
                    display_name VARCHAR(128) NOT NULL,
                    max_users INTEGER,
                    features JSON NOT NULL DEFAULT '[]',
                    price_monthly_cents INTEGER NOT NULL DEFAULT 0,
                    stripe_price_id VARCHAR(128),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
        if not table_exists(engine, "subscriptions"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    plan_id VARCHAR(36) NOT NULL,
                    stripe_subscription_id VARCHAR(128),
                    stripe_customer_id VARCHAR(128),
                    status VARCHAR(32) NOT NULL DEFAULT 'trialing',
                    trial_ends_at DATETIME,
                    current_period_end DATETIME,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant"
                    " ON subscriptions (tenant_id)"
                )
            )
        if not table_exists(engine, "billing_events"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS billing_events (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    stripe_event_id VARCHAR(128),
                    payload JSON NOT NULL DEFAULT '{}',
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_billing_events_tenant"
                    " ON billing_events (tenant_id)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True

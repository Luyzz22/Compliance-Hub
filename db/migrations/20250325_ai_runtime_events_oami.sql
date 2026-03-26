-- AI Runtime Events, Incident-Summaries, Tenant-OAMI-Cache (SQLite-kompatibel).
-- PostgreSQL: JSON → JSONB optional; RLS-Policies separat (Supabase).

CREATE TABLE IF NOT EXISTS ai_runtime_events (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    ai_system_id VARCHAR(255) NOT NULL,
    source VARCHAR(64) NOT NULL,
    source_event_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32),
    metric_key VARCHAR(128),
    incident_code VARCHAR(128),
    value FLOAT,
    delta FLOAT,
    threshold_breached BOOLEAN,
    environment VARCHAR(64),
    model_version VARCHAR(255),
    occurred_at TIMESTAMP NOT NULL,
    received_at TIMESTAMP NOT NULL,
    extra JSON NOT NULL DEFAULT ('{}'),
    CONSTRAINT fk_ai_runtime_events_ai_system
        FOREIGN KEY (ai_system_id) REFERENCES ai_systems (id) ON DELETE CASCADE,
    CONSTRAINT uq_ai_runtime_events_tenant_source_event UNIQUE (tenant_id, source, source_event_id)
);

CREATE INDEX IF NOT EXISTS ix_ai_runtime_events_tenant_id ON ai_runtime_events (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ai_runtime_events_tenant_system_occurred
    ON ai_runtime_events (tenant_id, ai_system_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_ai_runtime_events_tenant_system_type_occurred
    ON ai_runtime_events (tenant_id, ai_system_id, event_type, occurred_at);

CREATE TABLE IF NOT EXISTS ai_runtime_incident_summaries (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    ai_system_id VARCHAR(255) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    incident_count INTEGER NOT NULL DEFAULT 0,
    high_severity_count INTEGER NOT NULL DEFAULT 0,
    last_incident_at TIMESTAMP,
    computed_at_utc TIMESTAMP NOT NULL,
    CONSTRAINT fk_ai_runtime_incident_summaries_ai_system
        FOREIGN KEY (ai_system_id) REFERENCES ai_systems (id) ON DELETE CASCADE,
    CONSTRAINT uq_ai_runtime_incident_summary_window
        UNIQUE (tenant_id, ai_system_id, window_start, window_end)
);

CREATE INDEX IF NOT EXISTS ix_ai_runtime_incident_summaries_tenant_id
    ON ai_runtime_incident_summaries (tenant_id);
CREATE INDEX IF NOT EXISTS ix_ai_runtime_incident_summaries_ai_system_id
    ON ai_runtime_incident_summaries (ai_system_id);

CREATE TABLE IF NOT EXISTS tenant_operational_monitoring_snapshots (
    tenant_id VARCHAR(255) NOT NULL,
    window_days INTEGER NOT NULL,
    index_value INTEGER NOT NULL,
    level VARCHAR(16) NOT NULL,
    breakdown_json JSON NOT NULL DEFAULT ('{}'),
    computed_at_utc TIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, window_days)
);

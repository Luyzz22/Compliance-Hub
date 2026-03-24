-- NIS2 / KRITIS KPIs pro KI-System (mandantenfähig).
-- SQLite-kompatibel; für PostgreSQL ggf. UUID-Typ anpassen.

CREATE TABLE IF NOT EXISTS nis2_kritis_kpis (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    ai_system_id VARCHAR(255) NOT NULL,
    kpi_type VARCHAR(64) NOT NULL,
    value_percent INTEGER NOT NULL,
    evidence_ref TEXT,
    last_reviewed_at TIMESTAMP,
    CONSTRAINT fk_nis2_kritis_kpis_ai_system
        FOREIGN KEY (ai_system_id) REFERENCES ai_systems (id) ON DELETE CASCADE,
    CONSTRAINT uq_nis2_kritis_kpi_tenant_system_type
        UNIQUE (tenant_id, ai_system_id, kpi_type)
);

CREATE INDEX IF NOT EXISTS ix_nis2_kritis_kpis_tenant_id ON nis2_kritis_kpis (tenant_id);
CREATE INDEX IF NOT EXISTS ix_nis2_kritis_kpis_ai_system_id ON nis2_kritis_kpis (ai_system_id);

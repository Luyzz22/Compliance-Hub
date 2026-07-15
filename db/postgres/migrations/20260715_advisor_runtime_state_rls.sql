-- Compliance Hub governed runtime state for Azure Database for PostgreSQL.
-- Apply with a dedicated migration principal. The Entra application principal must be
-- granted membership in compliancehub_runtime_platform_app separately and must not own these
-- objects. Tenant-only principals receive compliancehub_runtime_app instead.

BEGIN;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'compliancehub_runtime_app') THEN
        CREATE ROLE compliancehub_runtime_app NOLOGIN NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'compliancehub_runtime_platform_app'
    ) THEN
        CREATE ROLE compliancehub_runtime_platform_app NOLOGIN NOBYPASSRLS;
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname IN ('compliancehub_runtime_app', 'compliancehub_runtime_platform_app')
          AND (rolsuper OR rolbypassrls OR rolcanlogin)
    ) THEN
        RAISE EXCEPTION 'runtime roles must be NOLOGIN, NOSUPERUSER and NOBYPASSRLS';
    END IF;
END
$roles$;

GRANT compliancehub_runtime_app TO compliancehub_runtime_platform_app;

CREATE SCHEMA IF NOT EXISTS compliancehub_private;
REVOKE ALL ON SCHEMA compliancehub_private FROM PUBLIC;
GRANT USAGE ON SCHEMA compliancehub_private TO compliancehub_runtime_app;

CREATE TABLE IF NOT EXISTS compliancehub_private.advisor_mandant_history (
    tenant_id VARCHAR(255) PRIMARY KEY,
    last_mandant_readiness_export_at TIMESTAMPTZ,
    last_datev_bundle_export_at TIMESTAMPTZ,
    last_review_marked_at TIMESTAMPTZ,
    last_review_note_de VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    row_version BIGINT NOT NULL DEFAULT 1,
    retention_until TIMESTAMPTZ,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_advisor_history_tenant_id
        CHECK (tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$'),
    CONSTRAINT ck_advisor_history_row_version CHECK (row_version > 0),
    CONSTRAINT ck_advisor_history_retention
        CHECK (retention_until IS NULL OR retention_until > created_at)
);

CREATE INDEX IF NOT EXISTS ix_advisor_mandant_history_retention
    ON compliancehub_private.advisor_mandant_history (retention_until)
    WHERE retention_until IS NOT NULL AND legal_hold = FALSE;

CREATE TABLE IF NOT EXISTS compliancehub_private.advisor_mandant_reminders (
    reminder_id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(16) NOT NULL,
    note VARCHAR(500),
    source VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    row_version BIGINT NOT NULL DEFAULT 1,
    retention_until TIMESTAMPTZ,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_advisor_reminder_tenant_id
        CHECK (tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$'),
    CONSTRAINT ck_advisor_reminder_category CHECK (
        category IN (
            'stale_review',
            'stale_export',
            'high_gap_count',
            'portfolio_attention',
            'sla_escalation',
            'follow_up_note',
            'manual'
        )
    ),
    CONSTRAINT ck_advisor_reminder_status
        CHECK (status IN ('open', 'done', 'dismissed')),
    CONSTRAINT ck_advisor_reminder_source CHECK (source IN ('auto', 'manual')),
    CONSTRAINT ck_advisor_reminder_row_version CHECK (row_version > 0),
    CONSTRAINT ck_advisor_reminder_timestamps CHECK (updated_at >= created_at),
    CONSTRAINT ck_advisor_reminder_retention
        CHECK (retention_until IS NULL OR retention_until > created_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_advisor_reminder_open_auto
    ON compliancehub_private.advisor_mandant_reminders (tenant_id, category)
    WHERE source = 'auto' AND status = 'open';

CREATE INDEX IF NOT EXISTS ix_advisor_reminder_tenant_status_due
    ON compliancehub_private.advisor_mandant_reminders (tenant_id, status, due_at);

CREATE INDEX IF NOT EXISTS ix_advisor_reminder_retention
    ON compliancehub_private.advisor_mandant_reminders (retention_until)
    WHERE retention_until IS NOT NULL AND legal_hold = FALSE;

CREATE TABLE IF NOT EXISTS compliancehub_private.runtime_state_deletion_audit (
    deletion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL,
    record_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actor_id VARCHAR(128) NOT NULL,
    deletion_reason VARCHAR(500) NOT NULL,
    source_row_version BIGINT NOT NULL,
    CONSTRAINT ck_runtime_deletion_actor CHECK (length(actor_id) > 0),
    CONSTRAINT ck_runtime_deletion_reason CHECK (length(deletion_reason) > 0)
);

CREATE INDEX IF NOT EXISTS ix_runtime_state_deletion_audit_tenant_time
    ON compliancehub_private.runtime_state_deletion_audit (tenant_id, deleted_at DESC);

ALTER TABLE compliancehub_private.advisor_mandant_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliancehub_private.advisor_mandant_history FORCE ROW LEVEL SECURITY;
ALTER TABLE compliancehub_private.advisor_mandant_reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliancehub_private.advisor_mandant_reminders FORCE ROW LEVEL SECURITY;
ALTER TABLE compliancehub_private.runtime_state_deletion_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliancehub_private.runtime_state_deletion_audit FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS advisor_mandant_history_tenant_isolation
    ON compliancehub_private.advisor_mandant_history;
CREATE POLICY advisor_mandant_history_tenant_isolation
    ON compliancehub_private.advisor_mandant_history
    FOR ALL
    TO compliancehub_runtime_app
    USING (
        tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), '')
        OR (
            current_setting('compliancehub.platform_access', TRUE) = 'true'
            AND pg_has_role(
                current_user,
                'compliancehub_runtime_platform_app',
                'member'
            )
        )
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), '')
        OR (
            current_setting('compliancehub.platform_access', TRUE) = 'true'
            AND pg_has_role(
                current_user,
                'compliancehub_runtime_platform_app',
                'member'
            )
        )
    );

DROP POLICY IF EXISTS advisor_mandant_reminders_tenant_isolation
    ON compliancehub_private.advisor_mandant_reminders;
CREATE POLICY advisor_mandant_reminders_tenant_isolation
    ON compliancehub_private.advisor_mandant_reminders
    FOR ALL
    TO compliancehub_runtime_app
    USING (
        tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), '')
        OR (
            current_setting('compliancehub.platform_access', TRUE) = 'true'
            AND pg_has_role(
                current_user,
                'compliancehub_runtime_platform_app',
                'member'
            )
        )
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), '')
        OR (
            current_setting('compliancehub.platform_access', TRUE) = 'true'
            AND pg_has_role(
                current_user,
                'compliancehub_runtime_platform_app',
                'member'
            )
        )
    );

DROP POLICY IF EXISTS runtime_state_deletion_audit_platform_read
    ON compliancehub_private.runtime_state_deletion_audit;
CREATE POLICY runtime_state_deletion_audit_platform_read
    ON compliancehub_private.runtime_state_deletion_audit
    FOR SELECT
    TO compliancehub_runtime_app
    USING (
        current_setting('compliancehub.platform_access', TRUE) = 'true'
        AND pg_has_role(
            current_user,
            'compliancehub_runtime_platform_app',
            'member'
        )
    );

DROP POLICY IF EXISTS runtime_state_deletion_audit_trigger_insert
    ON compliancehub_private.runtime_state_deletion_audit;
CREATE POLICY runtime_state_deletion_audit_trigger_insert
    ON compliancehub_private.runtime_state_deletion_audit
    FOR INSERT
    TO PUBLIC
    WITH CHECK (TRUE);

CREATE OR REPLACE FUNCTION compliancehub_private.audit_runtime_state_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, compliancehub_private
AS $function$
DECLARE
    actor TEXT;
    reason TEXT;
BEGIN
    actor := NULLIF(current_setting('compliancehub.actor_id', TRUE), '');
    reason := NULLIF(current_setting('compliancehub.deletion_reason', TRUE), '');
    IF actor IS NULL THEN
        RAISE EXCEPTION 'runtime state deletion requires actor context'
            USING ERRCODE = 'CH001';
    END IF;
    IF reason IS NULL THEN
        RAISE EXCEPTION 'runtime state deletion requires an approved reason'
            USING ERRCODE = 'CH002';
    END IF;

    INSERT INTO compliancehub_private.runtime_state_deletion_audit (
        table_name,
        record_id,
        tenant_id,
        actor_id,
        deletion_reason,
        source_row_version
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(to_jsonb(OLD) ->> 'reminder_id', OLD.tenant_id),
        OLD.tenant_id,
        actor,
        left(reason, 500),
        OLD.row_version
    );
    RETURN OLD;
END
$function$;

REVOKE ALL ON FUNCTION compliancehub_private.audit_runtime_state_delete() FROM PUBLIC;

DROP TRIGGER IF EXISTS trg_advisor_mandant_history_delete_audit
    ON compliancehub_private.advisor_mandant_history;
CREATE TRIGGER trg_advisor_mandant_history_delete_audit
    BEFORE DELETE ON compliancehub_private.advisor_mandant_history
    FOR EACH ROW EXECUTE FUNCTION compliancehub_private.audit_runtime_state_delete();

DROP TRIGGER IF EXISTS trg_advisor_mandant_reminder_delete_audit
    ON compliancehub_private.advisor_mandant_reminders;
CREATE TRIGGER trg_advisor_mandant_reminder_delete_audit
    BEFORE DELETE ON compliancehub_private.advisor_mandant_reminders
    FOR EACH ROW EXECUTE FUNCTION compliancehub_private.audit_runtime_state_delete();

REVOKE ALL ON TABLE compliancehub_private.advisor_mandant_history FROM PUBLIC;
REVOKE ALL ON TABLE compliancehub_private.advisor_mandant_reminders FROM PUBLIC;
REVOKE ALL ON TABLE compliancehub_private.runtime_state_deletion_audit FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON compliancehub_private.advisor_mandant_history TO compliancehub_runtime_app;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON compliancehub_private.advisor_mandant_reminders TO compliancehub_runtime_app;
GRANT SELECT
    ON compliancehub_private.runtime_state_deletion_audit TO compliancehub_runtime_app;

COMMENT ON TABLE compliancehub_private.advisor_mandant_history IS
    'Tenant-scoped advisor export and review history; FORCE RLS protected.';
COMMENT ON TABLE compliancehub_private.advisor_mandant_reminders IS
    'Tenant-scoped advisor reminders; FORCE RLS protected.';
COMMENT ON TABLE compliancehub_private.runtime_state_deletion_audit IS
    'Append-only metadata evidence for governed runtime-state deletion; contains no row payload.';

COMMIT;

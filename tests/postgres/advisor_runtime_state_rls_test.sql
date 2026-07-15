\set ON_ERROR_STOP on

CREATE ROLE compliancehub_runtime_tenant_test NOLOGIN NOBYPASSRLS;
CREATE ROLE compliancehub_runtime_platform_test NOLOGIN NOBYPASSRLS;
GRANT compliancehub_runtime_app TO compliancehub_runtime_tenant_test;
GRANT compliancehub_runtime_platform_app TO compliancehub_runtime_platform_test;

DO $test$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname IN (
            'compliancehub_runtime_app',
            'compliancehub_runtime_platform_app'
        )
          AND (rolsuper OR rolbypassrls OR rolcanlogin)
    ) THEN
        RAISE EXCEPTION 'runtime application roles have unsafe role attributes';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_class AS relation
        JOIN pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'compliancehub_private'
          AND relation.relname IN (
              'advisor_mandant_history',
              'advisor_mandant_reminders',
              'runtime_state_deletion_audit'
          )
          AND pg_get_userbyid(relation.relowner) IN (
              'compliancehub_runtime_app',
              'compliancehub_runtime_platform_app'
          )
    ) THEN
        RAISE EXCEPTION 'runtime application roles must not own protected tables';
    END IF;
END
$test$;

SET ROLE compliancehub_runtime_tenant_test;

BEGIN;
SELECT set_config('compliancehub.tenant_id', 'tenant-a', TRUE);
SELECT set_config('compliancehub.platform_access', 'false', TRUE);
SELECT set_config('compliancehub.actor_id', 'ci:tenant-a', TRUE);

INSERT INTO compliancehub_private.advisor_mandant_history (
    tenant_id,
    last_review_marked_at,
    last_review_note_de
) VALUES (
    'tenant-a',
    '2026-07-15T12:00:00Z',
    'tenant-a evidence'
);

INSERT INTO compliancehub_private.advisor_mandant_reminders (
    reminder_id,
    tenant_id,
    category,
    due_at,
    status,
    source,
    created_at,
    updated_at
) VALUES (
    '11111111-1111-4111-8111-111111111111',
    'tenant-a',
    'manual',
    '2026-07-20T12:00:00Z',
    'open',
    'manual',
    '2026-07-15T12:00:00Z',
    '2026-07-15T12:00:00Z'
);
COMMIT;

DO $test$
BEGIN
    PERFORM set_config('compliancehub.tenant_id', 'tenant-a', FALSE);
    PERFORM set_config('compliancehub.platform_access', 'false', FALSE);
    BEGIN
        INSERT INTO compliancehub_private.advisor_mandant_history (tenant_id)
        VALUES ('tenant-b');
        RAISE EXCEPTION 'cross-tenant INSERT unexpectedly succeeded'
            USING ERRCODE = 'ZX001';
    EXCEPTION
        WHEN insufficient_privilege THEN NULL;
    END;

    BEGIN
        INSERT INTO compliancehub_private.advisor_mandant_reminders (
            reminder_id,
            tenant_id,
            category,
            due_at,
            status,
            source,
            created_at,
            updated_at
        ) VALUES (
            '22222222-2222-4222-8222-222222222222',
            'tenant-b',
            'manual',
            '2026-07-20T12:00:00Z',
            'open',
            'manual',
            '2026-07-15T12:00:00Z',
            '2026-07-15T12:00:00Z'
        );
        RAISE EXCEPTION 'cross-tenant reminder INSERT unexpectedly succeeded'
            USING ERRCODE = 'ZX003';
    EXCEPTION
        WHEN insufficient_privilege THEN NULL;
    END;
END
$test$;

RESET compliancehub.tenant_id;
RESET compliancehub.platform_access;
RESET compliancehub.actor_id;

RESET ROLE;
INSERT INTO compliancehub_private.advisor_mandant_history (tenant_id)
VALUES ('tenant-b');
INSERT INTO compliancehub_private.advisor_mandant_reminders (
    reminder_id,
    tenant_id,
    category,
    due_at,
    status,
    source,
    created_at,
    updated_at
) VALUES (
    '22222222-2222-4222-8222-222222222222',
    'tenant-b',
    'manual',
    '2026-07-20T12:00:00Z',
    'open',
    'manual',
    '2026-07-15T12:00:00Z',
    '2026-07-15T12:00:00Z'
);

SET ROLE compliancehub_runtime_tenant_test;
BEGIN;
SELECT set_config('compliancehub.tenant_id', 'tenant-a', TRUE);
-- A tenant role cannot self-elevate by setting the platform flag.
SELECT set_config('compliancehub.platform_access', 'true', TRUE);
DO $test$
DECLARE
    visible_history_rows INTEGER;
    visible_reminder_rows INTEGER;
BEGIN
    SELECT count(*) INTO visible_history_rows
    FROM compliancehub_private.advisor_mandant_history;
    SELECT count(*) INTO visible_reminder_rows
    FROM compliancehub_private.advisor_mandant_reminders;
    IF visible_history_rows <> 1 OR visible_reminder_rows <> 1 THEN
        RAISE EXCEPTION
            'tenant RLS/self-elevation guard expected 1 history and 1 reminder row, observed % and %',
            visible_history_rows,
            visible_reminder_rows;
    END IF;
END
$test$;
COMMIT;

RESET ROLE;
SET ROLE compliancehub_runtime_platform_test;
BEGIN;
SELECT set_config('compliancehub.tenant_id', '__platform__', TRUE);
SELECT set_config('compliancehub.platform_access', 'true', TRUE);
SELECT set_config('compliancehub.actor_id', 'ci:platform', TRUE);
DO $test$
DECLARE
    visible_history_rows INTEGER;
    visible_reminder_rows INTEGER;
BEGIN
    SELECT count(*) INTO visible_history_rows
    FROM compliancehub_private.advisor_mandant_history;
    SELECT count(*) INTO visible_reminder_rows
    FROM compliancehub_private.advisor_mandant_reminders;
    IF visible_history_rows <> 2 OR visible_reminder_rows <> 2 THEN
        RAISE EXCEPTION
            'platform RLS expected 2 history and 2 reminder rows, observed % and %',
            visible_history_rows,
            visible_reminder_rows;
    END IF;
END
$test$;

DO $test$
BEGIN
    BEGIN
        INSERT INTO compliancehub_private.runtime_state_deletion_audit (
            table_name,
            record_id,
            tenant_id,
            actor_id,
            deletion_reason,
            source_row_version
        ) VALUES (
            'forged',
            'forged',
            'tenant-b',
            'ci:platform',
            'forged audit entry',
            1
        );
        RAISE EXCEPTION 'direct deletion audit INSERT unexpectedly succeeded'
            USING ERRCODE = 'ZX004';
    EXCEPTION
        WHEN insufficient_privilege THEN NULL;
    END;
END
$test$;

DO $test$
BEGIN
    BEGIN
        DELETE FROM compliancehub_private.advisor_mandant_history
        WHERE tenant_id = 'tenant-b';
        RAISE EXCEPTION 'deletion without reason unexpectedly succeeded'
            USING ERRCODE = 'ZX002';
    EXCEPTION
        WHEN SQLSTATE 'CH002' THEN NULL;
    END;
END
$test$;

SELECT set_config(
    'compliancehub.deletion_reason',
    'CI verification of governed deletion audit',
    TRUE
);
DELETE FROM compliancehub_private.advisor_mandant_history
WHERE tenant_id = 'tenant-b';

DO $test$
DECLARE
    audit_rows INTEGER;
BEGIN
    SELECT count(*) INTO audit_rows
    FROM compliancehub_private.runtime_state_deletion_audit
    WHERE tenant_id = 'tenant-b'
      AND actor_id = 'ci:platform'
      AND deletion_reason = 'CI verification of governed deletion audit';
    IF audit_rows <> 1 THEN
        RAISE EXCEPTION 'expected one deletion audit row, observed %', audit_rows;
    END IF;
END
$test$;
COMMIT;

RESET ROLE;
DROP ROLE compliancehub_runtime_tenant_test;
DROP ROLE compliancehub_runtime_platform_test;

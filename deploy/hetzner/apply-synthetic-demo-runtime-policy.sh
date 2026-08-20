#!/bin/sh
set -eu

PGPASSWORD="$(tr -d '\r\n' < /run/secrets/postgres_admin_password)"
export PGPASSWORD
export PGSSLROOTCERT=/run/secrets/postgres_ca_certificate

psql \
  --set ON_ERROR_STOP=1 \
  --host postgres \
  --username postgres \
  --dbname compliancehub \
  --file /policies/advisor-runtime-state.sql

psql \
  --set ON_ERROR_STOP=1 \
  --host postgres \
  --username postgres \
  --dbname compliancehub <<'SQL'
GRANT compliancehub_runtime_platform_app TO compliancehub_frontend;
REVOKE CREATE ON SCHEMA public FROM compliancehub_backend;
REVOKE ALL ON SCHEMA public FROM compliancehub_frontend;

DO $contract$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname IN ('compliancehub_backend', 'compliancehub_frontend')
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls)
    ) THEN
        RAISE EXCEPTION 'synthetic demo runtime role has privileged attributes';
    END IF;
    IF NOT pg_has_role(
        'compliancehub_frontend',
        'compliancehub_runtime_platform_app',
        'member'
    ) THEN
        RAISE EXCEPTION 'frontend runtime role lacks governed platform membership';
    END IF;
END
$contract$;
SQL

unset PGPASSWORD
echo "synthetic_demo_runtime_policy=passed"

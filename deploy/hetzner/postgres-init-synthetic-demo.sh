#!/bin/sh
set -eu

read_secret() {
  value="$(tr -d '\r\n' < "$1")"
  case "$value" in
    *[!A-Za-z0-9_-]*|'')
      echo "synthetic demo database secret has an invalid format" >&2
      exit 1
      ;;
  esac
  if [ "${#value}" -lt 32 ]; then
    echo "synthetic demo database secret is shorter than 32 characters" >&2
    exit 1
  fi
  printf '%s' "$value"
}

CH_BACKEND_PASSWORD="$(read_secret /run/secrets/postgres_backend_password)"
CH_FRONTEND_PASSWORD="$(read_secret /run/secrets/postgres_frontend_password)"
export CH_BACKEND_PASSWORD CH_FRONTEND_PASSWORD

psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv backend_password CH_BACKEND_PASSWORD
\getenv frontend_password CH_FRONTEND_PASSWORD
CREATE ROLE compliancehub_backend
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS
  PASSWORD :'backend_password';
CREATE ROLE compliancehub_frontend
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOBYPASSRLS
  PASSWORD :'frontend_password';
GRANT CONNECT ON DATABASE compliancehub TO compliancehub_backend, compliancehub_frontend;
GRANT USAGE, CREATE ON SCHEMA public TO compliancehub_backend;
REVOKE ALL ON SCHEMA public FROM compliancehub_frontend;
SQL

unset CH_BACKEND_PASSWORD CH_FRONTEND_PASSWORD

cat > "$PGDATA/pg_hba.conf" <<'HBA'
local   all             postgres                                peer
local   all             all                                     scram-sha-256
hostssl compliancehub   postgres              10.89.0.0/24       scram-sha-256
hostssl compliancehub   compliancehub_backend 10.89.0.0/24       scram-sha-256
hostssl compliancehub   compliancehub_frontend 10.89.0.0/24      scram-sha-256
host    all             all                   0.0.0.0/0           reject
host    all             all                   ::/0                reject
HBA

chmod 0600 "$PGDATA/pg_hba.conf"

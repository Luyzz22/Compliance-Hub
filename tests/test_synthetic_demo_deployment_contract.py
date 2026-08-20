"""Static fail-closed contract for the private synthetic Hetzner demonstration."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deploy" / "hetzner"


def _compose() -> dict:
    return yaml.safe_load((DEPLOYMENT / "compose.synthetic-demo.yml").read_text(encoding="utf-8"))


def _example_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in (
        (DEPLOYMENT / ".env.synthetic-demo.example").read_text(encoding="utf-8").splitlines()
    ):
        line = raw.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def test_only_the_cidr_restricted_edge_publishes_ports() -> None:
    compose = _compose()
    services = compose["services"]
    assert set(services["edge"]["ports"]) == {"80:80", "443:443"}
    for name in set(services) - {"edge"}:
        assert "ports" not in services[name]
    assert compose["networks"]["app_net"]["internal"] is True

    caddy = (DEPLOYMENT / "Caddyfile.synthetic-demo").read_text(encoding="utf-8")
    assert caddy.count("@outside not remote_ip {$COMPLIANCEHUB_DEMO_ALLOWED_CIDR}") == 2
    assert caddy.count("respond @outside 403") == 2
    assert "auto_https off" in caddy


def test_stateful_and_application_containers_are_hardened() -> None:
    services = _compose()["services"]
    for name in (
        "postgres",
        "schema-bootstrap",
        "runtime-policy",
        "opa",
        "backend",
        "frontend",
        "edge",
    ):
        service = services[name]
        assert service["read_only"] is True
        assert "no-new-privileges:true" in service["security_opt"]
    for name in ("schema-bootstrap", "runtime-policy", "opa", "backend", "frontend"):
        assert services[name]["cap_drop"] == ["ALL"]
    assert services["backend"]["user"] == "10001:10001"
    assert services["frontend"]["user"] == "10001:10001"
    assert services["runtime-policy"]["user"] == "70:70"


def test_database_bootstrap_precedes_runtime_and_uses_tls() -> None:
    services = _compose()["services"]
    assert services["schema-bootstrap"]["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert services["runtime-policy"]["depends_on"]["schema-bootstrap"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["backend"]["depends_on"]["runtime-policy"]["condition"] == (
        "service_completed_successfully"
    )
    postgres_command = services["postgres"]["command"]
    assert "ssl=on" in postgres_command
    assert "ssl_min_protocol_version=TLSv1.2" in postgres_command
    assert "password_encryption=scram-sha-256" in postgres_command
    assert "log_statement=none" in postgres_command
    assert "postgres:17.9-alpine@sha256:" in services["postgres"]["image"]

    init = (DEPLOYMENT / "postgres-init-synthetic-demo.sh").read_text(encoding="utf-8")
    assert "NOBYPASSRLS" in init
    assert "NOSUPERUSER" in init
    assert "hostssl compliancehub" in init
    assert "0.0.0.0/0           reject" in init


def test_demo_runtime_policy_grants_only_the_governed_frontend_role() -> None:
    source = (DEPLOYMENT / "apply-synthetic-demo-runtime-policy.sh").read_text(encoding="utf-8")
    assert "GRANT compliancehub_runtime_platform_app TO compliancehub_frontend" in source
    assert "REVOKE CREATE ON SCHEMA public FROM compliancehub_backend" in source
    assert "synthetic demo runtime role has privileged attributes" in source
    assert "set -eu" in source
    assert "echo $PGPASSWORD" not in source


def test_example_environment_is_synthetic_read_only_and_not_publicly_released() -> None:
    env = _example_env()
    expected = {
        "COMPLIANCEHUB_RELEASE_CHANNEL": "pilot",
        "COMPLIANCEHUB_RELEASE_PROFILE": "synthetic_demo",
        "COMPLIANCEHUB_FEATURE_DEMO_MODE": "true",
        "COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS": "true",
        "COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED": "true",
        "COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED": "true",
        "COMPLIANCEHUB_LLM_PII_MODE": "block",
        "COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED": "true",
        "COMPLIANCEHUB_SELF_REGISTRATION_ENABLED": "false",
        "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED": "false",
        "COMPLIANCEHUB_LEGAL_PUBLISH_READY": "false",
        "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND": "s3",
        "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND": "postgres",
    }
    for key, value in expected.items():
        assert env[key] == value
    assert env["COMPLIANCEHUB_S3_ENDPOINT"] == "https://nbg1.your-objectstorage.com"
    assert env["POSTGRES_HOST"] == "postgres"
    assert env["POSTGRES_USER"] == "compliancehub_frontend"
    assert not any(key in env for key in ("POSTGRES_PASSWORD", "AZURE_OPENAI_API_KEY"))
    assert ".env.synthetic-demo" in (DEPLOYMENT / ".gitignore").read_text(encoding="utf-8")


def test_frontend_build_and_runtime_contain_the_explicit_demo_contract() -> None:
    dockerfile = (ROOT / "frontend" / "Dockerfile.hetzner").read_text(encoding="utf-8")
    assert "ARG NEXT_PUBLIC_FEATURE_DEMO_AZURE_INFERENCE=false" in dockerfile
    assert "ARG NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID=" in dockerfile
    assert "ARG NEXT_PUBLIC_TENANT_ID=" in dockerfile

    compose = _compose()
    frontend = compose["services"]["frontend"]
    assert frontend["environment"]["POSTGRES_SSL_CA_FILE"] == (
        "/run/secrets/postgres_ca_certificate"
    )
    assert frontend["environment"]["COMPLIANCEHUB_RELEASE_PROFILE"] == "synthetic_demo"
    assert frontend["labels"]["com.complywithai.data.contract"] == "synthetic_only"


def test_backend_image_contains_postgres_driver_and_bounded_bootstrap() -> None:
    dockerfile = (ROOT / "Dockerfile.hetzner").read_text(encoding="utf-8")
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    bootstrap = (ROOT / "scripts" / "bootstrap_synthetic_demo.py").read_text(encoding="utf-8")
    assert "scripts/bootstrap_synthetic_demo.py" in dockerfile
    assert "psycopg==" in lock and "psycopg-binary==" in lock
    assert 'DEFAULT_TENANT_ID = "demo-mittelstand-ag"' in bootstrap
    assert "demo_playground=False" in bootstrap
    assert "EnterpriseRole.COMPLIANCE_ADMIN.value" in bootstrap
    assert "password_disclosed=false" in bootstrap
    assert "print(password" not in bootstrap


def test_preflight_checks_identity_storage_certificates_and_database_binding() -> None:
    preflight = (DEPLOYMENT / "preflight-synthetic-demo.py").read_text(encoding="utf-8")
    for invariant in (
        "COMPLIANCEHUB_DEMO_ALLOWED_CIDR",
        "AZURE_OPENAI_ENDPOINT",
        "nbg1.your-objectstorage.com",
        "sslmode=verify-full",
        "PostgreSQL trust-anchor copies differ",
        "openssl",
        "numeric UID",
        "synthetic_demo_preflight=passed",
        "production_ready=false",
    ):
        assert invariant in preflight

"""Static contract for the Hetzner-first container boundary."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deploy" / "hetzner"


def _compose() -> dict:
    return yaml.safe_load((DEPLOYMENT / "compose.yml").read_text(encoding="utf-8"))


def test_only_edge_publishes_host_ports_and_application_network_is_internal() -> None:
    compose = _compose()
    services = compose["services"]
    assert set(services["edge"]["ports"]) == {"80:80", "443:443"}
    assert "ports" not in services["frontend"]
    assert "ports" not in services["backend"]
    assert "ports" not in services["opa"]
    assert services["opa"]["networks"] == ["app_net"]
    assert compose["networks"]["app_net"]["internal"] is True


def test_application_containers_are_rootless_read_only_and_drop_capabilities() -> None:
    compose = _compose()
    for name in ("frontend", "backend", "opa"):
        service = compose["services"][name]
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in service["security_opt"]

        if name == "opa":
            assert service["user"] == "10001:10001"
            assert "@sha256:" in service["image"]
            continue
        dockerfile_name = (
            "frontend/Dockerfile.hetzner" if name == "frontend" else "Dockerfile.hetzner"
        )
        dockerfile = ROOT / dockerfile_name
        source = dockerfile.read_text(encoding="utf-8")
        assert "USER 10001:10001" in source
        assert all("@sha256:" in line for line in source.splitlines() if line.startswith("FROM "))

    assert compose["services"]["edge"]["user"] == "65532:65532"


def test_runtime_dependencies_and_all_public_images_are_immutable() -> None:
    compose = _compose()
    assert "@sha256:" in compose["services"]["edge"]["image"]
    assert "@sha256:" in compose["services"]["opa"]["image"]
    assert compose["services"]["frontend"]["image"].startswith("${COMPLIANCEHUB_FRONTEND_IMAGE:")
    assert compose["services"]["backend"]["image"].startswith("${COMPLIANCEHUB_BACKEND_IMAGE:")
    assert "build" not in compose["services"]["frontend"]
    assert "build" not in compose["services"]["backend"]

    lockfile = ROOT / "requirements.lock"
    assert lockfile.exists()
    lock = lockfile.read_text(encoding="utf-8")
    assert "--hash=sha256:" in lock
    dockerfile = (ROOT / "Dockerfile.hetzner").read_text(encoding="utf-8")
    assert "pip install --require-hashes --no-deps -r requirements.lock" in dockerfile
    assert "pip install --no-deps --no-build-isolation ." in dockerfile


def test_runtime_images_use_minimal_alpine_baselines_without_language_package_managers() -> None:
    backend = (ROOT / "Dockerfile.hetzner").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "Dockerfile.hetzner").read_text(encoding="utf-8")

    assert all(
        line.startswith("FROM python:3.11-alpine3.23@sha256:")
        for line in backend.splitlines()
        if line.startswith("FROM ")
    )
    assert "pip uninstall --yes pip setuptools wheel" in backend
    assert "rm -rf /usr/local/lib/python3.11/site-packages/*" in backend
    assert "/usr/local/bin/pip" in backend

    assert all(
        line.startswith("FROM node:22-alpine3.23@sha256:")
        for line in frontend.splitlines()
        if line.startswith("FROM ")
    )
    assert "rm -rf /usr/local/lib/node_modules" in frontend
    assert "/usr/local/bin/npm" in frontend
    assert "/usr/local/bin/npx" in frontend
    assert "/usr/local/bin/corepack" in frontend


def test_frontend_container_build_preserves_cross_stack_prebuild_gates() -> None:
    dockerfile = (ROOT / "frontend" / "Dockerfile.hetzner").read_text(encoding="utf-8")
    dockerignore = (ROOT / "frontend" / "Dockerfile.hetzner.dockerignore").read_text(
        encoding="utf-8"
    )
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "COPY frontend/ ./" in dockerfile
    assert "COPY db/postgres/migrations/20260715_advisor_runtime_state_rls.sql" in dockerfile
    assert "COPY tests/postgres/advisor_runtime_state_rls_test.sql" in dockerfile
    assert "frontend/node_modules" in dockerignore
    assert "frontend/.next" in dockerignore
    assert "!db/postgres/migrations/20260715_advisor_runtime_state_rls.sql" in dockerignore
    assert "component: frontend\n            context: ." in workflow


def test_secret_values_are_file_mounted_and_not_embedded_in_compose() -> None:
    source = (DEPLOYMENT / "compose.yml").read_text(encoding="utf-8")
    for forbidden in (
        "POSTGRES_PASSWORD:",
        "AWS_ACCESS_KEY_ID:",
        "AWS_SECRET_ACCESS_KEY:",
        "AZURE_OPENAI_API_KEY:",
        "COMPLIANCEHUB_BFF_SHARED_SECRET:",
        "COMPLIANCEHUB_ENTRA_CLIENT_SECRET:",
        "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET:",
        "COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY:",
    ):
        assert forbidden not in source
    for required in (
        "backend_database_url",
        "postgres_password",
        "s3_access_key",
        "s3_secret_access_key",
        "azure_openai_client_certificate",
        "bff_shared_secret",
        "audit_pseudonymization_key",
        "credential_pepper",
        "entra_client_secret",
        "auth_transaction_secret",
        "lead_admin_secret",
    ):
        assert required in source


def test_file_secret_permissions_are_an_explicit_host_preflight_contract() -> None:
    compose = _compose()
    contracts = compose["x-secret-host-contract"]

    assert set(contracts) == set(compose["secrets"])
    assert all(contract["mode"] == "0400" for contract in contracts.values())
    for service in compose["services"].values():
        for secret in service.get("secrets", []):
            assert set(secret) == {"source", "target"}


def test_audit_key_is_mounted_only_into_the_backend() -> None:
    services = _compose()["services"]
    frontend_secrets = {entry["source"] for entry in services["frontend"]["secrets"]}
    backend_secrets = {entry["source"] for entry in services["backend"]["secrets"]}

    assert "audit_pseudonymization_key" not in frontend_secrets
    assert "audit_pseudonymization_key" in backend_secrets
    assert "credential_pepper" not in frontend_secrets
    assert "credential_pepper" in backend_secrets


def test_frontend_is_standalone_and_has_no_vercel_runtime_dependency() -> None:
    next_config = (ROOT / "frontend" / "next.config.ts").read_text(encoding="utf-8")
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert 'output: "standalone"' in next_config
    assert "@vercel/oidc" not in package.get("dependencies", {})
    assert "@azure/storage-blob" not in package.get("dependencies", {})
    assert "@azure/identity" not in package.get("dependencies", {})
    assert not (ROOT / "frontend" / "vercel.json").exists()


def test_frontend_runtime_executes_enterprise_preflight_before_server() -> None:
    source = (ROOT / "frontend" / "Dockerfile.hetzner").read_text(encoding="utf-8")
    assert "COMPLIANCEHUB_RUNTIME_PREFLIGHT=true" in source
    assert "node scripts/verify-enterprise-readiness.mjs && exec node server.js" in source


def test_compose_contains_no_forbidden_external_provider_configuration() -> None:
    source = (DEPLOYMENT / "compose.yml").read_text(encoding="utf-8")
    assert "HUBSPOT_" not in source
    assert "PIPEDRIVE_" not in source
    assert "STRIPE_" not in source
    assert "POSTHOG_" not in source
    assert "LEAD_ADMIN_SECRET_FILE" in source


def test_haystack_dependency_telemetry_is_disabled_before_application_imports() -> None:
    dockerfile = (ROOT / "Dockerfile.hetzner").read_text(encoding="utf-8")
    compose = (DEPLOYMENT / "compose.yml").read_text(encoding="utf-8")
    package_init = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")

    assert "HAYSTACK_TELEMETRY_ENABLED=false" in dockerfile
    assert 'HAYSTACK_TELEMETRY_ENABLED: "false"' in compose
    assert "LANGCHAIN_TRACING_V2=false" in dockerfile
    assert 'LANGCHAIN_TRACING_V2: "false"' in compose
    assert "LANGSMITH_TRACING=false" in dockerfile
    assert 'LANGSMITH_TRACING: "false"' in compose
    assert '"HAYSTACK_TELEMETRY_ENABLED"' in package_init
    assert '"LANGCHAIN_TRACING_V2"' in package_init
    assert '"LANGSMITH_TRACING"' in package_init
    assert 'os.environ.setdefault(name, "false")' in package_init


def test_backend_uses_internal_fail_closed_opa_policy_engine() -> None:
    compose = _compose()
    backend = compose["services"]["backend"]
    opa = compose["services"]["opa"]

    assert backend["environment"]["COMPLIANCEHUB_OPA_STRICT_MISSING"] == "true"
    assert backend["environment"]["OPA_URL"] == "http://opa:8181"
    assert backend["depends_on"]["opa"]["condition"] == "service_healthy"
    assert "--v0-compatible" in opa["command"]
    assert "opa_action_policy" in {entry["source"] for entry in opa["configs"]}
    assert opa["healthcheck"]["test"][:3] == ["CMD", "/opa", "eval"]
    assert "--fail" in opa["healthcheck"]["test"]
    assert "--fail-defined" not in opa["healthcheck"]["test"]
    assert "data.compliancehub.allow_action == false" in opa["healthcheck"]["test"]


def test_ci_builds_and_scans_both_production_images() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "container-security:" in workflow
    assert "component: backend" in workflow
    assert "component: frontend" in workflow
    assert "docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a" in workflow
    assert "docker/setup-buildx-action@bb05f3f5519dd87d3ba754cc423b652a5edd6d2c" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    assert "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25" in workflow
    assert "severity: HIGH,CRITICAL" in workflow
    assert 'exit-code: "1"' in workflow
    assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"' in workflow


def test_application_containers_expose_release_evidence_labels() -> None:
    compose = _compose()

    for service_name in ("backend", "frontend"):
        labels = compose["services"][service_name]["labels"]
        assert labels["com.complywithai.release.id"]
        assert labels["com.complywithai.release.commit"]
        assert labels["com.complywithai.release.evidence-sha256"]
        assert labels["com.complywithai.release.blueprint-sha256"]


def test_backend_readiness_uses_a_file_secret_and_frontend_waits_for_it() -> None:
    compose = _compose()
    backend = compose["services"]["backend"]
    frontend = compose["services"]["frontend"]

    assert backend["environment"]["INTERNAL_HEALTH_API_KEY_FILE"] == (
        "/run/secrets/internal_health_api_key"
    )
    assert backend["environment"]["INTERNAL_HEALTH_ALLOWED_IPS"] == "127.0.0.1"
    assert backend["healthcheck"]["test"] == [
        "CMD",
        "python",
        "/app/scripts/container_readiness.py",
    ]
    assert "INTERNAL_HEALTH_API_KEY" not in backend["environment"]
    assert frontend["depends_on"]["backend"]["condition"] == "service_healthy"
    assert "internal_health_api_key" in {entry["source"] for entry in backend["secrets"]}

    dockerfile = (ROOT / "Dockerfile.hetzner").read_text(encoding="utf-8")
    assert "scripts/container_readiness.py" in dockerfile
    assert "scripts/verify_db_schema.py" in dockerfile

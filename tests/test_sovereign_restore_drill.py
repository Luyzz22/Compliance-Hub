"""Adversarial contracts for isolated PostgreSQL and S3 restore drills."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import sovereign_restore_drill


def _config(tmp_path: Path) -> Path:
    payload = {
        "schema_version": 1,
        "drill_id": "DR-20260813-CHANGE1234",
        "evidence_root": str(tmp_path / "evidence"),
        "postgres_backup_file": str(tmp_path / "approved.dump"),
        "postgres_backup_sha256": "a" * 64,
        "postgres_backup_created_at": "2026-08-13T10:00:00Z",
        "postgres_connection_file": str(tmp_path / "postgres-connection.json"),
        "postgres_pgpass_file": str(tmp_path / "pgpass"),
        "allowed_postgres_hosts": ["postgres-restore.internal.example.de"],
        "postgres_restore_database": "compliancehub_restore_20260813_change1234",
        "postgres_required_tables": ["tenants", "ai_systems", "audit_logs"],
        "postgres_minimum_public_tables": 3,
        "object_rclone_config_file": str(tmp_path / "rclone.conf"),
        "object_remote": "hetzner_restore",
        "object_backup_bucket": "compliancehub-backups",
        "object_restore_bucket": "compliancehub-restore-drills",
        "object_backup_prefix": "approved/2026-08-13",
        "object_backup_created_at": "2026-08-13T10:00:00Z",
        "object_restore_prefix": "restore-drills/DR-20260813-CHANGE1234",
        "allowed_object_hosts": ["fsn1.your-objectstorage.com"],
        "rpo_target_minutes": 1440,
        "rto_target_minutes": 240,
        "required_tools": {
            "psql": "17.9",
            "pg_restore": "17.9",
            "createdb": "17.9",
            "dropdb": "17.9",
            "rclone": "v1.72.1",
        },
    }
    path = tmp_path / "restore-drill.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    return path


def test_config_accepts_only_dedicated_restore_targets(tmp_path: Path) -> None:
    path = _config(tmp_path)
    config = sovereign_restore_drill.load_drill_config(path, allowed_uids={os.geteuid()})
    assert config["object_restore_prefix"] == "restore-drills/DR-20260813-CHANGE1234"

    payload = json.loads(path.read_text(encoding="utf-8"))
    path.chmod(0o600)
    payload["postgres_restore_database"] = "compliancehub_production"
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_restore_drill.DrillError, match="isolated drill prefix"):
        sovereign_restore_drill.load_drill_config(path, allowed_uids={os.geteuid()})

    path.chmod(0o600)
    payload["postgres_restore_database"] = "compliancehub_restore_20260813_change1234"
    payload["object_restore_prefix"] = payload["object_backup_prefix"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_restore_drill.DrillError, match="dedicated drill target"):
        sovereign_restore_drill.load_drill_config(path, allowed_uids={os.geteuid()})

    path.chmod(0o600)
    payload["object_restore_prefix"] = "restore-drills/DR-20260813-CHANGE1234"
    payload["object_restore_bucket"] = payload["object_backup_bucket"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_restore_drill.DrillError, match="dedicated restore bucket"):
        sovereign_restore_drill.load_drill_config(path, allowed_uids={os.geteuid()})


def test_config_rejects_boolean_schema_version(tmp_path: Path) -> None:
    path = _config(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    path.chmod(0o600)
    payload["schema_version"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_restore_drill.DrillError, match="schema must be 1"):
        sovereign_restore_drill.load_drill_config(path, allowed_uids={os.geteuid()})


def test_rclone_contract_requires_allowed_https_s3_endpoint(tmp_path: Path) -> None:
    path = tmp_path / "rclone.conf"
    path.write_text(
        "[hetzner_restore]\n"
        "type = s3\n"
        "provider = Other\n"
        "endpoint = https://fsn1.your-objectstorage.com\n"
        "access_key_id = restore-access-id\n"
        "secret_access_key = restore-secret-value-with-32-bytes\n"
        "acl = private\n",
        encoding="utf-8",
    )
    path.chmod(0o400)
    assert (
        sovereign_restore_drill._validate_rclone_config(
            path,
            remote="hetzner_restore",
            allowed_hosts={"fsn1.your-objectstorage.com"},
            allowed_uids={os.geteuid()},
        )
        == "fsn1.your-objectstorage.com"
    )

    path.chmod(0o600)
    path.write_text(path.read_text().replace("fsn1.your-objectstorage.com", "s3.amazonaws.com"))
    path.chmod(0o400)
    with pytest.raises(sovereign_restore_drill.DrillError, match="allowed HTTPS host"):
        sovereign_restore_drill._validate_rclone_config(
            path,
            remote="hetzner_restore",
            allowed_hosts={"fsn1.your-objectstorage.com"},
            allowed_uids={os.geteuid()},
        )


def test_pgpass_is_bound_to_exact_restore_host_port_and_user() -> None:
    connection = {
        "host": "postgres-restore.internal.example.de",
        "port": 5432,
        "username": "restore_operator",
    }
    sovereign_restore_drill._validate_pgpass(
        b"postgres-restore.internal.example.de:5432:*:restore_operator:long-restore-password\n",
        connection,
    )
    with pytest.raises(sovereign_restore_drill.DrillError, match="does not match"):
        sovereign_restore_drill._validate_pgpass(
            b"*:5432:*:restore_operator:long-restore-password\n",
            connection,
        )


def test_drill_id_reservation_is_atomic_and_persistent(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir(mode=0o700)
    reservation = sovereign_restore_drill._reserve_drill(root, "DR-20260813-CHANGE1234")
    assert reservation.stat().st_mode & 0o777 == 0o600
    with pytest.raises(sovereign_restore_drill.DrillError, match="already reserved"):
        sovereign_restore_drill._reserve_drill(root, "DR-20260813-CHANGE1234")


def test_postgres_restore_verifies_schema_cleans_up_and_never_passes_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
        capture: bool = False,
        timeout: int = 14_400,
    ) -> str:
        del cwd, timeout
        commands.append((command, environment))
        if command[0] == "psql" and "pg_database" in command[-3]:
            return "0"
        if command[0] == "psql":
            return json.dumps(
                {
                    "database": "compliancehub_restore_20260813_change1234",
                    "table_count": 3,
                    "tables": ["ai_systems", "audit_logs", "tenants"],
                }
            )
        return "" if capture else ""

    monkeypatch.setattr(sovereign_restore_drill, "_run", fake_run)
    result = sovereign_restore_drill._run_postgres_restore(
        repository=tmp_path,
        connection={
            "host": "postgres-restore.internal.example.de",
            "port": 5432,
            "username": "restore_operator",
            "maintenance_database": "postgres",
            "sslmode": "verify-full",
        },
        pgpass_file=tmp_path / "pgpass",
        backup=tmp_path / "approved.dump",
        restore_database="compliancehub_restore_20260813_change1234",
        required_tables={"tenants", "ai_systems", "audit_logs"},
        minimum_tables=3,
    )
    assert result["status"] == "passed"
    assert result["cleanup_status"] == "passed"
    assert [command[0] for command, _ in commands].count("dropdb") == 1
    assert all("password" not in " ".join(command).lower() for command, _ in commands)
    assert all(env["PGPASSFILE"] == str(tmp_path / "pgpass") for _, env in commands)
    assert all(env["PGSSLMODE"] == "verify-full" for _, env in commands)


def test_postgres_create_failure_does_not_delete_ambiguous_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
        capture: bool = False,
        timeout: int = 14_400,
    ) -> str:
        del cwd, environment, capture, timeout
        commands.append(command)
        if command[0] == "psql":
            return "0"
        if command[0] == "createdb":
            raise sovereign_restore_drill.DrillError("restore command failed: createdb")
        return ""

    monkeypatch.setattr(sovereign_restore_drill, "_run", fake_run)
    with pytest.raises(sovereign_restore_drill.DrillError, match="createdb"):
        sovereign_restore_drill._run_postgres_restore(
            repository=tmp_path,
            connection={
                "host": "postgres-restore.internal.example.de",
                "port": 5432,
                "username": "restore_operator",
                "maintenance_database": "postgres",
                "sslmode": "verify-full",
            },
            pgpass_file=tmp_path / "pgpass",
            backup=tmp_path / "approved.dump",
            restore_database="compliancehub_restore_20260813_change1234",
            required_tables={"tenants"},
            minimum_tables=1,
        )
    assert all(command[0] != "dropdb" for command in commands)


def test_object_restore_byte_checks_and_purges_dedicated_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []
    size_results = iter(
        [
            '{"count":2,"bytes":42}',
            '{"count":0,"bytes":0}',
            '{"count":2,"bytes":42}',
            '{"count":0,"bytes":0}',
        ]
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
        capture: bool = False,
        timeout: int = 14_400,
    ) -> str:
        del cwd, environment, capture, timeout
        commands.append(command)
        return next(size_results) if command[:2] == ["rclone", "size"] else ""

    monkeypatch.setattr(sovereign_restore_drill, "_run", fake_run)
    result = sovereign_restore_drill._run_object_restore(
        repository=tmp_path,
        config_file=tmp_path / "rclone.conf",
        remote="hetzner_restore",
        backup_bucket="compliancehub-backups",
        restore_bucket="compliancehub-restore-drills",
        source_prefix="approved/2026-08-13",
        target_prefix="restore-drills/DR-20260813-CHANGE1234",
    )
    assert result["status"] == "passed"
    assert result["cleanup_status"] == "passed"
    assert result["object_count"] == 2
    assert any(
        command[:2] == ["rclone", "check"] and "--download" in command for command in commands
    )
    assert any(command[:2] == ["rclone", "purge"] for command in commands)


def test_object_copy_failure_still_purges_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []
    size_results = iter(
        ['{"count":1,"bytes":21}', '{"count":0,"bytes":0}', '{"count":0,"bytes":0}']
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
        capture: bool = False,
        timeout: int = 14_400,
    ) -> str:
        del cwd, environment, capture, timeout
        commands.append(command)
        if command[:2] == ["rclone", "copy"]:
            raise sovereign_restore_drill.DrillError("restore command failed: rclone")
        return next(size_results) if command[:2] == ["rclone", "size"] else ""

    monkeypatch.setattr(sovereign_restore_drill, "_run", fake_run)
    with pytest.raises(sovereign_restore_drill.DrillError, match="command failed"):
        sovereign_restore_drill._run_object_restore(
            repository=tmp_path,
            config_file=tmp_path / "rclone.conf",
            remote="hetzner_restore",
            backup_bucket="compliancehub-backups",
            restore_bucket="compliancehub-restore-drills",
            source_prefix="approved/2026-08-13",
            target_prefix="restore-drills/DR-20260813-CHANGE1234",
        )
    assert any(command[:2] == ["rclone", "purge"] for command in commands)


def test_utc_contract_rejects_naive_timestamps() -> None:
    assert sovereign_restore_drill._parse_utc("2026-08-13T12:00:00Z", "created") == datetime(
        2026, 8, 13, 12, tzinfo=UTC
    )
    with pytest.raises(sovereign_restore_drill.DrillError, match="must use UTC"):
        sovereign_restore_drill._parse_utc("2026-08-13T12:00:00", "created")

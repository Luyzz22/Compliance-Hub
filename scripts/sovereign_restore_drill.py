#!/usr/bin/env python3
"""Prove PostgreSQL and S3 restoreability without mutating production targets."""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import stat

# Fixed argv execution is required for the explicitly approved restore tools.
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

CONFIG_FIELDS = {
    "schema_version",
    "drill_id",
    "evidence_root",
    "postgres_backup_file",
    "postgres_backup_sha256",
    "postgres_backup_created_at",
    "postgres_connection_file",
    "postgres_pgpass_file",
    "allowed_postgres_hosts",
    "postgres_restore_database",
    "postgres_required_tables",
    "postgres_minimum_public_tables",
    "object_rclone_config_file",
    "object_remote",
    "object_backup_bucket",
    "object_restore_bucket",
    "object_backup_prefix",
    "object_backup_created_at",
    "object_restore_prefix",
    "allowed_object_hosts",
    "rpo_target_minutes",
    "rto_target_minutes",
    "required_tools",
}
CONNECTION_FIELDS = {"host", "port", "username", "maintenance_database", "sslmode"}
DRILL_ID_PATTERN = re.compile(r"DR-[0-9]{8}-[A-Z0-9]{4,16}")
DATABASE_PATTERN = re.compile(r"compliancehub_restore_[a-z0-9_]{8,48}")
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
BUCKET_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
PREFIX_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,511}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
HOST_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)
FORBIDDEN_OBJECT_HOSTS = {
    "s3.amazonaws.com",
    "storage.googleapis.com",
}


class DrillError(RuntimeError):
    """The restore drill failed without disclosing secret material."""


def _secure_read(
    path: Path,
    *,
    allowed_modes: set[int],
    allowed_uids: set[int],
    minimum_bytes: int = 1,
    maximum_bytes: int = 64 * 1024,
) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise DrillError(f"required drill file cannot be inspected: {path.name}") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or stat.S_IMODE(metadata.st_mode) not in allowed_modes
        or metadata.st_uid not in allowed_uids
        or not minimum_bytes <= metadata.st_size <= maximum_bytes
    ):
        raise DrillError(f"required drill file has an unsafe contract: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DrillError(f"required drill file cannot be opened: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
            raise DrillError(f"required drill file changed during validation: {path.name}")
        content = os.read(descriptor, maximum_bytes + 1)
    finally:
        os.close(descriptor)
    if len(content) > maximum_bytes:
        raise DrillError(f"required drill file is too large: {path.name}")
    return content


def _secure_file_metadata(
    path: Path,
    *,
    allowed_uids: set[int],
    minimum_bytes: int,
    maximum_bytes: int,
) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise DrillError(f"backup cannot be inspected: {path.name}") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_uid not in allowed_uids
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o440}
        or not minimum_bytes <= metadata.st_size <= maximum_bytes
    ):
        raise DrillError(f"backup has an unsafe contract: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DrillError(f"backup cannot be opened: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
        ):
            raise DrillError(f"backup changed during validation: {path.name}")
        return opened
    finally:
        os.close(descriptor)


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise DrillError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DrillError(f"{field} must be an RFC 3339 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise DrillError(f"{field} must use UTC")
    return parsed


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def load_drill_config(
    path: Path,
    *,
    allowed_uids: set[int] | None = None,
) -> dict[str, object]:
    owners = allowed_uids or {0}
    try:
        payload = json.loads(_secure_read(path, allowed_modes={0o400, 0o440}, allowed_uids=owners))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DrillError("restore drill configuration must be valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != CONFIG_FIELDS:
        raise DrillError("restore drill configuration has unknown or missing fields")
    if type(payload.get("schema_version")) is not int or payload.get("schema_version") != 1:
        raise DrillError("restore drill configuration schema must be 1")
    drill_id = payload.get("drill_id")
    if not isinstance(drill_id, str) or not DRILL_ID_PATTERN.fullmatch(drill_id):
        raise DrillError("drill_id is invalid")

    for field in (
        "evidence_root",
        "postgres_backup_file",
        "postgres_connection_file",
        "postgres_pgpass_file",
        "object_rclone_config_file",
    ):
        value = payload.get(field)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise DrillError(f"{field} must be an absolute path")
    backup_digest = str(payload.get("postgres_backup_sha256") or "")
    if not SHA256_PATTERN.fullmatch(backup_digest) or backup_digest == "0" * 64:
        raise DrillError("postgres_backup_sha256 must be a lowercase SHA-256 digest")
    _parse_utc(payload.get("postgres_backup_created_at"), "postgres_backup_created_at")
    _parse_utc(payload.get("object_backup_created_at"), "object_backup_created_at")

    allowed_db_hosts = payload.get("allowed_postgres_hosts")
    allowed_object_hosts = payload.get("allowed_object_hosts")
    for field, hosts in (
        ("allowed_postgres_hosts", allowed_db_hosts),
        ("allowed_object_hosts", allowed_object_hosts),
    ):
        if (
            not isinstance(hosts, list)
            or not hosts
            or any(not isinstance(host, str) or not HOST_PATTERN.fullmatch(host) for host in hosts)
        ):
            raise DrillError(f"{field} must be a non-empty host allowlist")
    if any(host in FORBIDDEN_OBJECT_HOSTS for host in allowed_object_hosts):
        raise DrillError("object host allowlist contains a forbidden provider")

    database = payload.get("postgres_restore_database")
    if not isinstance(database, str) or not DATABASE_PATTERN.fullmatch(database):
        raise DrillError("postgres restore database must use the isolated drill prefix")
    required_tables = payload.get("postgres_required_tables")
    if (
        not isinstance(required_tables, list)
        or not required_tables
        or any(
            not isinstance(name, str) or not NAME_PATTERN.fullmatch(name)
            for name in required_tables
        )
    ):
        raise DrillError("postgres_required_tables is invalid")
    minimum_tables = payload.get("postgres_minimum_public_tables")
    if not isinstance(minimum_tables, int) or not 1 <= minimum_tables <= 10_000:
        raise DrillError("postgres_minimum_public_tables is invalid")

    remote = payload.get("object_remote")
    backup_bucket = payload.get("object_backup_bucket")
    restore_bucket = payload.get("object_restore_bucket")
    source_prefix = payload.get("object_backup_prefix")
    target_prefix = payload.get("object_restore_prefix")
    if not isinstance(remote, str) or not NAME_PATTERN.fullmatch(remote):
        raise DrillError("object_remote is invalid")
    for field, bucket in (
        ("object_backup_bucket", backup_bucket),
        ("object_restore_bucket", restore_bucket),
    ):
        if not isinstance(bucket, str) or not BUCKET_PATTERN.fullmatch(bucket):
            raise DrillError(f"{field} is invalid")
    if restore_bucket == backup_bucket or "restore" not in str(restore_bucket).split("-"):
        raise DrillError("object restore bucket must be a dedicated restore bucket")
    if (
        not isinstance(source_prefix, str)
        or not PREFIX_PATTERN.fullmatch(source_prefix)
        or source_prefix.startswith("/")
        or ".." in source_prefix.split("/")
    ):
        raise DrillError("object backup prefix is invalid")
    expected_target = f"restore-drills/{drill_id}"
    if target_prefix != expected_target or target_prefix == source_prefix:
        raise DrillError("object restore prefix must be the dedicated drill target")

    for field in ("rpo_target_minutes", "rto_target_minutes"):
        value = payload.get(field)
        if not isinstance(value, int) or not 1 <= value <= 10_080:
            raise DrillError(f"{field} is invalid")
    tools = payload.get("required_tools")
    if (
        not isinstance(tools, dict)
        or set(tools) != {"psql", "pg_restore", "createdb", "dropdb", "rclone"}
        or any(not isinstance(value, str) or not value for value in tools.values())
    ):
        raise DrillError("required restore tool versions are invalid")
    postgres_versions = {str(tools[name]) for name in ("psql", "pg_restore", "createdb", "dropdb")}
    if len(postgres_versions) != 1 or not re.fullmatch(r"[0-9]+\.[0-9]+", postgres_versions.pop()):
        raise DrillError("PostgreSQL restore tools must use one exact approved version")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", str(tools["rclone"])):
        raise DrillError("rclone must use an exact approved version")
    return payload


def _load_postgres_connection(
    path: Path,
    *,
    allowed_hosts: set[str],
    allowed_uids: set[int],
) -> dict[str, object]:
    try:
        connection = json.loads(
            _secure_read(path, allowed_modes={0o400, 0o440}, allowed_uids=allowed_uids)
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DrillError("PostgreSQL connection contract must be valid JSON") from exc
    if not isinstance(connection, dict) or set(connection) != CONNECTION_FIELDS:
        raise DrillError("PostgreSQL connection contract has unknown or missing fields")
    host = connection.get("host")
    port = connection.get("port")
    username = connection.get("username")
    database = connection.get("maintenance_database")
    if (
        not isinstance(host, str)
        or not HOST_PATTERN.fullmatch(host)
        or host not in allowed_hosts
        or not re.search(r"(?:^|[.-])restore(?:[.-]|$)", host)
    ):
        raise DrillError("PostgreSQL restore host is not allowed")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise DrillError("PostgreSQL restore port is invalid")
    if not isinstance(username, str) or not NAME_PATTERN.fullmatch(username):
        raise DrillError("PostgreSQL restore username is invalid")
    if database not in {"postgres", "template1"}:
        raise DrillError("PostgreSQL maintenance database is invalid")
    if connection.get("sslmode") not in {"verify-full", "verify-ca"}:
        raise DrillError("PostgreSQL restore connection must verify TLS")
    return connection


def _validate_rclone_config(
    path: Path,
    *,
    remote: str,
    allowed_hosts: set[str],
    allowed_uids: set[int],
) -> str:
    content = _secure_read(
        path,
        allowed_modes={0o400, 0o440},
        allowed_uids=allowed_uids,
        maximum_bytes=256 * 1024,
    )
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error) as exc:
        raise DrillError("rclone configuration is invalid") from exc
    if (
        parser.defaults()
        or set(parser.sections()) != {remote}
        or set(parser[remote])
        != {"type", "provider", "endpoint", "access_key_id", "secret_access_key", "acl"}
        or parser[remote].get("type") != "s3"
    ):
        raise DrillError("rclone remote must be an S3 configuration")
    if parser[remote].get("provider") != "Other":
        raise DrillError("rclone S3 provider must use the approved generic contract")
    endpoint = urlsplit(parser[remote].get("endpoint", ""))
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.hostname not in allowed_hosts
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise DrillError("rclone S3 endpoint is not an allowed HTTPS host")
    if (
        len(parser[remote].get("access_key_id", "")) < 16
        or len(parser[remote].get("secret_access_key", "")) < 32
        or parser[remote].get("acl", "private") != "private"
    ):
        raise DrillError("rclone S3 credentials are unavailable")
    return endpoint.hostname


def _validate_pgpass(content: bytes, connection: dict[str, object]) -> None:
    try:
        value = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DrillError("PostgreSQL password file must be UTF-8") from exc
    if value.endswith("\n"):
        value = value[:-1]
    if "\n" in value or "\r" in value or "\\" in value:
        raise DrillError("PostgreSQL password file must contain one literal entry")
    fields = value.split(":", 4)
    expected = [
        str(connection["host"]),
        str(connection["port"]),
        "*",
        str(connection["username"]),
    ]
    if len(fields) != 5 or fields[:4] != expected or len(fields[4]) < 20:
        raise DrillError("PostgreSQL password file does not match the restore connection")


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    capture: bool = False,
    timeout: int = 14_400,
) -> str:
    try:
        # No shell is used; argv entries are validated configuration or fixed controls.
        result = subprocess.run(  # nosec B603
            command,
            cwd=cwd,
            env=environment,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DrillError(f"restore command could not complete: {command[0]}") from exc
    if result.returncode:
        raise DrillError(f"restore command failed: {command[0]}")
    return result.stdout.strip() if capture else ""


def _check_tool_versions(config: dict[str, object], repository: Path) -> dict[str, str]:
    expected = config["required_tools"]
    if not isinstance(expected, dict):
        raise DrillError("restore tool contract is unavailable")
    versions: dict[str, str] = {}
    environment = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}
    for tool in ("psql", "pg_restore", "createdb", "dropdb", "rclone"):
        output = _run([tool, "--version"], cwd=repository, environment=environment, capture=True)
        version = str(expected[tool])
        first_line = output.splitlines()[0] if output else ""
        if not re.search(rf"(?:^|[ (]){re.escape(version)}(?:$|[ )])", first_line):
            raise DrillError(f"{tool} version does not match the approved drill contract")
        versions[tool] = version
    return versions


def _postgres_args(connection: dict[str, object], database: str) -> list[str]:
    return [
        "--host",
        str(connection["host"]),
        "--port",
        str(connection["port"]),
        "--username",
        str(connection["username"]),
        "--dbname",
        database,
    ]


def _postgres_server_args(connection: dict[str, object]) -> list[str]:
    return [
        "--host",
        str(connection["host"]),
        "--port",
        str(connection["port"]),
        "--username",
        str(connection["username"]),
    ]


def _run_postgres_restore(
    *,
    repository: Path,
    connection: dict[str, object],
    pgpass_file: Path,
    backup: Path,
    restore_database: str,
    required_tables: set[str],
    minimum_tables: int,
) -> dict[str, object]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PGPASSFILE": str(pgpass_file),
        "PGCONNECT_TIMEOUT": "15",
        "PGSSLMODE": str(connection["sslmode"]),
    }
    maintenance = str(connection["maintenance_database"])
    _run(["pg_restore", "--list", str(backup)], cwd=repository, environment=environment)
    database_exists = _run(
        [
            "psql",
            *_postgres_args(connection, maintenance),
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set",
            "ON_ERROR_STOP=1",
            "--command",
            "SELECT count(*) FROM pg_database WHERE datname = "
            ":'restore_database' AND datallowconn;",
            "--variable",
            f"restore_database={restore_database}",
        ],
        cwd=repository,
        environment=environment,
        capture=True,
    )
    if database_exists != "0":
        raise DrillError("PostgreSQL restore target must not exist")
    started = datetime.now(UTC)
    created = False
    cleanup_status = "failed"
    try:
        _run(
            [
                "createdb",
                *_postgres_server_args(connection),
                "--maintenance-db",
                maintenance,
                restore_database,
            ],
            cwd=repository,
            environment=environment,
        )
        created = True
        _run(
            [
                "pg_restore",
                *_postgres_args(connection, restore_database),
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                str(backup),
            ],
            cwd=repository,
            environment=environment,
        )
        query = (
            "SELECT json_build_object("
            "'database',current_database(),"
            "'table_count',(SELECT count(*)::int FROM pg_catalog.pg_tables "
            "WHERE schemaname='public'),"
            "'tables',(SELECT coalesce(json_agg(tablename ORDER BY tablename),'[]'::json) "
            "FROM pg_catalog.pg_tables WHERE schemaname='public'));"
        )
        output = _run(
            [
                "psql",
                *_postgres_args(connection, restore_database),
                "--no-psqlrc",
                "--tuples-only",
                "--no-align",
                "--set",
                "ON_ERROR_STOP=1",
                "--command",
                query,
            ],
            cwd=repository,
            environment=environment,
            capture=True,
        )
        try:
            result = json.loads(output)
            tables = result["tables"]
            table_count = result["table_count"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise DrillError("PostgreSQL restore verification output is invalid") from exc
        if (
            result.get("database") != restore_database
            or not isinstance(table_count, int)
            or table_count < minimum_tables
            or not isinstance(tables, list)
            or not required_tables.issubset(set(tables))
        ):
            raise DrillError("PostgreSQL restored schema does not meet the approved contract")
        result_payload = {
            "status": "passed",
            "public_table_count": table_count,
            "required_tables": sorted(required_tables),
            "restore_seconds": round((datetime.now(UTC) - started).total_seconds(), 3),
        }
    finally:
        if created:
            _run(
                [
                    "dropdb",
                    *_postgres_server_args(connection),
                    "--maintenance-db",
                    maintenance,
                    "--force",
                    "--if-exists",
                    restore_database,
                ],
                cwd=repository,
                environment=environment,
            )
            cleanup_status = "passed"
    if cleanup_status != "passed":
        raise DrillError("PostgreSQL restore target cleanup did not complete")
    result_payload["cleanup_status"] = cleanup_status
    return result_payload


def _rclone_size(
    reference: str,
    *,
    repository: Path,
    config_file: Path,
    environment: dict[str, str],
) -> tuple[int, int]:
    output = _run(
        ["rclone", "size", reference, "--json", "--config", str(config_file)],
        cwd=repository,
        environment=environment,
        capture=True,
    )
    try:
        payload = json.loads(output)
        count = payload.get("count", payload.get("Count"))
        total_bytes = payload.get("bytes", payload.get("Bytes"))
    except (json.JSONDecodeError, TypeError) as exc:
        raise DrillError("object restore size output is invalid") from exc
    if not isinstance(count, int) or not isinstance(total_bytes, int):
        raise DrillError("object restore size output is incomplete")
    return count, total_bytes


def _run_object_restore(
    *,
    repository: Path,
    config_file: Path,
    remote: str,
    backup_bucket: str,
    restore_bucket: str,
    source_prefix: str,
    target_prefix: str,
) -> dict[str, object]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }
    source = f"{remote}:{backup_bucket}/{source_prefix}"
    target = f"{remote}:{restore_bucket}/{target_prefix}"
    source_count, source_bytes = _rclone_size(
        source,
        repository=repository,
        config_file=config_file,
        environment=environment,
    )
    target_count, target_bytes = _rclone_size(
        target,
        repository=repository,
        config_file=config_file,
        environment=environment,
    )
    if source_count <= 0 or source_bytes <= 0:
        raise DrillError("object backup is empty")
    if target_count or target_bytes:
        raise DrillError("object restore target must be empty")
    started = datetime.now(UTC)
    copy_attempted = False
    cleanup_status = "failed"
    try:
        copy_attempted = True
        _run(
            [
                "rclone",
                "copy",
                source,
                target,
                "--config",
                str(config_file),
                "--metadata",
                "--immutable",
            ],
            cwd=repository,
            environment=environment,
        )
        _run(
            [
                "rclone",
                "check",
                source,
                target,
                "--config",
                str(config_file),
                "--download",
                "--one-way",
            ],
            cwd=repository,
            environment=environment,
        )
        restored_count, restored_bytes = _rclone_size(
            target,
            repository=repository,
            config_file=config_file,
            environment=environment,
        )
        if (restored_count, restored_bytes) != (source_count, source_bytes):
            raise DrillError("object restore counts or bytes do not match the backup")
        result_payload = {
            "status": "passed",
            "object_count": restored_count,
            "total_bytes": restored_bytes,
            "verified_object_count": restored_count,
            "restore_seconds": round((datetime.now(UTC) - started).total_seconds(), 3),
        }
    finally:
        if copy_attempted:
            _run(
                ["rclone", "purge", target, "--config", str(config_file)],
                cwd=repository,
                environment=environment,
            )
            remaining_count, remaining_bytes = _rclone_size(
                target,
                repository=repository,
                config_file=config_file,
                environment=environment,
            )
            if remaining_count or remaining_bytes:
                raise DrillError("object restore target cleanup is incomplete")
            cleanup_status = "passed"
    if cleanup_status != "passed":
        raise DrillError("object restore target cleanup did not complete")
    result_payload["cleanup_status"] = cleanup_status
    return result_payload


def _ensure_evidence_root(root: Path, *, allowed_uids: set[int]) -> None:
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise DrillError("restore evidence root cannot be inspected") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or root.is_symlink()
        or metadata.st_uid not in allowed_uids
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DrillError("restore evidence root must be an owner-only directory")


def _reserve_drill(root: Path, drill_id: str) -> Path:
    lock = root / f".{drill_id}.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise DrillError("restore drill id is already reserved and requires review") from exc
    try:
        content = f"drill_id={drill_id}\nreserved_at={datetime.now(UTC).isoformat()}\n".encode()
        written = os.write(descriptor, content)
        if written != len(content):
            raise DrillError("restore drill reservation write did not complete")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return lock


def _write_json(path: Path, payload: object) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(encoded):
            count = os.write(descriptor, encoded[written:])
            if count <= 0:
                raise DrillError("restore evidence write did not complete")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_drill(
    config: dict[str, object],
    *,
    repository: Path,
    allowed_uids: set[int] | None = None,
) -> Path:
    runtime_uid = os.geteuid()
    trusted_config_owners = allowed_uids or {0}
    started = datetime.now(UTC)
    backup_created = _parse_utc(config["postgres_backup_created_at"], "postgres backup")
    object_created = _parse_utc(config["object_backup_created_at"], "object backup")
    rpo_minutes = round(
        max((started - backup_created).total_seconds(), (started - object_created).total_seconds())
        / 60,
        3,
    )
    rpo_target = int(config["rpo_target_minutes"])
    if rpo_minutes < 0 or rpo_minutes > rpo_target:
        raise DrillError("backup age exceeds the approved RPO")

    evidence_root = Path(str(config["evidence_root"]))
    _ensure_evidence_root(evidence_root, allowed_uids={runtime_uid})
    evidence_path = evidence_root / f"{config['drill_id']}.json"
    if evidence_path.exists() or evidence_path.is_symlink():
        raise DrillError("restore evidence target already exists")

    backup = Path(str(config["postgres_backup_file"]))
    _secure_file_metadata(
        backup,
        allowed_uids={0},
        minimum_bytes=1024,
        maximum_bytes=1024 * 1024 * 1024 * 1024,
    )
    backup_digest = _sha256_file(backup)
    if backup_digest != config["postgres_backup_sha256"]:
        raise DrillError("PostgreSQL backup digest does not match the approved contract")

    connection = _load_postgres_connection(
        Path(str(config["postgres_connection_file"])),
        allowed_hosts=set(config["allowed_postgres_hosts"]),
        allowed_uids=trusted_config_owners,
    )
    pgpass = Path(str(config["postgres_pgpass_file"]))
    pgpass_content = _secure_read(
        pgpass,
        allowed_modes={0o400},
        allowed_uids={0, runtime_uid},
        minimum_bytes=16,
        maximum_bytes=16 * 1024,
    )
    _validate_pgpass(pgpass_content, connection)
    object_host = _validate_rclone_config(
        Path(str(config["object_rclone_config_file"])),
        remote=str(config["object_remote"]),
        allowed_hosts=set(config["allowed_object_hosts"]),
        allowed_uids={0, runtime_uid},
    )
    tools = _check_tool_versions(config, repository)
    _reserve_drill(evidence_root, str(config["drill_id"]))

    postgres_result = _run_postgres_restore(
        repository=repository,
        connection=connection,
        pgpass_file=pgpass,
        backup=backup,
        restore_database=str(config["postgres_restore_database"]),
        required_tables=set(config["postgres_required_tables"]),
        minimum_tables=int(config["postgres_minimum_public_tables"]),
    )
    object_result = _run_object_restore(
        repository=repository,
        config_file=Path(str(config["object_rclone_config_file"])),
        remote=str(config["object_remote"]),
        backup_bucket=str(config["object_backup_bucket"]),
        restore_bucket=str(config["object_restore_bucket"]),
        source_prefix=str(config["object_backup_prefix"]),
        target_prefix=str(config["object_restore_prefix"]),
    )
    completed = datetime.now(UTC)
    rto_seconds = round((completed - started).total_seconds(), 3)
    rto_target_seconds = int(config["rto_target_minutes"]) * 60
    recovery_status = "passed" if rto_seconds <= rto_target_seconds else "failed"
    payload = {
        "schema_version": 1,
        "drill_id": config["drill_id"],
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": completed.isoformat().replace("+00:00", "Z"),
        "tools": tools,
        "postgres": {
            **postgres_result,
            "backup_sha256": backup_digest,
            "backup_created_at": backup_created.isoformat().replace("+00:00", "Z"),
            "restore_host_sha256": hashlib.sha256(
                str(connection["host"]).encode("utf-8")
            ).hexdigest(),
        },
        "object_storage": {
            **object_result,
            "backup_reference_sha256": hashlib.sha256(
                (
                    f"{config['object_remote']}:{config['object_backup_bucket']}/"
                    f"{config['object_backup_prefix']}"
                ).encode()
            ).hexdigest(),
            "backup_created_at": object_created.isoformat().replace("+00:00", "Z"),
            "endpoint_host_sha256": hashlib.sha256(object_host.encode("utf-8")).hexdigest(),
        },
        "recovery": {
            "status": recovery_status,
            "rpo_minutes": rpo_minutes,
            "rpo_target_minutes": rpo_target,
            "rto_seconds": rto_seconds,
            "rto_target_seconds": rto_target_seconds,
        },
    }
    _write_json(evidence_path, payload)
    if recovery_status != "passed":
        raise DrillError("restore drill exceeded the approved RTO")
    return evidence_path


def main() -> int:
    os.umask(0o077)
    repository = Path(__file__).resolve().parents[1]
    config_path = Path(os.environ.get("COMPLIANCEHUB_RESTORE_DRILL_CONFIG", ""))
    if not config_path.is_absolute():
        raise DrillError("COMPLIANCEHUB_RESTORE_DRILL_CONFIG must be an absolute path")
    config = load_drill_config(config_path)
    evidence = run_drill(config, repository=repository)
    print(f"restore_drill=passed evidence={evidence.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillError as exc:
        print(f"restore_drill=failed: {exc}", file=os.sys.stderr)
        raise SystemExit(1) from exc

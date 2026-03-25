from __future__ import annotations

import csv
import io
import json
import re
from uuid import uuid4

from openpyxl import load_workbook
from pydantic import BaseModel, ValidationError

from app.ai_system_models import (
    AIActCategory,
    AIImportResult,
    AIImportRowError,
    AISystem,
    AISystemCreate,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemUpdate,
    DataSensitivity,
)
from app.policy_service import evaluate_policies_for_ai_system
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository
from app.security import AuthContext

ALLOWED_FIELDS = frozenset(
    {
        "id",
        "name",
        "description",
        "business_unit",
        "risk_level",
        "ai_act_category",
        "owner_email",
        "criticality",
        "data_sensitivity",
        "has_incident_runbook",
        "has_supplier_risk_register",
        "has_backup_runbook",
        "gdpr_dpia_required",
    }
)

HEADER_SYNONYMS: dict[str, str] = {
    "system_id": "id",
    "uuid": "id",
    "risiko": "risk_level",
    "risikostufe": "risk_level",
    "risk": "risk_level",
    "ai_category": "ai_act_category",
    "eu_ai_act_category": "ai_act_category",
    "kategorie": "ai_act_category",
    "bu": "business_unit",
    "geschaeftseinheit": "business_unit",
    "abteilung": "business_unit",
    "businessunit": "business_unit",
    "owner": "owner_email",
    "e_mail": "owner_email",
    "dpia": "gdpr_dpia_required",
    "gdpr_dpia": "gdpr_dpia_required",
    "incident_runbook": "has_incident_runbook",
    "supplier_risk": "has_supplier_risk_register",
    "supplier_register": "has_supplier_risk_register",
    "backup_runbook": "has_backup_runbook",
}


def _normalize_header_key(cell: str) -> str:
    s = cell.strip().lower().replace("\ufeff", "")
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def _resolve_field(normalized_header: str) -> str | None:
    key = HEADER_SYNONYMS.get(normalized_header, normalized_header)
    return key if key in ALLOWED_FIELDS else None


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None or not str(raw).strip():
        return default
    s = str(raw).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "ja", "j", "wahr", "x", "✓", "ok"):
        return True
    if s in ("0", "false", "f", "no", "n", "nein", "-", ""):
        return False
    raise ValueError(f"Ungültiger Boolescher Wert: {raw!r}")


def _parse_risk_level(raw: str) -> AISystemRiskLevel:
    s = raw.strip().lower().replace(" ", "_").replace("-", "_")
    mapping: dict[str, AISystemRiskLevel] = {
        "low": AISystemRiskLevel.low,
        "niedrig": AISystemRiskLevel.low,
        "gering": AISystemRiskLevel.low,
        "limited": AISystemRiskLevel.limited,
        "begrenzt": AISystemRiskLevel.limited,
        "high": AISystemRiskLevel.high,
        "hoch": AISystemRiskLevel.high,
        "elevated": AISystemRiskLevel.high,
        "unacceptable": AISystemRiskLevel.unacceptable,
        "unakzeptabel": AISystemRiskLevel.unacceptable,
        "inakzeptabel": AISystemRiskLevel.unacceptable,
    }
    if s in mapping:
        return mapping[s]
    try:
        return AISystemRiskLevel(s)
    except ValueError as exc:
        raise ValueError(f"Ungültiges risk_level: {raw!r}") from exc


def _parse_ai_act_category(raw: str) -> AIActCategory:
    s = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases: dict[str, AIActCategory] = {
        "highrisk": AIActCategory.high_risk,
        "high_risk": AIActCategory.high_risk,
        "hohes_risiko": AIActCategory.high_risk,
        "limitedrisk": AIActCategory.limited_risk,
        "limited_risk": AIActCategory.limited_risk,
        "begrenztes_risiko": AIActCategory.limited_risk,
        "minimalrisk": AIActCategory.minimal_risk,
        "minimal_risk": AIActCategory.minimal_risk,
        "minimales_risiko": AIActCategory.minimal_risk,
        "prohibited": AIActCategory.prohibited,
        "verboten": AIActCategory.prohibited,
    }
    if s in aliases:
        return aliases[s]
    try:
        return AIActCategory(s)
    except ValueError as exc:
        raise ValueError(f"Ungültige ai_act_category: {raw!r}") from exc


def _parse_criticality(raw: str | None) -> AISystemCriticality:
    if raw is None or not str(raw).strip():
        return AISystemCriticality.medium
    s = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    aliases: dict[str, AISystemCriticality] = {
        "low": AISystemCriticality.low,
        "niedrig": AISystemCriticality.low,
        "medium": AISystemCriticality.medium,
        "mittel": AISystemCriticality.medium,
        "high": AISystemCriticality.high,
        "hoch": AISystemCriticality.high,
        "very_high": AISystemCriticality.very_high,
        "veryhigh": AISystemCriticality.very_high,
        "sehr_hoch": AISystemCriticality.very_high,
        "sehrhoch": AISystemCriticality.very_high,
    }
    if s in aliases:
        return aliases[s]
    try:
        return AISystemCriticality(s)
    except ValueError as exc:
        raise ValueError(f"Ungültige criticality: {raw!r}") from exc


def _parse_data_sensitivity(raw: str | None) -> DataSensitivity:
    if raw is None or not str(raw).strip():
        return DataSensitivity.internal
    s = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    aliases: dict[str, DataSensitivity] = {
        "public": DataSensitivity.public,
        "oeffentlich": DataSensitivity.public,
        "internal": DataSensitivity.internal,
        "intern": DataSensitivity.internal,
        "confidential": DataSensitivity.confidential,
        "vertraulich": DataSensitivity.confidential,
        "restricted": DataSensitivity.restricted,
        "streng_vertraulich": DataSensitivity.restricted,
    }
    if s in aliases:
        return aliases[s]
    try:
        return DataSensitivity(s)
    except ValueError as exc:
        raise ValueError(f"Ungültige data_sensitivity: {raw!r}") from exc


def _row_to_create_payload(row: dict[str, str], resolved_id: str) -> AISystemCreate:
    name = (row.get("name") or "").strip()
    description = (row.get("description") or "").strip()
    business_unit = (row.get("business_unit") or "").strip()
    if not name:
        raise ValueError("Pflichtfeld name ist leer")
    if not description:
        raise ValueError("Pflichtfeld description ist leer")
    if not business_unit:
        raise ValueError("Pflichtfeld business_unit ist leer")
    rl_raw = (row.get("risk_level") or "").strip()
    ac_raw = (row.get("ai_act_category") or "").strip()
    if not rl_raw:
        raise ValueError("Pflichtfeld risk_level ist leer")
    if not ac_raw:
        raise ValueError("Pflichtfeld ai_act_category ist leer")
    owner = (row.get("owner_email") or "").strip() or None
    return AISystemCreate(
        id=resolved_id,
        name=name,
        description=description,
        business_unit=business_unit,
        risk_level=_parse_risk_level(rl_raw),
        ai_act_category=_parse_ai_act_category(ac_raw),
        gdpr_dpia_required=_parse_bool(row.get("gdpr_dpia_required"), False),
        owner_email=owner,
        criticality=_parse_criticality(row.get("criticality")),
        data_sensitivity=_parse_data_sensitivity(row.get("data_sensitivity")),
        has_incident_runbook=_parse_bool(row.get("has_incident_runbook"), False),
        has_supplier_risk_register=_parse_bool(row.get("has_supplier_risk_register"), False),
        has_backup_runbook=_parse_bool(row.get("has_backup_runbook"), False),
    )


def _create_to_update(create: AISystemCreate) -> AISystemUpdate:
    return AISystemUpdate(
        name=create.name,
        description=create.description,
        business_unit=create.business_unit,
        risk_level=create.risk_level,
        ai_act_category=create.ai_act_category,
        gdpr_dpia_required=create.gdpr_dpia_required,
        owner_email=create.owner_email,
        criticality=create.criticality,
        data_sensitivity=create.data_sensitivity,
        has_incident_runbook=create.has_incident_runbook,
        has_supplier_risk_register=create.has_supplier_risk_register,
        has_backup_runbook=create.has_backup_runbook,
    )


def _model_to_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), default=str)


def _iter_csv_rows(data: bytes) -> list[tuple[int, dict[str, str]]]:
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    header_cells = rows[0]
    canonical = [_resolve_field(_normalize_header_key(h or "")) for h in header_cells]
    out: list[tuple[int, dict[str, str]]] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        d: dict[str, str] = {}
        for j, key in enumerate(canonical):
            if key is None:
                continue
            val = (row[j] if j < len(row) else "") or ""
            d[key] = str(val).strip()
        if not any(v for v in d.values()):
            continue
        out.append((row_idx, d))
    return out


def _iter_xlsx_rows(data: bytes) -> list[tuple[int, dict[str, str]]]:
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None)
        if not header_row:
            return []
        header_cells = [str(c) if c is not None else "" for c in header_row]
        canonical = [_resolve_field(_normalize_header_key(h)) for h in header_cells]
        out: list[tuple[int, dict[str, str]]] = []
        for row_idx, row in enumerate(rows_iter, start=2):
            if row is None:
                continue
            d: dict[str, str] = {}
            for j, key in enumerate(canonical):
                if key is None:
                    continue
                cell = row[j] if j < len(row) else None
                val = "" if cell is None else str(cell).strip()
                d[key] = val
            if not any(v for v in d.values()):
                continue
            out.append((row_idx, d))
        return out
    finally:
        wb.close()


def _parse_table_rows(filename: str, data: bytes) -> list[tuple[int, dict[str, str]]]:
    name = filename.lower()
    if name.endswith(".xlsx"):
        return _iter_xlsx_rows(data)
    return _iter_csv_rows(data)


def _after_create(
    tenant_id: str,
    auth: AuthContext,
    created: AISystem,
    audit_log_repo: AuditLogRepository,
    audit_event_repo: AuditRepository,
    policy_repo: PolicyRepository,
    violation_repo: ViolationRepository,
) -> None:
    policy_repo.ensure_default_policy_rules(tenant_id)
    audit_log_repo.record_event(
        tenant_id=tenant_id,
        actor="system",
        action="create_ai_system",
        entity_type="AISystem",
        entity_id=created.id,
        before=None,
        after=_model_to_json(created),
    )
    audit_event_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth.api_key,
        entity_type="ai_system",
        entity_id=created.id,
        action="created",
        metadata={"status": created.status.value},
    )
    evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=created,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_event_repo,
        actor_type="api_key",
        actor_id=auth.api_key,
    )


def _after_update(
    tenant_id: str,
    auth: AuthContext,
    updated: AISystem,
    audit_event_repo: AuditRepository,
    policy_repo: PolicyRepository,
    violation_repo: ViolationRepository,
) -> None:
    audit_event_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth.api_key,
        entity_type="ai_system",
        entity_id=updated.id,
        action="updated",
        metadata={"status": updated.status.value},
    )
    evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=updated,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_event_repo,
        actor_type="api_key",
        actor_id=auth.api_key,
    )


def import_ai_systems_from_file(
    *,
    tenant_id: str,
    auth: AuthContext,
    filename: str,
    data: bytes,
    repository: AISystemRepository,
    audit_log_repo: AuditLogRepository,
    audit_event_repo: AuditRepository,
    policy_repo: PolicyRepository,
    violation_repo: ViolationRepository,
) -> AIImportResult:
    errors: list[AIImportRowError] = []
    imported = 0

    try:
        parsed = _parse_table_rows(filename, data)
    except Exception as exc:  # noqa: BLE001 — tolerant catch for malformed XLSX/CSV
        return AIImportResult(
            total_rows=0,
            imported_count=0,
            failed_count=1,
            errors=[
                AIImportRowError(row_number=0, message=f"Datei konnte nicht gelesen werden: {exc}")
            ],
        )

    total = len(parsed)

    for row_number, row in parsed:
        try:
            explicit_id = (row.get("id") or "").strip()
            name = (row.get("name") or "").strip()

            if explicit_id:
                target_id = explicit_id
                existing = repository.get_by_id(tenant_id, target_id)
                payload = _row_to_create_payload(row, target_id)
                if existing is None:
                    created = repository.create(tenant_id, payload)
                    _after_create(
                        tenant_id,
                        auth,
                        created,
                        audit_log_repo,
                        audit_event_repo,
                        policy_repo,
                        violation_repo,
                    )
                else:
                    updated = repository.update(
                        tenant_id,
                        target_id,
                        _create_to_update(payload),
                    )
                    _after_update(
                        tenant_id,
                        auth,
                        updated,
                        audit_event_repo,
                        policy_repo,
                        violation_repo,
                    )
            else:
                if not name:
                    raise ValueError("Ohne id ist name Pflicht")
                existing = repository.get_by_name(tenant_id, name)
                new_id = str(uuid4()) if existing is None else existing.id
                payload = _row_to_create_payload(row, new_id)
                if existing is None:
                    created = repository.create(tenant_id, payload)
                    _after_create(
                        tenant_id,
                        auth,
                        created,
                        audit_log_repo,
                        audit_event_repo,
                        policy_repo,
                        violation_repo,
                    )
                else:
                    updated = repository.update(
                        tenant_id,
                        existing.id,
                        _create_to_update(payload),
                    )
                    _after_update(
                        tenant_id,
                        auth,
                        updated,
                        audit_event_repo,
                        policy_repo,
                        violation_repo,
                    )
            imported += 1
        except (ValueError, ValidationError) as exc:
            msg = str(exc)
            if isinstance(exc, ValidationError):
                msg = "; ".join(f"{e['loc']}: {e['msg']}" for e in exc.errors())
            errors.append(AIImportRowError(row_number=row_number, message=msg))

    return AIImportResult(
        total_rows=total,
        imported_count=imported,
        failed_count=len(errors),
        errors=errors,
    )

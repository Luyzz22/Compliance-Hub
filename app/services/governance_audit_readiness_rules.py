"""
Deterministic audit readiness & evidence completeness (MVP).

No ML: rules are explicit so advisors and auditors can explain outcomes.
Combines unified-control status, next_review_at, and evidence source_type coverage
against required evidence keys per in-scope framework (defaults + tenant overrides).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Default evidence keys per framework tag (tenant DB rows extend/override per
# framework_tag + evidence_type_key). Keys are matched case-insensitively
# against governance_control_evidence.source_type.
# ---------------------------------------------------------------------------
DEFAULT_REQUIRED_EVIDENCE_BY_FRAMEWORK: dict[str, tuple[str, ...]] = {
    "EU_AI_ACT": ("policy", "technical_record", "manual"),
    "ISO_42001": ("policy", "manual"),
    "ISO_27001": ("policy", "procedure"),
    "ISO_27701": ("policy", "privacy_record"),
    "NIS2": ("policy", "incident_evidence", "manual"),
}


def normalize_framework_tag(tag: str) -> str:
    return tag.strip().upper().replace(" ", "_").replace("-", "_")


def statuses_sufficient_for_readiness(status: str) -> bool:
    """MVP: only implemented counts as fully compliant; extend later (e.g. monitored)."""
    return status.strip().lower() == "implemented"


def review_overdue(
    *,
    status: str,
    next_review_at: datetime | None,
    now: datetime,
) -> bool:
    """Aligns with governance control KPI semantics (explicit overdue + date drift)."""
    st = status.strip().lower()
    if st == "overdue":
        return True
    if next_review_at is None:
        return False
    dt = next_review_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return bool(st == "implemented" and dt < now)


def evidence_type_satisfied(required_key: str, present_source_types: set[str]) -> bool:
    rk = required_key.lower().strip()
    if rk in present_source_types:
        return True
    for p in present_source_types:
        if rk in p or p in rk:
            return True
    return False


def merged_required_keys_for_framework(
    framework_tag: str,
    tenant_rows_for_fw: list[tuple[str, str, int]],
) -> list[tuple[str, str, int]]:
    """
    Returns (evidence_type_key_lower, label, priority) for one framework.
    Tenant rows override defaults for the same key; additional keys append.
    """
    fw = normalize_framework_tag(framework_tag)
    defaults = DEFAULT_REQUIRED_EVIDENCE_BY_FRAMEWORK.get(fw, ("policy", "manual"))
    out: dict[str, tuple[str, int]] = {}
    for k in defaults:
        kl = k.lower()
        out[kl] = (k, 2)
    for key, label, prio in tenant_rows_for_fw:
        kl = key.lower()
        out[kl] = (label or key, prio)
    return sorted(((kl, lab, pr) for kl, (lab, pr) in out.items()), key=lambda x: (-x[2], x[0]))


@dataclass(frozen=True)
class ControlSignals:
    control_id: str
    title: str
    framework_tags: list[str]
    status: str
    owner: str | None
    next_review_at: datetime | None
    evidence_source_types: list[str]


def compute_control_metrics(
    ctrl: ControlSignals,
    case_frameworks: set[str],
    tenant_req_index: dict[str, list[tuple[str, str, int]]],
    now: datetime,
) -> tuple[float, list[str], bool, bool, list[tuple[str, str, str, int]]]:
    """
    Returns (completeness_pct, missing_types, is_ready, review_overdue_flag, gap_rows).

    gap_rows: (framework, missing_key, label, priority) for board / gap tab.
    """
    cfw = {normalize_framework_tag(x) for x in case_frameworks}
    tags = {normalize_framework_tag(t) for t in ctrl.framework_tags}
    active_fw = sorted(cfw & tags)
    present = {str(x).lower().strip() for x in ctrl.evidence_source_types if x}

    required_flat: list[tuple[str, str, int, str]] = []
    for fw in active_fw:
        rows = tenant_req_index.get(fw, [])
        for ek, lab, pr in merged_required_keys_for_framework(fw, rows):
            required_flat.append((ek, lab, pr, fw))

    missing: list[str] = []
    gap_detail: list[tuple[str, str, str, int]] = []
    met = 0
    total = len(required_flat)
    for ek, lab, pr, fw in required_flat:
        if evidence_type_satisfied(ek, present):
            met += 1
        else:
            if ek.lower() not in {m.lower() for m in missing}:
                missing.append(ek)
            gap_detail.append((fw, ek, lab, pr))

    completeness = 100.0 if total == 0 else round(100.0 * met / total, 1)
    ro = review_overdue(status=ctrl.status, next_review_at=ctrl.next_review_at, now=now)
    ready = (
        statuses_sufficient_for_readiness(ctrl.status) and not ro and (total == 0 or met == total)
    )
    return completeness, missing, ready, ro, gap_detail

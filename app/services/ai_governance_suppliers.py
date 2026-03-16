"""AI-Governance Supplier-Risk-Übersicht für Board-Drilldown (NIS2 Art. 21/24)."""

from __future__ import annotations

from app.repositories.ai_systems import AISystemRepository
from app.supplier_risk_models import (
    AISupplierRiskBySystemEntry,
    AISupplierRiskOverview,
    BySupplierRiskLevelEntry,
    SupplierRiskLevel,
)


def _criticality_to_supplier_risk_level(criticality: str) -> SupplierRiskLevel:
    if criticality in ("high", "very_high"):
        return SupplierRiskLevel.high
    if criticality == "medium":
        return SupplierRiskLevel.medium
    return SupplierRiskLevel.low


def _supplier_risk_score(has_register: bool, criticality: str) -> float:
    """0..1: höher = mehr Risiko (ohne Register) bzw. besser abgesichert (mit Register)."""
    if criticality in ("high", "very_high"):
        return 1.0 if not has_register else 0.0
    if criticality == "medium":
        return 0.5 if not has_register else 0.0
    return 0.25 if not has_register else 0.0


def compute_ai_supplier_risk_overview(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
) -> AISupplierRiskOverview:
    """Aggregierte Supplier-Risiko-Übersicht für GET .../suppliers/overview."""
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    total = len(ai_systems)
    with_register = sum(1 for s in ai_systems if s.has_supplier_risk_register)
    without_register = total - with_register
    critical = [s for s in ai_systems if s.criticality in ("high", "very_high")]
    critical_total = len(critical)
    critical_without_controls = sum(1 for s in critical if not s.has_supplier_risk_register)

    by_level: dict[SupplierRiskLevel, tuple[int, int]] = {
        SupplierRiskLevel.high: (0, 0),
        SupplierRiskLevel.medium: (0, 0),
        SupplierRiskLevel.low: (0, 0),
    }
    for s in ai_systems:
        level = _criticality_to_supplier_risk_level(s.criticality)
        with_r, without_r = by_level[level]
        if s.has_supplier_risk_register:
            by_level[level] = (with_r + 1, without_r)
        else:
            by_level[level] = (with_r, without_r + 1)

    by_risk_level = [
        BySupplierRiskLevelEntry(
            risk_level=level,
            systems_with_register=by_level[level][0],
            systems_without_register=by_level[level][1],
        )
        for level in (SupplierRiskLevel.high, SupplierRiskLevel.medium, SupplierRiskLevel.low)
    ]
    return AISupplierRiskOverview(
        tenant_id=tenant_id,
        total_systems_with_suppliers=with_register,
        systems_without_supplier_risk_register=without_register,
        critical_suppliers_total=critical_total,
        critical_suppliers_without_controls=critical_without_controls,
        by_risk_level=by_risk_level,
    )


def compute_ai_supplier_risk_by_system(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
) -> list[AISupplierRiskBySystemEntry]:
    """Pro-System-Liste für GET .../suppliers/by-system (höchstes Risiko zuerst)."""
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    entries = [
        AISupplierRiskBySystemEntry(
            ai_system_id=s.id,
            ai_system_name=s.name,
            has_supplier_risk_register=s.has_supplier_risk_register,
            supplier_risk_score=round(
                _supplier_risk_score(s.has_supplier_risk_register, s.criticality), 2
            ),
        )
        for s in ai_systems
    ]
    return sorted(entries, key=lambda e: (-e.supplier_risk_score, e.ai_system_name))

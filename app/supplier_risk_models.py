"""NIS2 Art. 21/24 Supply-Chain-Risiko – Board-Drilldown-Modelle."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class SupplierRiskLevel(StrEnum):
    """Risikostufe für Lieferanten-/KI-System-Kontext (NIS2 Supply Chain)."""

    high = "high"
    medium = "medium"
    low = "low"


class BySupplierRiskLevelEntry(BaseModel):
    """Anzahl KI-Systeme mit/ohne Supplier-Risikoregister pro Risikostufe."""

    risk_level: SupplierRiskLevel
    systems_with_register: int
    systems_without_register: int


class AISupplierRiskOverview(BaseModel):
    """Übersicht Supplier-Risiko für Board-Drilldown (NIS2 Art. 21/24, KRITIS-Bezug)."""

    tenant_id: str
    total_systems_with_suppliers: int
    systems_without_supplier_risk_register: int
    critical_suppliers_total: int
    critical_suppliers_without_controls: int
    by_risk_level: list[BySupplierRiskLevelEntry]


class AISupplierRiskBySystemEntry(BaseModel):
    """Pro KI-System: Supplier-Risikoregister und abgeleiteter Score."""

    ai_system_id: str
    ai_system_name: str
    has_supplier_risk_register: bool
    supplier_risk_score: float

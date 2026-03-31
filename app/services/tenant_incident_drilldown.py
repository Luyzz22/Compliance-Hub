"""Aggregierter Incident-Drilldown pro KI-System und dominanter Event-Quelle (Lieferant)."""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.incident_drilldown_models import (
    IncidentDrilldownCategoryCounts,
    TenantIncidentDrilldownItem,
    TenantIncidentDrilldownOut,
)
from app.oami_subtype_weights import incident_subtype_oami_category, incident_subtype_oami_weight
from app.repositories.ai_runtime_events import AiRuntimeEventRepository
from app.repositories.ai_systems import AISystemRepository

_SUPPLIER_LABEL_DE: dict[str, str] = {
    "sap_ai_core": "SAP AI Core",
    "sap_btp_event_mesh": "SAP BTP Event Mesh",
    "manual_import": "Manuell / Custom",
    "other_provider": "Sonstiger Anbieter",
}


def event_source_supplier_label_de(source: str) -> str:
    s = (source or "").strip().lower()
    if s in _SUPPLIER_LABEL_DE:
        return _SUPPLIER_LABEL_DE[s]
    if not s:
        return "Unbekannt"
    return s.replace("_", " ").title()


def _local_hint_de(
    *,
    sh: float,
    av: float,
    ot: float,
    total: int,
) -> str:
    if total <= 0:
        return ""
    if sh >= 0.45 and sh > av and sh > ot:
        return "Schwerpunkt: sicherheitsrelevante Laufzeit-Incidents (OAMI-Gewichtung)."
    if av >= 0.45 and av > sh and av > ot:
        return "Schwerpunkt: Verfügbarkeits-Incidents (Betriebsstabilität)."
    if total <= 3:
        return "Wenige klassifizierte Incidents; Einordnung mit Vorsicht nutzen."
    return "Ausgewogene Verteilung der Incident-Subtypen im Systemfenster."


def compute_tenant_incident_drilldown(
    session: Session,
    tenant_id: str,
    *,
    window_days: int = 90,
) -> TenantIncidentDrilldownOut:
    now = datetime.now(UTC)
    since = now - timedelta(days=window_days)
    until = now
    ev_repo = AiRuntimeEventRepository(session)
    sys_repo = AISystemRepository(session)
    system_ids = sorted(ev_repo.list_system_ids_with_events(tenant_id, since=since, until=until))
    items: list[TenantIncidentDrilldownItem] = []
    with_incidents = 0

    for sid in system_ids:
        inc_rows = [
            r
            for r in ev_repo.list_in_window(tenant_id, sid, since=since, until=until)
            if str(r.event_type).lower() == "incident"
        ]
        inc_total = len(inc_rows)
        if inc_total <= 0:
            continue
        with_incidents += 1
        safety_c = availability_c = other_c = 0
        burden = {"safety": 0.0, "availability": 0.0, "other": 0.0}
        for r in inc_rows:
            st_raw = (getattr(r, "event_subtype", None) or "").strip().lower()
            st_key = st_raw if st_raw else None
            cat = incident_subtype_oami_category(st_key)
            w = incident_subtype_oami_weight(st_key)
            burden[cat] += w
            if cat == "safety":
                safety_c += 1
            elif cat == "availability":
                availability_c += 1
            else:
                other_c += 1
        counts = IncidentDrilldownCategoryCounts(
            safety=safety_c,
            availability=availability_c,
            other=other_c,
        )

        total_b = sum(burden.values())
        if total_b <= 0:
            sh = av = ot = 1.0 / 3.0
        else:
            sh = burden["safety"] / total_b
            av = burden["availability"] / total_b
            ot = burden["other"] / total_b

        cnt = Counter((r.source or "").strip().lower() or "unknown" for r in inc_rows)
        src = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if cnt else ""
        label = event_source_supplier_label_de(src)
        system = sys_repo.get_by_id(tenant_id, sid)
        name = system.name if system else sid

        items.append(
            TenantIncidentDrilldownItem(
                ai_system_id=sid,
                ai_system_name=name,
                supplier_label_de=label,
                event_source=src or "unknown",
                incident_total_90d=inc_total,
                incident_count_by_category=counts,
                weighted_incident_share_safety=round(sh, 4),
                weighted_incident_share_availability=round(av, 4),
                weighted_incident_share_other=round(ot, 4),
                oami_local_hint_de=_local_hint_de(sh=sh, av=av, ot=ot, total=inc_total),
            ),
        )

    return TenantIncidentDrilldownOut(
        tenant_id=tenant_id,
        window_days=window_days,
        systems_with_runtime_events=len(system_ids),
        systems_with_incidents=with_incidents,
        items=sorted(items, key=lambda x: (-x.incident_total_90d, x.ai_system_id)),
    )


def tenant_incident_drilldown_to_csv(data: TenantIncidentDrilldownOut) -> str:
    """UTF-8 CSV für interne Auswertung (keine Roh-Event-IDs)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "tenant_id",
            "window_days",
            "ai_system_id",
            "ai_system_name",
            "event_source",
            "supplier_label_de",
            "incident_total_90d",
            "count_safety",
            "count_availability",
            "count_other",
            "weighted_share_safety",
            "weighted_share_availability",
            "weighted_share_other",
            "oami_local_hint_de",
        ],
    )
    for it in data.items:
        c = it.incident_count_by_category
        w.writerow(
            [
                data.tenant_id,
                data.window_days,
                it.ai_system_id,
                it.ai_system_name,
                it.event_source,
                it.supplier_label_de,
                it.incident_total_90d,
                c.safety,
                c.availability,
                c.other,
                it.weighted_incident_share_safety,
                it.weighted_incident_share_availability,
                it.weighted_incident_share_other,
                it.oami_local_hint_de,
            ],
        )
    return buf.getvalue()

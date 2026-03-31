"""OAMI Incident-Subtype-Profil für Board-Report (Logik; Modelle: ``ai_governance_models``)."""

from __future__ import annotations

import logging

from app.ai_governance_models import (
    OAMI_SUBTYPE_CHART_NOTE_DE,
    OamiIncidentCategoryCounts,
    OamiIncidentSubtypeProfile,
)
from app.governance_maturity_contract import INDEX_LEVEL_DE
from app.oami_subtype_weights import incident_subtype_oami_category, incident_subtype_oami_weight
from app.operational_monitoring_models import TenantOperationalMonitoringIndexOut

logger = logging.getLogger(__name__)


def _trim_board_sentence(text: str, *, max_len: int = 240) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def _narrative_for_profile(
    *,
    level_api: str,
    index: int,
    safety_driven: bool,
    availability_driven: bool,
    incidents_positive: bool,
) -> str:
    level_de = INDEX_LEVEL_DE.get(level_api, level_api)
    if safety_driven:
        base = (
            f"Der OAMI liegt auf Stufe {level_de} (Index {index}/100); maßgeblich sind "
            "wenige, aber sicherheitsrelevante Laufzeit-Incidents – das Board sollte "
            "Post-Market- und Eskalationspfade für Sicherheitssignale priorisieren, "
            "nicht nur Verfügbarkeit."
        )
    elif availability_driven:
        base = (
            f"Der OAMI steht auf Stufe {level_de} (Index {index}/100); das Laufzeitbild wird "
            "überwiegend von Verfügbarkeits-Incidents getragen – Fokus auf Betriebsstabilität, "
            "Service-Recovery und klare Abgrenzung zu sicherheitsklassifizierten Vorfällen."
        )
    elif str(level_api) == "low" and incidents_positive:
        base = (
            f"Der OAMI ist auf Stufe {level_de} (Index {index}/100); sichtbare Incidents sind "
            "selten und überwiegend unspezifisch – dennoch sollten Datenaktualität und "
            "kontinuierliche Überwachung verbessert werden, damit das Bild belastbar bleibt."
        )
    else:
        base = (
            f"Der OAMI steht auf Stufe {level_de} (Index {index}/100); die gewichtete "
            "Incident-Last verteilt sich ausgewogen zwischen Sicherheits-, Verfügbarkeits- "
            "und sonstigen Signalen ohne einseitige Dominanz einer Subtyp-Kategorie."
        )
    return _trim_board_sentence(base)


def build_oami_incident_subtype_profile_for_board(
    tenant_oami: TenantOperationalMonitoringIndexOut,
) -> OamiIncidentSubtypeProfile | None:
    """
    Liefert Profil nur wenn Mandant Laufzeitdaten hat und Subtype-Kontext sinnvoll ist.
    """
    if not tenant_oami.has_any_runtime_data:
        return None

    by_sub = dict(tenant_oami.runtime_incident_by_subtype)
    inc_total = sum(int(v) for v in by_sub.values() if int(v) > 0)
    hint = (tenant_oami.oami_operational_hint_de or "").strip()

    if inc_total <= 0 and not hint:
        return None

    burden = {"safety": 0.0, "availability": 0.0, "other": 0.0}
    counts = {"safety": 0, "availability": 0, "other": 0}

    if inc_total > 0:
        for raw_k, raw_v in by_sub.items():
            try:
                n = int(raw_v)
            except (TypeError, ValueError):
                continue
            if n <= 0:
                continue
            ks = str(raw_k).strip().lower()
            cat = incident_subtype_oami_category(ks)
            w = incident_subtype_oami_weight(ks)
            burden[cat] += float(n) * w
            counts[cat] += n
    else:
        for k in burden:
            burden[k] = 1.0 / 3.0

    total_burden = sum(burden.values())
    if total_burden <= 0:
        logger.debug("oami_subtype_profile_zero_burden tenant=%s", tenant_oami.tenant_id)
        return None

    sh = burden["safety"] / total_burden
    av = burden["availability"] / total_burden
    ot = burden["other"] / total_burden

    safety_driven = sh >= 0.45 and sh > av and sh > ot
    availability_driven = av >= 0.45 and av > sh and av > ot

    narrative = _narrative_for_profile(
        level_api=str(tenant_oami.level),
        index=int(tenant_oami.operational_monitoring_index),
        safety_driven=safety_driven,
        availability_driven=availability_driven,
        incidents_positive=inc_total > 0,
    )

    return OamiIncidentSubtypeProfile(
        incident_weighted_share_safety=sh,
        incident_weighted_share_availability=av,
        incident_weighted_share_other=ot,
        incident_count_by_category=OamiIncidentCategoryCounts(
            safety=counts["safety"],
            availability=counts["availability"],
            other=counts["other"],
        ),
        oami_subtype_narrative_de=narrative,
        chart_note_de=OAMI_SUBTYPE_CHART_NOTE_DE,
    )

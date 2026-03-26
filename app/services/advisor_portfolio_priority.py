"""
Regelbasierte Priorisierung für das Berater-Portfolio (ohne undurchsichtige Scores).

Nutzt Readiness-Level (bzw. Näherung über EU-AI-Act-Readiness), GAI- und OAMI-Level
sowie die Zuordnung zu den Golden-Szenarien A–D, sofern die Kennzahlen passen.
"""

from __future__ import annotations

from typing import Literal

from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.advisor_portfolio_models import (
    GovernanceActivityPortfolioSummary,
    OperationalMonitoringPortfolioSummary,
)
from app.readiness_score_models import ReadinessScoreSummary

AdvisorPriorityBucket = Literal["high", "medium", "low"]
MaturityScenarioHint = Literal["a", "b", "c", "d"]

_PRIORITY_SORT = {"high": 0, "medium": 1, "low": 2}


def _ord_readiness_level(level: str) -> int | None:
    m = {"basic": 0, "managed": 1, "embedded": 2}
    return m.get(str(level).strip().lower())


def _ord_index_level(level: str | None) -> int | None:
    if level is None:
        return None
    m = {"low": 0, "medium": 1, "high": 2}
    return m.get(str(level).strip().lower())


def effective_readiness_level(
    readiness_summary: ReadinessScoreSummary | None,
    eu_ai_act_readiness: float,
) -> str:
    """API-Level oder grobe Näherung aus EU-AI-Act-Readiness (0–1), wenn Score fehlt."""
    if readiness_summary is not None:
        return str(readiness_summary.level).strip().lower()
    if eu_ai_act_readiness < 0.5:
        return "basic"
    if eu_ai_act_readiness < 0.72:
        return "managed"
    return "embedded"


def infer_maturity_scenario_hint(
    readiness_level: str,
    gai_level: str | None,
    oami_level: str | None,
) -> MaturityScenarioHint | None:
    """
    Ordnet die Kennzahl-Kombination den Golden-Szenarien A–D zu (exakte Muster).

    Fehlendes OAMI wird für die Mustererkennung wie „low“ behandelt (vorsichtig).
    """
    r = _ord_readiness_level(readiness_level)
    g = _ord_index_level(gai_level)
    o_raw = oami_level
    o = _ord_index_level(o_raw) if o_raw is not None else 0

    if r is None or g is None:
        return None

    if r == 2 and g == 2 and o == 2:
        return "d"
    if r == 0 and g == 0 and o <= 0:
        return "a"
    if r == 1 and g == 2 and o <= 0:
        return "b"
    if r == 2 and g == 1 and o == 1:
        return "c"
    return None


def compute_advisor_priority_bucket(
    readiness_level: str,
    gai_level: str | None,
    oami_level: str | None,
    scenario: MaturityScenarioHint | None,
) -> AdvisorPriorityBucket:
    """
    Hohe Priorität: Szenario A/B oder (Readiness basic/managed und niedriges/fehlendes OAMI).

    Niedrige Priorität: Szenario D oder eingebettet + hohes GAI + hohes OAMI.

    Sonst mittlere Priorität.
    """
    r = _ord_readiness_level(readiness_level)
    g = _ord_index_level(gai_level)
    o = _ord_index_level(oami_level) if oami_level is not None else None
    o_conservative = 0 if o is None else o

    if scenario == "d" or (r == 2 and g == 2 and o == 2):
        return "low"
    if scenario in ("a", "b"):
        return "high"
    if r is not None and r <= 1 and o_conservative <= 0:
        return "high"
    return "medium"


def derive_primary_focus_tag_de(
    brief: AdvisorGovernanceMaturityBrief | None,
    *,
    readiness_level: str,
    gai_level: str | None,
    oami_level: str | None,
) -> str:
    """
    Kompakter Schwerpunkt für die Tabellenzeile (Monitoring / Readiness / Nutzung / Governance).

    Primär aus dem ersten Eintrag von recommended_focus_areas; sonst heuristisch aus Levels.
    """
    if brief is not None and brief.recommended_focus_areas:
        return _primary_focus_from_text(brief.recommended_focus_areas[0])
    o_ord = _ord_index_level(oami_level) if oami_level is not None else None
    if o_ord is None or o_ord <= 0:
        return "Monitoring"
    r_ord = _ord_readiness_level(readiness_level)
    if r_ord is not None and r_ord <= 0:
        return "Readiness"
    g_ord = _ord_index_level(gai_level)
    if g_ord is not None and g_ord <= 0:
        return "Nutzung"
    return "Governance"


def _primary_focus_from_text(line: str) -> str:
    u = line.upper()
    if "OAMI" in u or "MONITORING" in u or "LAUFZEIT" in u:
        return "Monitoring"
    if "READINESS" in u or "REGISTER" in u or "NACHWEIS" in u:
        return "Readiness"
    if "GAI" in u or "NUTZUNG" in u or "STEUERUNG" in u or "PROZESS" in u:
        return "Nutzung"
    return "Governance"


def advisor_priority_explanation_de(
    bucket: AdvisorPriorityBucket,
    scenario: MaturityScenarioHint | None,
    primary_focus: str,
) -> str:
    """Kurzer Tooltip-Text für Berater (deterministisch)."""
    scen = ""
    if scenario == "a":
        scen = " Zuordnung zu Reife-Szenario A (Grundlagen)."
    elif scenario == "b":
        scen = " Zuordnung zu Reife-Szenario B (Monitoring nachziehen)."
    elif scenario == "c":
        scen = " Zuordnung zu Reife-Szenario C (Nutzung ausbauen)."
    elif scenario == "d":
        scen = " Zuordnung zu Reife-Szenario D (Feintuning)."
    base = {
        "high": (
            "Hohe Beraterpriorität: niedrige Readiness und/oder schwaches operatives Monitoring "
            "oder klares Aufbau-/Monitoring-Szenario."
        ),
        "medium": (
            "Mittlere Priorität: einzelne Säulen (Readiness, GAI oder OAMI) noch ausbaufähig; "
            "Fortschritt beobachten."
        ),
        "low": (
            "Geringere Dringlichkeit: Reife über die Säulen hinweg insgesamt solide; Fokus auf "
            "Feintuning und Skalierung."
        ),
    }[bucket]
    return f"{base}{scen} Hauptschwerpunkt: {primary_focus}."[:500]


def advisor_portfolio_priority_sort_key(bucket: AdvisorPriorityBucket) -> int:
    """Sortierung: niedrigere Zahl = zuerst anzeigen (hohe Priorität oben)."""
    return _PRIORITY_SORT[bucket]

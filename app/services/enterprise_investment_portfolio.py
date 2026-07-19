from __future__ import annotations

from datetime import UTC, datetime

from app.enterprise_connector_candidate_models import (
    ConnectorCandidatePriority,
    EnterpriseConnectorCandidateRow,
    EnterpriseConnectorCandidatesResponse,
)
from app.enterprise_integration_blueprint_models import SourceSystemType
from app.enterprise_investment_portfolio_models import (
    EnterpriseInvestmentInitiative,
    EnterpriseInvestmentPortfolioResponse,
    InvestmentDecision,
    InvestmentEnvelopeBand,
    InvestmentPortfolioSummary,
    InvestmentPortfolioWeights,
    TimeToValueBand,
)

BASELINE_WEIGHTS = InvestmentPortfolioWeights()

_INITIATIVE_NAMES: dict[SourceSystemType, str] = {
    SourceSystemType.sap_s4hana: "SAP S/4HANA Evidence Integration",
    SourceSystemType.sap_btp: "SAP BTP Governance Integration",
    SourceSystemType.datev: "DATEV Evidence & Export Integration",
    SourceSystemType.ms_dynamics: "Microsoft Dynamics Governance Integration",
    SourceSystemType.generic_api: "Generic API Evidence Integration",
}

ASSUMPTIONS_DE = [
    "Die Bewertung verwendet keine Umsatz-, Vertrags-, Personal- oder Budgetdaten.",
    "Investment-Bänder sind relative Größenklassen und keine Euro-Schätzung.",
    "Ein Szenario ersetzt weder Business Case noch Finance-, Legal- oder Architekturfreigabe.",
    (
        "Scores werden ausschließlich aus strukturierten Readiness-, Blocker- "
        "und Compliance-Signalen abgeleitet."
    ),
]


def build_enterprise_investment_portfolio(
    *,
    tenant_id: str,
    candidates: EnterpriseConnectorCandidatesResponse,
    include_markdown: bool,
    generated_at_utc: datetime | None = None,
) -> EnterpriseInvestmentPortfolioResponse:
    generated_at = generated_at_utc or datetime.now(UTC)
    initiatives = [_build_initiative(tenant_id, row) for row in candidates.candidate_rows]
    initiatives.sort(
        key=lambda item: (
            -item.portfolio_score,
            item.blocker_score,
            item.initiative_id,
        )
    )
    initiatives = [
        item.model_copy(update={"baseline_rank": index})
        for index, item in enumerate(initiatives, 1)
    ]

    summary = InvestmentPortfolioSummary(
        total_initiatives=len(initiatives),
        fund_now_count=sum(
            i.recommended_decision == InvestmentDecision.fund_now for i in initiatives
        ),
        sequence_count=sum(
            i.recommended_decision == InvestmentDecision.sequence for i in initiatives
        ),
        validate_count=sum(
            i.recommended_decision == InvestmentDecision.validate for i in initiatives
        ),
        hold_count=sum(i.recommended_decision == InvestmentDecision.hold for i in initiatives),
        large_envelope_count=sum(
            i.investment_envelope_band == InvestmentEnvelopeBand.large for i in initiatives
        ),
        missing_finance_inputs=sum(i.requires_finance_input for i in initiatives),
        top_recommendation_de=(
            f"{initiatives[0].initiative_name_de}: "
            f"{initiatives[0].recommended_decision.value} ({initiatives[0].portfolio_score}/100)"
            if initiatives
            else None
        ),
    )
    markdown = _build_markdown(tenant_id, initiatives, summary) if include_markdown else None
    return EnterpriseInvestmentPortfolioResponse(
        tenant_id=tenant_id,
        generated_at_utc=generated_at,
        baseline_weights=BASELINE_WEIGHTS,
        summary=summary,
        initiatives=initiatives,
        assumptions_de=ASSUMPTIONS_DE,
        markdown_de=markdown,
    )


def _build_initiative(
    tenant_id: str,
    row: EnterpriseConnectorCandidateRow,
) -> EnterpriseInvestmentInitiative:
    execution_confidence = _clamp(
        round(row.readiness_score * 0.6 + (100 - row.blocker_score) * 0.4)
    )
    capital_efficiency = _clamp(100 - row.estimated_implementation_complexity)
    portfolio_score = _clamp(
        round(
            (
                row.strategic_value_score * BASELINE_WEIGHTS.strategic_value_weight
                + row.compliance_impact_score * BASELINE_WEIGHTS.risk_reduction_weight
                + execution_confidence * BASELINE_WEIGHTS.execution_confidence_weight
                + capital_efficiency * BASELINE_WEIGHTS.capital_efficiency_weight
            )
            / 100
        )
    )
    envelope = _envelope_band(row.estimated_implementation_complexity)
    decision = _decision(
        candidate_priority=row.recommended_priority,
        portfolio_score=portfolio_score,
        execution_confidence=execution_confidence,
        blocker_score=row.blocker_score,
        envelope=envelope,
    )
    preconditions = _funding_preconditions(
        readiness_score=row.readiness_score,
        blocker_score=row.blocker_score,
        envelope=envelope,
    )
    return EnterpriseInvestmentInitiative(
        initiative_id=f"connector:{row.connector_type.value}",
        tenant_id=tenant_id,
        connector_type=row.connector_type,
        initiative_name_de=_INITIATIVE_NAMES[row.connector_type],
        baseline_rank=1,
        recommended_decision=decision,
        investment_envelope_band=envelope,
        time_to_value_band=_time_to_value_band(envelope, row.readiness_score),
        strategic_value_score=row.strategic_value_score,
        risk_reduction_score=row.compliance_impact_score,
        execution_confidence_score=execution_confidence,
        capital_efficiency_score=capital_efficiency,
        blocker_score=row.blocker_score,
        portfolio_score=portfolio_score,
        decision_rationale_de=(
            f"{_INITIATIVE_NAMES[row.connector_type]} erreicht {portfolio_score}/100. "
            f"Strategischer Wert {row.strategic_value_score}, Risikowirkung "
            f"{row.compliance_impact_score}, Ausführungssicherheit {execution_confidence} "
            f"und Kapitaleffizienz {capital_efficiency}."
        ),
        funding_preconditions_de=preconditions,
        source_refs=[
            f"connector_candidate:{row.connector_type.value}",
            "enterprise_onboarding_readiness",
            "enterprise_control_center",
        ],
    )


def _decision(
    *,
    candidate_priority: ConnectorCandidatePriority,
    portfolio_score: int,
    execution_confidence: int,
    blocker_score: int,
    envelope: InvestmentEnvelopeBand,
) -> InvestmentDecision:
    if candidate_priority == ConnectorCandidatePriority.not_now or blocker_score >= 70:
        return InvestmentDecision.hold
    if execution_confidence < 55:
        return InvestmentDecision.validate
    if portfolio_score >= 72 and blocker_score <= 35 and envelope != InvestmentEnvelopeBand.large:
        return InvestmentDecision.fund_now
    if portfolio_score >= 60:
        return InvestmentDecision.sequence
    return InvestmentDecision.validate


def _envelope_band(complexity: int) -> InvestmentEnvelopeBand:
    if complexity >= 70:
        return InvestmentEnvelopeBand.large
    if complexity >= 45:
        return InvestmentEnvelopeBand.medium
    return InvestmentEnvelopeBand.small


def _time_to_value_band(
    envelope: InvestmentEnvelopeBand,
    readiness_score: int,
) -> TimeToValueBand:
    if envelope == InvestmentEnvelopeBand.small and readiness_score >= 60:
        return TimeToValueBand.near_term
    if envelope == InvestmentEnvelopeBand.large:
        return TimeToValueBand.long_term
    return TimeToValueBand.mid_term


def _funding_preconditions(
    *,
    readiness_score: int,
    blocker_score: int,
    envelope: InvestmentEnvelopeBand,
) -> list[str]:
    conditions = [
        "Finance Owner, Euro-Korridor und Capex-/Opex-Behandlung bestätigen.",
        "Messbare Value-Hypothese und Abbruchkriterium dokumentieren.",
    ]
    if readiness_score < 65:
        conditions.append("Readiness auf mindestens 65/100 evidenzbasiert bestätigen.")
    if blocker_score > 35:
        conditions.append("Blocker-Belastung vor Finanzierung auf höchstens 35/100 reduzieren.")
    if envelope == InvestmentEnvelopeBand.large:
        conditions.append(
            "Architektur-, Delivery- und Beschaffungsfreigabe vor Commit abschließen."
        )
    return conditions


def _build_markdown(
    tenant_id: str,
    initiatives: list[EnterpriseInvestmentInitiative],
    summary: InvestmentPortfolioSummary,
) -> str:
    lines = [
        "# CFO Investment Portfolio (Wave 59)",
        "",
        f"- Mandant: {tenant_id}",
        f"- Initiativen: {summary.total_initiatives}",
        f"- Jetzt finanzieren: {summary.fund_now_count}",
        f"- Sequenzieren: {summary.sequence_count}",
        f"- Validieren: {summary.validate_count}",
        f"- Halten: {summary.hold_count}",
        "- Hinweis: Relative Entscheidungshilfe, keine Budgetfreigabe oder Finanzprognose.",
        "",
        "## Priorisierte Initiativen",
    ]
    for item in initiatives:
        lines.append(
            f"{item.baseline_rank}. {item.initiative_name_de}: "
            f"{item.recommended_decision.value} ({item.portfolio_score}/100, "
            f"Envelope {item.investment_envelope_band.value})."
        )
    lines.extend(["", "## Verbindliche Annahmen"])
    lines.extend(f"- {assumption}" for assumption in ASSUMPTIONS_DE)
    return "\n".join(lines).strip() + "\n"


def _clamp(value: int) -> int:
    return max(0, min(100, value))

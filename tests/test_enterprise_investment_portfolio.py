from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.enterprise_connector_candidate_models import (
    ConnectorCandidatePriority,
    ConnectorScoringWeights,
    EnterpriseConnectorCandidateRow,
    EnterpriseConnectorCandidatesResponse,
    ImplementationComplexityBand,
)
from app.enterprise_integration_blueprint_models import SourceSystemType
from app.main import app
from app.services.enterprise_investment_portfolio import (
    build_enterprise_investment_portfolio,
)

client = TestClient(app)


def _candidate(
    connector_type: SourceSystemType,
    *,
    readiness: int,
    blocker: int,
    strategic: int,
    compliance: int,
    complexity: int,
    priority: ConnectorCandidatePriority,
) -> EnterpriseConnectorCandidateRow:
    return EnterpriseConnectorCandidateRow(
        tenant_id="cfo-test",
        connector_type=connector_type,
        readiness_score=readiness,
        blocker_score=blocker,
        strategic_value_score=strategic,
        compliance_impact_score=compliance,
        estimated_implementation_complexity=complexity,
        complexity_band=(
            ImplementationComplexityBand.high
            if complexity >= 70
            else ImplementationComplexityBand.medium
            if complexity >= 45
            else ImplementationComplexityBand.low
        ),
        recommended_priority=priority,
        rationale_summary_de="Testkandidat",
        rationale_factors_de=[],
        score_total=70,
    )


def test_portfolio_is_deterministic_and_never_claims_financial_estimates() -> None:
    generated_at = datetime(2026, 7, 19, 12, tzinfo=UTC)
    rows = [
        _candidate(
            SourceSystemType.datev,
            readiness=82,
            blocker=18,
            strategic=82,
            compliance=88,
            complexity=38,
            priority=ConnectorCandidatePriority.high,
        ),
        _candidate(
            SourceSystemType.sap_s4hana,
            readiness=58,
            blocker=42,
            strategic=94,
            compliance=76,
            complexity=82,
            priority=ConnectorCandidatePriority.medium,
        ),
    ]
    candidates = EnterpriseConnectorCandidatesResponse(
        tenant_id="cfo-test",
        generated_at_utc=generated_at,
        scoring_weights=ConnectorScoringWeights(),
        candidate_rows=rows,
        top_priorities=rows,
        grouped_priorities_by_connector_type={},
    )

    result = build_enterprise_investment_portfolio(
        tenant_id="cfo-test",
        candidates=candidates,
        include_markdown=True,
        generated_at_utc=generated_at,
    )

    assert result.generated_at_utc == generated_at
    assert sum(result.baseline_weights.model_dump().values()) == 100
    assert result.initiatives[0].connector_type == SourceSystemType.datev
    assert result.initiatives[0].recommended_decision == "fund_now"
    assert result.initiatives[1].investment_envelope_band == "large"
    assert all(item.requires_finance_input for item in result.initiatives)
    assert all(not item.is_financial_estimate for item in result.initiatives)
    assert "keine Budgetfreigabe" in (result.markdown_de or "")


def test_investment_portfolio_api_is_tenant_scoped_and_explainable() -> None:
    tenant = "investment-portfolio-tenant"
    response = client.get(
        "/api/internal/enterprise/investment-portfolio?include_markdown=true",
        headers={
            "x-api-key": "test-key",
            "x-tenant-id": tenant,
            "x-opa-user-role": "tenant_admin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == tenant
    assert body["initiatives"]
    assert body["summary"]["missing_finance_inputs"] == len(body["initiatives"])
    assert body["markdown_de"]
    assert all(item["tenant_id"] == tenant for item in body["initiatives"])


def test_investment_portfolio_requires_executive_dashboard_permission() -> None:
    response = client.get(
        "/api/internal/enterprise/investment-portfolio",
        headers={
            "x-api-key": "test-key",
            "x-tenant-id": "investment-portfolio-viewer",
            "x-opa-user-role": "viewer",
        },
    )

    assert response.status_code == 403

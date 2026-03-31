"""Neues Mandanten-Onboarding: Stammdaten, Pilot-Feature-Defaults, initialer API-Key."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.provisioning_models import (
    InitialProvisionedApiKey,
    ProvisionTenantRequest,
    ProvisionTenantResponse,
)
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.tenant_api_keys import TenantApiKeyRepository
from app.repositories.tenant_feature_overrides import TenantFeatureOverrideRepository
from app.repositories.tenant_registry import TenantRegistryRepository

PILOT_TENANT_FEATURE_DEFAULTS: dict[str, bool] = {
    FeatureFlag.advisor_workspace.value: False,
    FeatureFlag.advisor_client_snapshot.value: True,
    FeatureFlag.readiness_score.value: True,
    FeatureFlag.demo_seeding.value: False,
    FeatureFlag.evidence_uploads.value: True,
    FeatureFlag.guided_setup.value: True,
    FeatureFlag.pilot_runbook.value: True,
    FeatureFlag.ai_governance_playbook.value: True,
    FeatureFlag.cross_regulation_dashboard.value: True,
    FeatureFlag.cross_regulation_llm_assist.value: True,
    FeatureFlag.ai_compliance_board_report.value: True,
    FeatureFlag.ai_kpi_kri.value: True,
    FeatureFlag.ai_governance_setup_wizard.value: True,
    FeatureFlag.api_keys_ui.value: True,
    FeatureFlag.llm_enabled.value: False,
    FeatureFlag.llm_legal_reasoning.value: False,
    FeatureFlag.llm_report_assistant.value: False,
    FeatureFlag.llm_classification_tagging.value: False,
    FeatureFlag.llm_chat_assistant.value: False,
    FeatureFlag.llm_kpi_suggestions.value: False,
    FeatureFlag.llm_explain.value: False,
    FeatureFlag.llm_action_drafts.value: False,
}

_INITIAL_KEY_NAME = "Initial Pilot Key"


def _new_tenant_id() -> str:
    return f"pilot-{uuid.uuid4().hex[:16]}"


def provision_tenant(session: Session, body: ProvisionTenantRequest) -> ProvisionTenantResponse:
    """
    Legt tenants-Zeile, Feature-Overrides, ersten API-Key und optional advisor_tenants an.
    Kein Demo-Seed (Endpunkt orchestriert seed bei Bedarf).
    """
    tenant_id = _new_tenant_id()
    reg = TenantRegistryRepository(session)
    flags_repo = TenantFeatureOverrideRepository(session)
    keys_repo = TenantApiKeyRepository(session)

    ks: str | None = None
    if body.kritis_sector is not None and str(body.kritis_sector).strip():
        ks = str(body.kritis_sector).strip()[:64]
    reg.create(
        tenant_id=tenant_id,
        display_name=body.tenant_name.strip(),
        industry=body.industry.strip(),
        country=body.country.strip() or "DE",
        nis2_scope=body.nis2_scope.strip() or "in_scope",
        ai_act_scope=body.ai_act_scope.strip() or "in_scope",
        kritis_sector=ks,
    )

    flags_repo.set_many(tenant_id, dict(PILOT_TENANT_FEATURE_DEFAULTS))

    key_row, plain = keys_repo.create_key(tenant_id=tenant_id, name=_INITIAL_KEY_NAME)

    advisor_linked = False
    if body.advisor_id and str(body.advisor_id).strip():
        adv = AdvisorTenantRepository(session)
        adv.upsert_link(
            advisor_id=str(body.advisor_id).strip(),
            tenant_id=tenant_id,
            tenant_display_name=body.tenant_name.strip(),
            industry=body.industry.strip(),
            country=body.country.strip() or "DE",
        )
        advisor_linked = True

    effective = {f.value: is_feature_enabled(f, tenant_id, session=session) for f in FeatureFlag}

    return ProvisionTenantResponse(
        tenant_id=tenant_id,
        display_name=body.tenant_name.strip(),
        industry=body.industry.strip(),
        country=body.country.strip() or "DE",
        feature_flags=effective,
        initial_api_key=InitialProvisionedApiKey(
            key_id=key_row.id,
            name=key_row.name,
            key_last4=key_row.key_last4,
            plain_key=plain,
        ),
        advisor_linked=advisor_linked,
        demo_seeded=False,
    )

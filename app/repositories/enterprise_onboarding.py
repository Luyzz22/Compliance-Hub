from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.enterprise_onboarding_models import (
    EnterpriseOnboardingReadinessResponse,
    EnterpriseOnboardingReadinessUpsert,
    OnboardingBlocker,
)
from app.models_db import EnterpriseOnboardingReadinessDB
from app.services.enterprise_identity_mapping import validate_role_mapping_rules


class EnterpriseOnboardingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, tenant_id: str) -> EnterpriseOnboardingReadinessResponse | None:
        row = self._session.get(EnterpriseOnboardingReadinessDB, tenant_id)
        if row is None:
            return None
        payload = EnterpriseOnboardingReadinessUpsert.model_validate(row.payload)
        blockers = self._compute_blockers(payload)
        return EnterpriseOnboardingReadinessResponse(
            tenant_id=tenant_id,
            updated_at_utc=row.updated_at_utc,
            updated_by=row.updated_by,
            enterprise_name=payload.enterprise_name,
            tenant_structure=payload.tenant_structure,
            advisor_visibility_enabled=payload.advisor_visibility_enabled,
            sso_readiness=payload.sso_readiness,
            integration_readiness=payload.integration_readiness,
            rollout_notes=payload.rollout_notes,
            blockers=blockers,
        )

    def upsert(
        self,
        tenant_id: str,
        body: EnterpriseOnboardingReadinessUpsert,
        actor: str,
    ) -> EnterpriseOnboardingReadinessResponse:
        now = datetime.now(UTC)
        row = self._session.get(EnterpriseOnboardingReadinessDB, tenant_id)
        if row is None:
            row = EnterpriseOnboardingReadinessDB(
                tenant_id=tenant_id,
                payload=body.model_dump(mode="json"),
                updated_at_utc=now,
                updated_by=actor,
            )
            self._session.add(row)
        else:
            row.payload = body.model_dump(mode="json")
            row.updated_at_utc = now
            row.updated_by = actor
        self._session.commit()
        self._session.refresh(row)
        return self.get(tenant_id)  # type: ignore[return-value]

    @staticmethod
    def _compute_blockers(body: EnterpriseOnboardingReadinessUpsert) -> list[OnboardingBlocker]:
        blockers: list[OnboardingBlocker] = []
        if body.sso_readiness.onboarding_status.value in {"not_started", "planned"}:
            blockers.append(
                OnboardingBlocker(
                    key="sso_not_validated",
                    title_de="SSO-Readiness ist noch nicht validiert.",
                    severity="warning",
                )
            )
        mapping_errors = validate_role_mapping_rules(body.sso_readiness.role_mapping_rules)
        if mapping_errors:
            blockers.append(
                OnboardingBlocker(
                    key="role_mapping_alignment",
                    title_de="Role-Mapping-Regeln müssen auf Least-Privilege geprüft werden.",
                    severity="critical",
                )
            )
        for item in body.integration_readiness:
            if item.blocker:
                blockers.append(
                    OnboardingBlocker(
                        key=f"integration_{item.target_type.value}",
                        title_de=f"Integration {item.target_type.value}: {item.blocker}",
                        severity="warning",
                    )
                )
        return blockers

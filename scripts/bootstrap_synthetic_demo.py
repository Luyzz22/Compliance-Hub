#!/usr/bin/env python3
"""Create the governed schema and one read-only synthetic demonstration workspace.

This command is intentionally separate from application startup. It is idempotent for the
fixed tenant and operator identity and never prints the operator password or verification
token. It is not a customer-production provisioning path.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db import SessionLocal, engine  # noqa: E402
from app.db_migrations import run_all_db_migrations  # noqa: E402
from app.feature_flags import FeatureFlag  # noqa: E402
from app.models_db import Base  # noqa: E402
from app.rbac.roles import EnterpriseRole  # noqa: E402
from app.repositories.ai_governance_actions import AIGovernanceActionRepository  # noqa: E402
from app.repositories.ai_systems import AISystemRepository  # noqa: E402
from app.repositories.classifications import ClassificationRepository  # noqa: E402
from app.repositories.evidence_files import EvidenceFileRepository  # noqa: E402
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository  # noqa: E402
from app.repositories.policies import PolicyRepository  # noqa: E402
from app.repositories.tenant_feature_overrides import (  # noqa: E402
    TenantFeatureOverrideRepository,
)
from app.repositories.tenant_registry import TenantRegistryRepository  # noqa: E402
from app.repositories.users import UserRepository  # noqa: E402
from app.secret_files import read_secret  # noqa: E402
from app.services.ai_kpi_seed import ensure_ai_kpi_definitions_seeded  # noqa: E402
from app.services.cross_regulation_seed import ensure_cross_regulation_catalog_seeded  # noqa: E402
from app.services.demo_governance_maturity_seed import (  # noqa: E402
    seed_demo_governance_maturity_layer,
)
from app.services.demo_tenant_seeder import seed_demo_tenant  # noqa: E402
from app.services.identity_service import IdentityService  # noqa: E402
from app.services.tenant_provisioning import PILOT_TENANT_FEATURE_DEFAULTS  # noqa: E402

DEFAULT_TENANT_ID = "demo-mittelstand-ag"
DEFAULT_OPERATOR_EMAIL = "demo-operator@complywithai.de"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _require_synthetic_contract() -> None:
    required = {
        "COMPLIANCEHUB_FEATURE_DEMO_MODE": "true",
        "COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS": "true",
        "COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED": "true",
    }
    missing = [name for name in required if not _truthy(os.getenv(name))]
    if missing:
        raise RuntimeError(
            "Synthetic demo bootstrap requires explicit safety flags: " + ", ".join(missing)
        )
    if os.getenv("COMPLIANCEHUB_ENV", "").strip().lower() in {"prod", "production"}:
        raise RuntimeError("Synthetic demo bootstrap must run before production runtime startup")


def _feature_flags() -> dict[str, bool]:
    flags = dict(PILOT_TENANT_FEATURE_DEFAULTS)
    flags[FeatureFlag.demo_seeding.value] = True
    flags[FeatureFlag.llm_enabled.value] = True
    flags[FeatureFlag.llm_chat_assistant.value] = True
    return flags


def _ensure_tenant_and_seed(session, tenant_id: str) -> None:
    registry = TenantRegistryRepository(session)
    tenant = registry.get_by_id(tenant_id)
    if tenant is None:
        registry.create(
            tenant_id=tenant_id,
            display_name="Mittelstand AG (synthetische Demo)",
            industry="Manufacturing",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
    elif not tenant.is_demo or tenant.demo_playground:
        raise RuntimeError("Existing tenant does not satisfy the read-only demo contract")

    TenantFeatureOverrideRepository(session).set_many(tenant_id, _feature_flags())
    systems = AISystemRepository(session)
    if not systems.list_for_tenant(tenant_id):
        seed_demo_tenant(
            session,
            "industrial_sme",
            tenant_id,
            advisor_id=None,
            ai_repo=systems,
            cls_repo=ClassificationRepository(session),
            nis2_repo=Nis2KritisKpiRepository(session),
            policy_repo=PolicyRepository(session),
            action_repo=AIGovernanceActionRepository(session),
            evidence_repo=EvidenceFileRepository(session),
        )
    seed_demo_governance_maturity_layer(session, tenant_id)


def _ensure_operator(session, *, tenant_id: str, email: str, password: str) -> None:
    repository = UserRepository(session)
    identity = IdentityService(repository)
    user = repository.get_by_email(email)
    if user is None:
        registration = identity.register(
            email=email,
            password=password,
            display_name="Compliance Hub Demo",
            company="Synthetische Demo",
            language="de",
            timezone_str="Europe/Berlin",
        )
        if "error" in registration:
            raise RuntimeError(f"Unable to create synthetic demo operator: {registration['error']}")
        verification = identity.verify_email(str(registration["verification_token"]))
        if "error" in verification:
            raise RuntimeError("Unable to verify synthetic demo operator")
        user_id = str(registration["user_id"])
    else:
        if not user.is_active or not user.email_verified:
            raise RuntimeError("Existing synthetic demo operator is inactive or unverified")
        user_id = str(user.id)

    identity.assign_role(
        user_id,
        tenant_id,
        EnterpriseRole.COMPLIANCE_ADMIN.value,
        assigned_by="system:synthetic_demo_bootstrap",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the read-only synthetic demo")
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument(
        "--operator-email",
        default=os.getenv("COMPLIANCEHUB_DEMO_OPERATOR_EMAIL", DEFAULT_OPERATOR_EMAIL),
    )
    args = parser.parse_args()

    _require_synthetic_contract()
    tenant_id = args.tenant_id.strip()
    operator_email = args.operator_email.strip().lower()
    if not tenant_id or not operator_email or "@" not in operator_email:
        raise RuntimeError("Synthetic tenant ID and operator email must be configured")
    password = read_secret(
        "COMPLIANCEHUB_DEMO_OPERATOR_PASSWORD",
        "COMPLIANCEHUB_DEMO_OPERATOR_PASSWORD_FILE",
        required=True,
        minimum_characters=16,
    )

    Base.metadata.create_all(bind=engine)
    migration = run_all_db_migrations(engine)
    if migration.ledgerless_unsatisfied:
        raise RuntimeError("Synthetic schema migrations remain unsatisfied")

    with SessionLocal() as session:
        ensure_cross_regulation_catalog_seeded(session)
        ensure_ai_kpi_definitions_seeded(session)
        _ensure_tenant_and_seed(session, tenant_id)
        _ensure_operator(
            session,
            tenant_id=tenant_id,
            email=operator_email,
            password=password,
        )

    print(
        "synthetic_demo_bootstrap=passed "
        f"tenant_id={tenant_id} operator_email={operator_email} password_disclosed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

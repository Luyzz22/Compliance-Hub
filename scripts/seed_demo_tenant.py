#!/usr/bin/env python3
"""Legt Demo-Mandanten mit Pilot-Feature-Defaults an und führt den Demo-Daten-Seed aus.

Beispiele:
  python scripts/seed_demo_tenant.py --preset mittelstand-ag
  python scripts/seed_demo_tenant.py --all-presets
  python scripts/seed_demo_tenant.py --tenant-id demo-x \\
      --template kritis_energy --display-name "Demo AG"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db import SessionLocal  # noqa: E402
from app.feature_flags import FeatureFlag  # noqa: E402
from app.repositories.ai_governance_actions import AIGovernanceActionRepository  # noqa: E402
from app.repositories.ai_systems import AISystemRepository  # noqa: E402
from app.repositories.classifications import ClassificationRepository  # noqa: E402
from app.repositories.evidence_files import EvidenceFileRepository  # noqa: E402
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository  # noqa: E402
from app.repositories.policies import PolicyRepository  # noqa: E402
from app.repositories.tenant_api_keys import TenantApiKeyRepository  # noqa: E402
from app.repositories.tenant_feature_overrides import TenantFeatureOverrideRepository  # noqa: E402
from app.repositories.tenant_registry import TenantRegistryRepository  # noqa: E402
from app.services.ai_kpi_seed import ensure_ai_kpi_definitions_seeded  # noqa: E402
from app.services.cross_regulation_seed import ensure_cross_regulation_catalog_seeded  # noqa: E402
from app.services.demo_governance_maturity_seed import (  # noqa: E402
    seed_demo_governance_maturity_layer,
)
from app.services.demo_tenant_seeder import seed_demo_tenant  # noqa: E402
from app.services.tenant_provisioning import PILOT_TENANT_FEATURE_DEFAULTS  # noqa: E402

DEMO_PRESETS: dict[str, dict[str, str]] = {
    "mittelstand-ag": {
        "tenant_id": "demo-mittelstand-ag",
        "display_name": "Mittelstand AG",
        "template_key": "industrial_sme",
        "industry": "Manufacturing",
        "country": "DE",
    },
    "grc-consulting": {
        "tenant_id": "demo-grc-consulting",
        "display_name": "GRC Consulting GmbH",
        "template_key": "tax_advisor",
        "industry": "Professional Services",
        "country": "DE",
    },
}


def _demo_feature_flags() -> dict[str, bool]:
    d = dict(PILOT_TENANT_FEATURE_DEFAULTS)
    d[FeatureFlag.demo_seeding.value] = True
    return d


def _ensure_tenant_and_seed(session, spec: dict[str, str], *, create_api_key: bool) -> None:
    tid = spec["tenant_id"]
    reg = TenantRegistryRepository(session)
    row = reg.get_by_id(tid)
    if row is None:
        reg.create(
            tenant_id=tid,
            display_name=spec["display_name"][:255],
            industry=spec["industry"][:128],
            country=spec["country"][:64],
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
        print(f"tenant registry: created {tid} (is_demo=True)")
    else:
        print(f"tenant registry: exists {tid}")

    TenantFeatureOverrideRepository(session).set_many(tid, _demo_feature_flags())

    ai = AISystemRepository(session)
    if ai.list_for_tenant(tid):
        print(f"skip core seed: tenant {tid} already has AI systems")
    else:
        result = seed_demo_tenant(
            session,
            spec["template_key"],
            tid,
            advisor_id=None,
            ai_repo=ai,
            cls_repo=ClassificationRepository(session),
            nis2_repo=Nis2KritisKpiRepository(session),
            policy_repo=PolicyRepository(session),
            action_repo=AIGovernanceActionRepository(session),
            evidence_repo=EvidenceFileRepository(session),
        )
        br = result.board_reports_count
        kr = result.ai_kpi_value_rows_count
        xr = result.cross_reg_control_rows_count
        print(
            f"seed ok: systems={result.ai_systems_count} board_reports={br} "
            f"kpi_rows={kr} xref_ctrls={xr}",
        )

    layer = seed_demo_governance_maturity_layer(session, tid)
    print(
        f"governance maturity layer: telemetry_events={layer.telemetry_events_inserted} "
        f"runtime_events={layer.runtime_events_inserted} "
        f"oami_snapshot={layer.oami_snapshot_persisted} "
        f"skipped_already={layer.skipped_already_seeded}",
    )

    if create_api_key:
        keys = TenantApiKeyRepository(session).list_for_tenant(tid)
        if not keys:
            _, plain = TenantApiKeyRepository(session).create_key(
                tenant_id=tid,
                name="Demo Workspace Key",
            )
            print("created API key (store securely; shown once):")
            print(plain)
        else:
            print(f"tenant already has {len(keys)} API key(s); omitting new key")


def main() -> None:
    p = argparse.ArgumentParser(description="Seed demo tenants for ComplianceHub")
    p.add_argument(
        "--preset", choices=sorted(DEMO_PRESETS.keys()), help="Vordefiniertes Demo-Profil"
    )
    p.add_argument("--all-presets", action="store_true", help="Alle Presets nacheinander")
    p.add_argument("--tenant-id", help="Eigene tenant_id (mit --template/--display-name)")
    p.add_argument("--template", help="Template-Key (kritis_energy, industrial_sme, tax_advisor)")
    p.add_argument("--display-name", help="Anzeigename")
    p.add_argument("--industry", default="Demo", help="Branche (bei manueller Angabe)")
    p.add_argument("--country", default="DE", help="Land")
    p.add_argument("--no-api-key", action="store_true", help="Keinen Mandanten-API-Key erzeugen")
    args = p.parse_args()

    if args.all_presets:
        specs = list(DEMO_PRESETS.values())
    elif args.preset:
        specs = [DEMO_PRESETS[args.preset]]
    elif args.tenant_id and args.template and args.display_name:
        specs = [
            {
                "tenant_id": args.tenant_id.strip(),
                "template_key": args.template.strip(),
                "display_name": args.display_name.strip(),
                "industry": args.industry.strip(),
                "country": args.country.strip(),
            },
        ]
    else:
        p.error(
            "Nutzen Sie --preset, --all-presets oder --tenant-id mit --template und --display-name"
        )

    s = SessionLocal()
    try:
        ensure_cross_regulation_catalog_seeded(s)
        ensure_ai_kpi_definitions_seeded(s)
        for spec in specs:
            print("---", spec["tenant_id"], "---")
            _ensure_tenant_and_seed(s, spec, create_api_key=not args.no_api_key)
    finally:
        s.close()


if __name__ == "__main__":
    main()

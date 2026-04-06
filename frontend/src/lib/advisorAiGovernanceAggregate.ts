import "server-only";

import { buildAdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceBuild";
import type { AdvisorAiGovernanceSnapshotInput } from "@/lib/advisorAiGovernanceTypes";
import type { MappedTenantPillarSnapshotBundle, TenantPillarSnapshot } from "@/lib/boardReadinessAggregate";
import { loadMappedTenantPillarSnapshots } from "@/lib/boardReadinessAggregate";

export function advisorAiGovernanceSnapshotInputFromTenant(s: TenantPillarSnapshot): AdvisorAiGovernanceSnapshotInput {
  const hrIds =
    s.raw.compliance_dashboard?.systems
      .filter((x) => x.risk_level === "high_risk")
      .map((x) => x.ai_system_id) ?? [];
  let high_risk_without_owner_count = 0;
  for (const id of hrIds) {
    const sys = s.raw.ai_systems.find((x) => x.id === id);
    if (!String(sys?.owner_email || "").trim()) high_risk_without_owner_count += 1;
  }

  return {
    tenant_id: s.tenant_id,
    mandant_label: s.tenant_label,
    api_fetch_ok: s.raw.fetch_ok,
    declared_ai_system_count: s.raw.ai_systems.length,
    has_compliance_dashboard: s.raw.compliance_dashboard != null,
    high_risk_system_count: s.eu.hr_total,
    eu_ai_act_status: s.eu.status,
    eu_ai_act_score: s.eu.score,
    iso_42001_status: s.iso.status,
    iso_42001_score: s.iso.score,
    board_report_fresh_when_hr: s.eu.board_fresh,
    high_risk_without_owner_count,
  };
}

export function computeAdvisorAiGovernanceFromBundle(bundle: MappedTenantPillarSnapshotBundle) {
  const inputs = bundle.snapshots.map(advisorAiGovernanceSnapshotInputFromTenant);
  return buildAdvisorAiGovernancePortfolioDto(inputs, bundle.tenants_partial, bundle.generated_at);
}

export async function computeAdvisorAiGovernanceOverview(now: Date = new Date()) {
  const bundle = await loadMappedTenantPillarSnapshots(now);
  return computeAdvisorAiGovernanceFromBundle(bundle);
}

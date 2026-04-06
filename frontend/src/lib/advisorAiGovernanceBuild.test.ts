import { describe, expect, it } from "vitest";

import {
  buildAdvisorAiGovernanceMandantRow,
  buildAdvisorAiGovernancePortfolioDto,
  stubAdvisorAiGovernancePortfolioDto,
  trafficToCompletenessBucket,
} from "@/lib/advisorAiGovernanceBuild";
import type { AdvisorAiGovernanceSnapshotInput } from "@/lib/advisorAiGovernanceTypes";
import { ADVISOR_AI_GOVERNANCE_VERSION } from "@/lib/advisorAiGovernanceTypes";

function baseInput(partial: Partial<AdvisorAiGovernanceSnapshotInput> = {}): AdvisorAiGovernanceSnapshotInput {
  return {
    tenant_id: "t-1",
    mandant_label: "Acme",
    api_fetch_ok: true,
    declared_ai_system_count: 2,
    has_compliance_dashboard: true,
    high_risk_system_count: 1,
    eu_ai_act_status: "amber",
    eu_ai_act_score: 55,
    iso_42001_status: "red",
    iso_42001_score: 33,
    board_report_fresh_when_hr: true,
    high_risk_without_owner_count: 1,
    ...partial,
  };
}

describe("advisorAiGovernanceBuild", () => {
  it("trafficToCompletenessBucket maps traffic", () => {
    expect(trafficToCompletenessBucket("red", true)).toBe("weak");
    expect(trafficToCompletenessBucket("amber", true)).toBe("medium");
    expect(trafficToCompletenessBucket("green", true)).toBe("strong");
    expect(trafficToCompletenessBucket("green", false)).toBe("unknown");
  });

  it("buildAdvisorAiGovernanceMandantRow sets registration and oversight hints", () => {
    const row = buildAdvisorAiGovernanceMandantRow(baseInput());
    expect(row.high_risk_indicator).toBe("yes");
    expect(row.registration_relevance).toBe("yes");
    expect(row.human_oversight_readiness).toBe("no");
    expect(row.notes_de.length).toBeGreaterThan(0);
  });

  it("stubAdvisorAiGovernancePortfolioDto matches version", () => {
    const dto = stubAdvisorAiGovernancePortfolioDto("2026-04-01T12:00:00Z");
    expect(dto.version).toBe(ADVISOR_AI_GOVERNANCE_VERSION);
    expect(dto.summary.total_mandanten).toBe(0);
  });

  it("buildAdvisorAiGovernancePortfolioDto aggregates buckets", () => {
    const dto = buildAdvisorAiGovernancePortfolioDto(
      [baseInput({ tenant_id: "a" }), baseInput({ tenant_id: "b", high_risk_system_count: 0, high_risk_without_owner_count: 0 })],
      0,
      "2026-04-01T12:00:00Z",
    );
    expect(dto.mandanten).toHaveLength(2);
    expect(dto.summary.count_potential_high_risk_exposure).toBe(1);
    expect(dto.top_attention.length).toBeGreaterThan(0);
    expect(dto.markdown_de).toContain("AI-Governance");
  });
});

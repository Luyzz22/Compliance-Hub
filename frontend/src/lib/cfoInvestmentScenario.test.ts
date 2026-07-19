import { describe, expect, it } from "vitest";

import type { EnterpriseInvestmentInitiativeDto } from "@/lib/api";

import { CFO_SCENARIOS, rankInvestmentInitiatives } from "./cfoInvestmentScenario";

function initiative(
  id: string,
  scores: Pick<
    EnterpriseInvestmentInitiativeDto,
    | "strategic_value_score"
    | "risk_reduction_score"
    | "execution_confidence_score"
    | "capital_efficiency_score"
  >,
): EnterpriseInvestmentInitiativeDto {
  return {
    initiative_id: id,
    tenant_id: "tenant-cfo",
    connector_type: "generic_api",
    initiative_name_de: id,
    baseline_rank: 1,
    recommended_decision: "sequence",
    investment_envelope_band: "medium",
    time_to_value_band: "mid_term",
    blocker_score: 20,
    portfolio_score: 70,
    decision_rationale_de: "Kontrollierte Testannahme.",
    funding_preconditions_de: ["Finance Owner bestätigen."],
    source_refs: ["test"],
    requires_finance_input: true,
    is_financial_estimate: false,
    ...scores,
  };
}

describe("CFO investment scenarios", () => {
  it("uses explicit weights that each sum to 100", () => {
    for (const scenario of CFO_SCENARIOS) {
      expect(Object.values(scenario.weights).reduce((sum, value) => sum + value, 0)).toBe(100);
    }
  });

  it("re-ranks deterministically without changing source initiatives", () => {
    const strategic = initiative("Strategischer Hebel", {
      strategic_value_score: 95,
      risk_reduction_score: 40,
      execution_confidence_score: 75,
      capital_efficiency_score: 40,
    });
    const risk = initiative("Risikohebel", {
      strategic_value_score: 55,
      risk_reduction_score: 95,
      execution_confidence_score: 80,
      capital_efficiency_score: 80,
    });
    const source = [strategic, risk];

    expect(rankInvestmentInitiatives(source, "risk_containment")[0].initiative_id).toBe(
      "Risikohebel",
    );
    expect(rankInvestmentInitiatives(source, "acceleration")[0].initiative_id).toBe(
      "Strategischer Hebel",
    );
    expect(source[0]).toBe(strategic);
    expect(source[0]).not.toHaveProperty("scenario_score");
  });
});

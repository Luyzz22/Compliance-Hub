import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { EnterpriseInvestmentInitiativeDto } from "@/lib/api";

import { CfoInvestmentScenarioExplorer } from "./CfoInvestmentScenarioExplorer";

afterEach(() => {
  cleanup();
});

function initiative(
  id: string,
  name: string,
  strategic: number,
  risk: number,
): EnterpriseInvestmentInitiativeDto {
  return {
    initiative_id: id,
    tenant_id: "tenant-cfo",
    connector_type: "generic_api",
    initiative_name_de: name,
    baseline_rank: 1,
    recommended_decision: "sequence",
    investment_envelope_band: "medium",
    time_to_value_band: "mid_term",
    strategic_value_score: strategic,
    risk_reduction_score: risk,
    execution_confidence_score: 75,
    capital_efficiency_score: 50,
    blocker_score: 20,
    portfolio_score: 70,
    decision_rationale_de: "Kontrollierte Testannahme.",
    funding_preconditions_de: ["Finance Owner bestätigen."],
    source_refs: ["test"],
    requires_finance_input: true,
    is_financial_estimate: false,
  };
}

describe("CfoInvestmentScenarioExplorer", () => {
  it("switches the visible decision lens without mutating the baseline", () => {
    render(
      <CfoInvestmentScenarioExplorer
        initiatives={[
          initiative("strategic", "Strategischer Hebel", 98, 35),
          initiative("risk", "Risikohebel", 45, 98),
        ]}
      />,
    );

    const riskButton = screen.getByRole("button", { name: "Risikobegrenzung" });
    expect(riskButton.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(riskButton);

    expect(riskButton.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("heading", { name: "Risikohebel", level: 3 })).toBeTruthy();
    expect(screen.getByText(/Priorisiert die stärkste Compliance/)).toBeTruthy();
  });
});

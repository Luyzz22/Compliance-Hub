import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AdvisorPortfolioTenantEntry } from "@/lib/api";

import { AdvisorPortfolioTable } from "./AdvisorPortfolioTable";

vi.mock("@/lib/workspaceTenantClient", () => ({
  openWorkspaceTenantAndGoComplianceOverview: vi.fn(),
}));

const sampleRows: AdvisorPortfolioTenantEntry[] = [
  {
    tenant_id: "t-demo-1",
    tenant_name: "Demo Mandant A",
    industry: "IT",
    country: "DE",
    eu_ai_act_readiness: 0.72,
    nis2_kritis_kpi_mean_percent: 55,
    nis2_kritis_systems_full_coverage_ratio: 0.4,
    high_risk_systems_count: 2,
    open_governance_actions_count: 3,
    setup_completed_steps: 4,
    setup_total_steps: 7,
    setup_progress_ratio: 4 / 7,
  },
];

describe("AdvisorPortfolioTable", () => {
  it("renders tenant name and readiness", () => {
    render(<AdvisorPortfolioTable rows={sampleRows} />);
    expect(screen.getByText("Demo Mandant A")).toBeTruthy();
    expect(screen.getByText("72%")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Tenant öffnen/i })).toBeTruthy();
  });

  it("shows empty state without rows", () => {
    render(<AdvisorPortfolioTable rows={[]} />);
    expect(screen.getByText(/Keine Mandanten in diesem Portfolio/)).toBeTruthy();
  });
});

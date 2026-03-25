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
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    expect(screen.getByText("Demo Mandant A")).toBeTruthy();
    expect(screen.getByText("72%")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Tenant öffnen/i })).toBeTruthy();
  });

  it("shows Mandanten-Steckbrief download links when advisorId is set", () => {
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    const mdLinks = screen.getAllByRole("link", { name: /Steckbrief \(MD\)/i });
    expect(mdLinks.length).toBeGreaterThanOrEqual(1);
    const mdHref = mdLinks[0].getAttribute("href") ?? "";
    expect(mdHref).toContain("/api/advisor/tenant-report");
    expect(mdHref).toContain("tenantId=t-demo-1");
    expect(mdHref).toContain("format=markdown");
    expect(mdHref).toContain("advisorId=advisor-demo%40example.com");

    const jsonLinks = screen.getAllByRole("link", { name: /^JSON$/i });
    expect(jsonLinks[0].getAttribute("href") ?? "").toContain("format=json");
  });

  it("shows empty state without rows", () => {
    render(<AdvisorPortfolioTable rows={[]} advisorId="x" />);
    expect(screen.getByText(/Keine Mandanten in diesem Portfolio/)).toBeTruthy();
  });
});

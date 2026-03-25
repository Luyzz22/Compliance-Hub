import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AdvisorPortfolioTenantEntry } from "@/lib/api";

import { AdvisorPortfolioTable } from "./AdvisorPortfolioTable";

const portfolioFeatureFlags = vi.hoisted(() => ({ snapshot: true, readiness: true }));

vi.mock("@/lib/workspaceTenantClient", () => ({
  openWorkspaceTenantAndGoComplianceOverview: vi.fn(),
  openWorkspaceTenantAndGo: vi.fn(),
}));

vi.mock("@/lib/config", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/config")>();
  return {
    ...actual,
    featurePilotRunbook: () => true,
    featureAdvisorClientSnapshot: () => portfolioFeatureFlags.snapshot,
    featureReadinessScore: () => portfolioFeatureFlags.readiness,
  };
});

afterEach(() => {
  portfolioFeatureFlags.snapshot = true;
  portfolioFeatureFlags.readiness = true;
  cleanup();
});

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
    governance_brief: {
      wizard_progress_count: 4,
      wizard_steps_total: 6,
      active_framework_keys: ["eu_ai_act", "iso_42001", "nis2"],
      cross_reg_mean_coverage_percent: 62,
      regulatory_gap_count: 5,
      nis2_critical_ai_count: 1,
    },
    readiness_summary: { score: 58, level: "managed" },
  },
];

describe("AdvisorPortfolioTable", () => {
  it("renders tenant name and readiness", () => {
    portfolioFeatureFlags.snapshot = true;
    portfolioFeatureFlags.readiness = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    expect(screen.getByText("Demo Mandant A")).toBeTruthy();
    expect(screen.getByText("72%")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Tenant öffnen/i })).toBeTruthy();
  });

  it("shows Mandanten-Steckbrief download links when advisorId is set", () => {
    portfolioFeatureFlags.snapshot = true;
    portfolioFeatureFlags.readiness = true;
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

  it("renders governance snapshot link and framework badges when brief is present", () => {
    portfolioFeatureFlags.snapshot = true;
    portfolioFeatureFlags.readiness = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    const snap = screen.getByTestId("advisor-snapshot-link-t-demo-1");
    expect(snap.getAttribute("href")).toBe("/advisor/clients/t-demo-1/governance-snapshot");
    expect(screen.getByText("eu_ai_act")).toBeTruthy();
    expect(screen.getByText("4/6")).toBeTruthy();
    expect(screen.getByText("62%")).toBeTruthy();
    expect(screen.getByText(/NIS2-krit\.: 1/)).toBeTruthy();
    expect(screen.getByTestId("advisor-readiness-badge-t-demo-1").textContent).toContain("58");
  });

  it("hides snapshot columns when featureAdvisorClientSnapshot is off", () => {
    portfolioFeatureFlags.snapshot = false;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    expect(screen.queryByTestId("advisor-snapshot-link-t-demo-1")).toBeNull();
    expect(screen.queryByText("Snapshot anzeigen")).toBeNull();
  });

  it("hides readiness column when featureReadinessScore is off", () => {
    portfolioFeatureFlags.readiness = false;
    portfolioFeatureFlags.snapshot = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    expect(screen.queryByTestId("advisor-readiness-badge-t-demo-1")).toBeNull();
    expect(screen.queryByText("Readiness")).toBeNull();
  });
});

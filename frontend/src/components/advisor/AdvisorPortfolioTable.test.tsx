import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AdvisorPortfolioTenantEntry } from "@/lib/api";
import {
  PORTFOLIO_COL_GAI_SHORT,
  PORTFOLIO_COL_OAMI_SHORT,
  PORTFOLIO_COL_READINESS,
  getActivityCopy,
  getMonitoringCopy,
} from "@/lib/governanceMaturityDeCopy";

import { AdvisorPortfolioTable } from "./AdvisorPortfolioTable";

const portfolioFeatureFlags = vi.hoisted(() => ({
  snapshot: true,
  readiness: true,
  governanceMaturity: true,
}));

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
    featureGovernanceMaturity: () => portfolioFeatureFlags.governanceMaturity,
  };
});

afterEach(() => {
  portfolioFeatureFlags.snapshot = true;
  portfolioFeatureFlags.readiness = true;
  portfolioFeatureFlags.governanceMaturity = true;
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
    governance_activity_summary: { index: 42, level: "medium" },
    operational_monitoring_summary: { index: 55, level: "high" },
    governance_maturity_advisor_brief: {
      governance_maturity_summary: {
        readiness: { score: 58, level: "managed", short_reason: "x" },
        activity: { index: 42, level: "medium", short_reason: "y" },
        operational_monitoring: { index: 55, level: "high", short_reason: "z" },
        overall_assessment: {
          level: "medium",
          short_summary: "Kurz.",
          key_risks: [],
          key_strengths: [],
        },
      },
      recommended_focus_areas: ["OAMI niedrig – Monitoring ausbauen"],
      suggested_next_steps_window: "nächste 90 Tage",
    },
    advisor_priority: "medium",
    advisor_priority_sort_key: 1,
    advisor_priority_explanation_de:
      "Mittlere Priorität: Readiness etabliert; GAI/OAMI ohne kritische Lücke.",
    maturity_scenario_hint: null,
    primary_focus_tag_de: "Monitoring",
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

  it("shows Reife-Brief focus marker when governance maturity brief is present", () => {
    portfolioFeatureFlags.governanceMaturity = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    const cell = screen.getByTestId("advisor-gm-brief-t-demo-1");
    expect(cell.textContent).toContain("Fokus:");
    expect(cell.textContent).toContain("OAMI");
  });

  it("includes focus areas and next-steps window in Reife-Brief tooltip title", () => {
    portfolioFeatureFlags.governanceMaturity = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    const span = screen.getByTestId("advisor-gm-brief-t-demo-1").querySelector("span[title]");
    const title = span?.getAttribute("title") ?? "";
    expect(title).toContain("OAMI niedrig");
    expect(title).toContain("Zeithorizont:");
    expect(title).toContain("nächste 90 Tage");
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
    expect(snap.getAttribute("href")).toBe(
      "/advisor/clients/t-demo-1/governance-snapshot?highlight=governance-maturity",
    );
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
    expect(screen.queryByText(PORTFOLIO_COL_READINESS)).toBeNull();
  });

  it("uses governanceMaturityDeCopy column headers and index level labels for GAI/OAMI", () => {
    portfolioFeatureFlags.governanceMaturity = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);

    expect(
      screen.getByRole("columnheader", { name: PORTFOLIO_COL_READINESS }),
    ).toBeTruthy();
    expect(
      screen.getByRole("columnheader", { name: PORTFOLIO_COL_GAI_SHORT }),
    ).toBeTruthy();
    expect(
      screen.getByRole("columnheader", { name: PORTFOLIO_COL_OAMI_SHORT }),
    ).toBeTruthy();

    const gaiCell = screen.getByTestId("advisor-gai-cell-t-demo-1");
    expect(gaiCell.textContent).toContain("42");
    expect(gaiCell.textContent).toContain(getActivityCopy("medium").levelLabelDe);

    const oamiCell = screen.getByTestId("advisor-oami-cell-t-demo-1");
    expect(oamiCell.textContent).toContain("55");
    expect(oamiCell.textContent).toContain(getMonitoringCopy("high").levelLabelDe);
  });

  it("renders advisor priority badge and Schwerpunkt from API fields", () => {
    portfolioFeatureFlags.governanceMaturity = true;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    const pri = screen.getByTestId("advisor-priority-t-demo-1");
    expect(pri.textContent).toContain("Mittel");
    const focus = screen.getByTestId("advisor-primary-focus-t-demo-1");
    expect(focus.textContent).toContain("Monitoring");
    const priWrap = pri.querySelector("span[title]");
    expect(priWrap?.getAttribute("title") ?? "").toContain("Mittlere Priorität");
  });

  it("hides GAI/OAMI columns when featureGovernanceMaturity is off", () => {
    portfolioFeatureFlags.governanceMaturity = false;
    render(<AdvisorPortfolioTable rows={sampleRows} advisorId="advisor-demo@example.com" />);
    expect(screen.queryByRole("columnheader", { name: PORTFOLIO_COL_GAI_SHORT })).toBeNull();
    expect(screen.queryByTestId("advisor-gai-cell-t-demo-1")).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /Reife-Brief/i })).toBeNull();
    expect(screen.queryByTestId("advisor-gm-brief-t-demo-1")).toBeNull();
  });
});

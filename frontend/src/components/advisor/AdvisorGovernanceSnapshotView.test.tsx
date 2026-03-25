import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AdvisorClientGovernanceSnapshotDto } from "@/lib/api";

import { AdvisorGovernanceSnapshotView } from "./AdvisorGovernanceSnapshotView";

const { fetchSnap, postMd } = vi.hoisted(() => {
  const minimalSnapshot: AdvisorClientGovernanceSnapshotDto = {
    advisor_id: "adv@x",
    client_tenant_id: "t-1",
    generated_at_utc: "2025-01-01T00:00:00Z",
    client_info: {
      tenant_id: "t-1",
      display_name: "Mandant X",
      industry: "IT",
      country: "DE",
      tenant_kind: "enterprise",
      registry_nis2_scope: null,
      registry_ai_act_scope: null,
    },
    setup_status: {
      guided_setup_completed_steps: 2,
      guided_setup_total_steps: 7,
      ai_governance_wizard_progress_steps: [1, 2],
      ai_governance_wizard_steps_total: 6,
      ai_governance_wizard_marked_steps: [],
    },
    framework_scope: { active_frameworks: ["eu_ai_act"], compliance_scopes: [] },
    ai_systems_summary: {
      total_count: 3,
      high_risk_count: 1,
      nis2_critical_count: 0,
      by_risk_level: {},
    },
    kpi_summary: {
      high_risk_systems_in_scope: 1,
      systems_with_kpi_values: 0,
      critical_kpi_system_rows: 0,
      aggregate_trends_non_flat: 0,
    },
    cross_reg_summary: [
      {
        framework_key: "eu_ai_act",
        name: "EU AI Act",
        coverage_percent: 50,
        gap_count: 2,
        total_requirements: 10,
      },
    ],
    gap_assist: { regulatory_gap_items_count: 1, llm_gap_suggestions_count: null },
    reports_summary: {
      reports_total: 0,
      last_report_id: null,
      last_report_created_at: null,
      last_report_audience: null,
      last_report_title: null,
    },
  };
  const fetchSnap = vi.fn().mockResolvedValue(minimalSnapshot);
  const postMd = vi.fn().mockResolvedValue({
    markdown: "## Test\n\n- Punkt",
    provider: "anthropic",
    model_id: "claude",
  });
  return { fetchSnap, postMd };
});

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    ADVISOR_ID_FROM_ENV: "adv@test",
    fetchAdvisorClientGovernanceSnapshot: fetchSnap,
    postAdvisorGovernanceSnapshotMarkdown: postMd,
  };
});

vi.mock("@/lib/workspaceTenantClient", () => ({
  openWorkspaceTenantAndGo: vi.fn(),
}));

vi.mock("@/lib/config", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/config")>();
  return {
    ...actual,
    featureAiComplianceBoardReport: () => false,
  };
});

describe("AdvisorGovernanceSnapshotView", () => {
  it("loads snapshot and triggers markdown POST on button click", async () => {
    render(<AdvisorGovernanceSnapshotView clientTenantId="t-1" />);

    await waitFor(() => {
      expect(fetchSnap).toHaveBeenCalledWith("adv@test", "t-1");
    });
    expect(await screen.findByText("Mandant X")).toBeTruthy();
    expect(screen.getByTestId("snap-client-info")).toBeTruthy();

    fireEvent.click(screen.getByTestId("snap-gen-md"));
    await waitFor(() => {
      expect(postMd).toHaveBeenCalledWith("adv@test", "t-1");
    });
    expect(await screen.findByTestId("snap-md-preview")).toBeTruthy();
    expect(screen.getByText("Punkt")).toBeTruthy();
  });
});

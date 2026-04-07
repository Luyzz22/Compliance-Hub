import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AdvisorClientGovernanceSnapshotDto } from "@/lib/api";
import {
  GAI_FULL_NAME,
  GAI_TOOLTIP_C_LEVEL,
  OAMI_DEMO_SIGNALS_NOTE,
  OAMI_FULL_NAME,
  OAMI_SECTION_TITLE,
  OAMI_TOOLTIP_C_LEVEL,
  READINESS_PRODUCT_TITLE,
  READINESS_TAGLINE,
} from "@/lib/governanceMaturityDeCopy";

import { AdvisorGovernanceSnapshotView } from "./AdvisorGovernanceSnapshotView";

const snapshotViewFlags = vi.hoisted(() => ({
  readinessScore: false,
  governanceMaturity: false,
}));

const navSearchParams = vi.hoisted(() => ({ current: new URLSearchParams() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => navSearchParams.current,
}));

const { fetchSnap, postMd, fetchAdvisorReadiness, minimalSnapshot } = vi.hoisted(() => {
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
      ki_register_registered: 1,
      ki_register_planned: 1,
      ki_register_partial: 0,
      ki_register_unknown: 1,
      advisor_attention_items: 2,
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
    operational_ai_monitoring: {
      index_90d: 58,
      level: "medium",
      has_runtime_data: true,
      systems_scored: 2,
      narrative_de: "Operatives Monitoring: mittlere Reife (Demo).",
      drivers_de: ["Letzte Laufzeitereignisse", "KPI-Trends"],
      safety_related_runtime_incidents_90d: 2,
      availability_runtime_incidents_90d: 1,
      operational_subtype_hint_de: "Sicherheitsnahe Signale prägen den Index stärker.",
    },
    governance_maturity_advisor_brief: null,
  };
  const fetchSnap = vi.fn().mockResolvedValue(minimalSnapshot);
  const postMd = vi.fn().mockResolvedValue({
    markdown: "## Test\n\n- Punkt",
    provider: "anthropic",
    model_id: "claude",
  });
  const fetchAdvisorReadiness = vi.fn().mockResolvedValue({
    tenant_id: "t-1",
    score: 71,
    level: "managed",
    interpretation: "Readiness OK.",
    dimensions: {
      setup: { normalized: 0.7, score_0_100: 70 },
      coverage: { normalized: 0.7, score_0_100: 70 },
      kpi: { normalized: 0.7, score_0_100: 70 },
      gaps: { normalized: 0.7, score_0_100: 70 },
      reporting: { normalized: 0.7, score_0_100: 70 },
    },
  });
  return { fetchSnap, postMd, fetchAdvisorReadiness, minimalSnapshot };
});

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    ADVISOR_ID_FROM_ENV: "adv@test",
    fetchAdvisorClientGovernanceSnapshot: fetchSnap,
    postAdvisorGovernanceSnapshotMarkdown: postMd,
    fetchAdvisorTenantReadinessScore: fetchAdvisorReadiness,
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
    featureReadinessScore: () => snapshotViewFlags.readinessScore,
    featureGovernanceMaturity: () => snapshotViewFlags.governanceMaturity,
  };
});

afterEach(() => {
  snapshotViewFlags.readinessScore = false;
  snapshotViewFlags.governanceMaturity = false;
  minimalSnapshot.governance_maturity_advisor_brief = null;
  navSearchParams.current = new URLSearchParams();
  vi.useRealTimers();
  cleanup();
});

describe("AdvisorGovernanceSnapshotView", () => {
  it("loads snapshot and triggers markdown POST on button click", async () => {
    render(<AdvisorGovernanceSnapshotView clientTenantId="t-1" />);

    await waitFor(() => {
      expect(fetchSnap).toHaveBeenCalledWith("adv@test", "t-1");
    });
    expect(await screen.findByText("Mandant X")).toBeTruthy();
    expect(screen.getByTestId("snap-client-info")).toBeTruthy();
    expect(screen.getByTestId("snap-gai-note")).toBeTruthy();
    expect(screen.getByTestId("snap-oami")).toBeTruthy();
    expect(screen.getByTestId("snap-oami-subtype")).toBeTruthy();
    expect(screen.getByText(/Operatives Monitoring: mittlere Reife/i)).toBeTruthy();

    fireEvent.click(screen.getByTestId("snap-gen-md"));
    await waitFor(() => {
      expect(postMd).toHaveBeenCalledWith("adv@test", "t-1");
    });
    expect(await screen.findByTestId("snap-md-preview")).toBeTruthy();
    expect(screen.getByText("Punkt")).toBeTruthy();
  });

  it("renders Readiness, GAI and OAMI tiles using centralized copy strings", async () => {
    snapshotViewFlags.readinessScore = true;
    render(<AdvisorGovernanceSnapshotView clientTenantId="t-1" />);

    await waitFor(() => {
      expect(fetchAdvisorReadiness).toHaveBeenCalledWith("adv@test", "t-1");
    });

    const intro = screen.getByTestId("advisor-governance-snapshot-view");
    expect(intro.textContent).toContain(READINESS_PRODUCT_TITLE);
    expect(intro.textContent).toContain(READINESS_TAGLINE.slice(0, 40));
    expect(intro.textContent).toContain(GAI_FULL_NAME);
    expect(intro.textContent).toContain(GAI_TOOLTIP_C_LEVEL.slice(0, 40));
    expect(intro.textContent).toContain(OAMI_FULL_NAME);

    const readinessSection = await screen.findByTestId("snap-readiness");
    expect(within(readinessSection).getByText(READINESS_PRODUCT_TITLE)).toBeTruthy();

    const gaiTile = screen.getByTestId("snap-gai-note");
    expect(within(gaiTile).getByText(GAI_FULL_NAME)).toBeTruthy();
    expect(gaiTile.textContent).toContain(GAI_TOOLTIP_C_LEVEL.slice(0, 50));

    const oamiTile = screen.getByTestId("snap-oami");
    expect(within(oamiTile).getByText(OAMI_SECTION_TITLE)).toBeTruthy();
    expect(oamiTile.textContent).toContain(OAMI_TOOLTIP_C_LEVEL.slice(0, 50));
    expect(within(oamiTile).getByText(OAMI_DEMO_SIGNALS_NOTE)).toBeTruthy();
  });

  it("shows Governance-Maturity-Brief when feature flag and payload are set", async () => {
    snapshotViewFlags.governanceMaturity = true;
    minimalSnapshot.governance_maturity_advisor_brief = {
      governance_maturity_summary: {
        readiness: { score: 40, level: "basic", short_reason: "Aufbau." },
        activity: { index: 35, level: "low", short_reason: "Nutzen." },
        operational_monitoring: {
          index: 30,
          level: "low",
          short_reason: "Monitoring.",
        },
        overall_assessment: {
          level: "low",
          short_summary: "Konservatives Gesamtbild.",
          key_risks: [],
          key_strengths: [],
        },
      },
      recommended_focus_areas: ["OAMI niedrig – Monitoring ausbauen", "Readiness stärken"],
      suggested_next_steps_window: "nächste 90 Tage",
      client_ready_paragraph_de: "Kurz zum Weiterleiten an den Mandanten.",
    };
    render(<AdvisorGovernanceSnapshotView clientTenantId="t-1" />);
    expect(await screen.findByTestId("snap-gm-advisor-brief")).toBeTruthy();
    expect(screen.getByText(/Governance-Maturity-Brief/i)).toBeTruthy();
    expect(screen.getByText(/Konservatives Gesamtbild/i)).toBeTruthy();
    expect(screen.getByText(/nächste 90 Tage/i)).toBeTruthy();
    const focusList = screen.getByTestId("snap-gm-advisor-brief").querySelector("ul");
    expect(focusList?.textContent).toContain("OAMI niedrig");
    expect(screen.getByText(/Nächste Schritte \(Horizont\)/i)).toBeTruthy();
  });

  it("scrolls to governance-maturity brief when URL highlight=governance-maturity", async () => {
    snapshotViewFlags.governanceMaturity = true;
    navSearchParams.current = new URLSearchParams("highlight=governance-maturity");
    minimalSnapshot.governance_maturity_advisor_brief = {
      governance_maturity_summary: {
        readiness: { score: 40, level: "basic", short_reason: "Aufbau." },
        activity: { index: 35, level: "low", short_reason: "Nutzen." },
        operational_monitoring: {
          index: 30,
          level: "low",
          short_reason: "Monitoring.",
        },
        overall_assessment: {
          level: "low",
          short_summary: "Konservatives Gesamtbild.",
          key_risks: [],
          key_strengths: [],
        },
      },
      recommended_focus_areas: ["OAMI niedrig – Monitoring ausbauen"],
      suggested_next_steps_window: "nächste 90 Tage",
      client_ready_paragraph_de: "Kurz.",
    };
    const scrollIntoView = vi.fn();
    const origGet = document.getElementById.bind(document);
    const idSpy = vi.spyOn(document, "getElementById").mockImplementation((id: string) => {
      if (id === "governance-maturity-anchor") {
        return { scrollIntoView } as unknown as HTMLElement;
      }
      return origGet(id);
    });
    try {
      render(<AdvisorGovernanceSnapshotView clientTenantId="t-1" />);
      const section = await screen.findByTestId("snap-gm-advisor-brief");
      expect(section.id).toBe("governance-maturity-anchor");
      await waitFor(
        () => {
          expect(scrollIntoView).toHaveBeenCalledWith(
            expect.objectContaining({ behavior: "smooth", block: "start" }),
          );
        },
        { timeout: 3000 },
      );
    } finally {
      idSpy.mockRestore();
    }
  });
});

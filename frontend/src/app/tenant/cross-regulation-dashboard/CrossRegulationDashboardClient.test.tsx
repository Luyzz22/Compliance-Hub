import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CrossRegulationDashboardClient } from "./CrossRegulationDashboardClient";

afterEach(() => {
  cleanup();
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchRequirementControlsDetail: vi.fn().mockResolvedValue({
      requirement: {
        id: 1,
        framework_key: "eu_ai_act",
        framework_name: "EU AI Act",
        code: "Art.9",
        title: "Risiko",
        description: null,
        requirement_type: "governance",
        criticality: "high",
        coverage_status: "full",
        linked_control_count: 1,
        primary_control_names: ["C1"],
        related_framework_keys: ["eu_ai_act"],
      },
      links: [
        {
          link_id: 1,
          control_id: "c1",
          control_name: "C1",
          coverage_level: "full",
          control_status: "implemented",
          owner_role: "CISO",
          ai_system_ids: [],
          policy_ids: [],
          action_ids: [],
        },
      ],
    }),
  };
});

describe("CrossRegulationDashboardClient", () => {
  const summary = [
    {
      framework_key: "eu_ai_act",
      name: "EU AI Act",
      subtitle: "AI",
      total_requirements: 2,
      covered_requirements: 0,
      gap_count: 2,
      coverage_percent: 0,
      partial_count: 0,
      planned_only_count: 0,
    },
    {
      framework_key: "nis2",
      name: "NIS2",
      subtitle: "Cyber",
      total_requirements: 1,
      covered_requirements: 0,
      gap_count: 1,
      coverage_percent: 0,
      partial_count: 0,
      planned_only_count: 0,
    },
  ];

  const requirements = [
    {
      id: 1,
      framework_key: "eu_ai_act",
      framework_name: "EU AI Act",
      code: "Art.9",
      title: "Risiko",
      description: null,
      requirement_type: "governance",
      criticality: "high",
      coverage_status: "gap",
      linked_control_count: 0,
      primary_control_names: [],
      related_framework_keys: ["eu_ai_act"],
    },
    {
      id: 2,
      framework_key: "eu_ai_act",
      framework_name: "EU AI Act",
      code: "Art.10",
      title: "Daten",
      description: null,
      requirement_type: "governance",
      criticality: "high",
      coverage_status: "partial",
      linked_control_count: 1,
      primary_control_names: ["X"],
      related_framework_keys: ["eu_ai_act", "iso_42001"],
    },
    {
      id: 3,
      framework_key: "nis2",
      framework_name: "NIS2",
      code: "Art.21",
      title: "Risiko NIS2",
      description: null,
      requirement_type: "governance",
      criticality: "high",
      coverage_status: "gap",
      linked_control_count: 0,
      primary_control_names: [],
      related_framework_keys: ["nis2"],
    },
  ];

  it("zeigt Framework-Cards und Requirements-Tabelle", () => {
    render(
      <CrossRegulationDashboardClient
        tenantId="t1"
        summary={summary}
        requirements={requirements}
        controls={[]}
      />,
    );
    expect(screen.getByTestId("cross-reg-framework-cards")).toBeTruthy();
    expect(screen.getByTestId("cross-reg-requirements-table")).toBeTruthy();
    const cards = screen.getByTestId("cross-reg-framework-cards");
    expect(within(cards).getByRole("heading", { name: "EU AI Act" })).toBeTruthy();
    expect(screen.getAllByText(/Art\.9/).length).toBeGreaterThan(0);
  });

  it("filtert nach Framework EU AI Act", () => {
    render(
      <CrossRegulationDashboardClient
        tenantId="t1"
        summary={summary}
        requirements={requirements}
        controls={[]}
      />,
    );
    const table = screen.getByTestId("cross-reg-requirements-table");
    const fw = within(table).getByTestId("filter-framework");
    fireEvent.change(fw, { target: { value: "eu_ai_act" } });
    const rows = within(table).getAllByRole("row");
    // header + 2 data rows (Art.9, Art.10)
    expect(rows.length).toBe(3);
    expect(within(table).queryByText(/Art\.21/)).toBeNull();
  });

  it("filtert nach Coverage Lücke", () => {
    render(
      <CrossRegulationDashboardClient
        tenantId="t1"
        summary={summary}
        requirements={requirements}
        controls={[]}
      />,
    );
    const table = screen.getByTestId("cross-reg-requirements-table");
    fireEvent.change(within(table).getByTestId("filter-coverage"), {
      target: { value: "gap" },
    });
    const rows = within(table).getAllByRole("row");
    // Kopfzeile + Art.9 + Art.21 (Teilweise ausgeblendet)
    expect(rows.length).toBe(3);
  });
});

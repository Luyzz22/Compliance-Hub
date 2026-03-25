import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchKpis: vi.fn(),
  postKpi: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchTenantAiSystemKpis: mocks.fetchKpis,
    postTenantAiSystemKpi: mocks.postKpi,
  };
});

import { AiSystemKpiPanel } from "./AiSystemKpiPanel";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AiSystemKpiPanel", () => {
  it("renders KPI series and form", async () => {
    mocks.fetchKpis.mockResolvedValue({
      ai_system_id: "sys-1",
      series: [
        {
          definition: {
            id: "def-1",
            key: "incident_rate_ai",
            name: "Incident-Rate",
            description: "Test-Beschreibung",
            category: "compliance",
            unit: "percent",
            recommended_direction: "down",
            framework_tags: ["eu_ai_act"],
          },
          periods: [
            {
              id: "v1",
              period_start: "2025-01-01T00:00:00.000Z",
              period_end: "2025-03-31T00:00:00.000Z",
              value: 1.2,
              source: "manual",
              comment: null,
            },
          ],
          trend: "flat",
          latest_status: "ok",
        },
      ],
    });

    render(<AiSystemKpiPanel tenantId="t1" systemId="sys-1" />);

    await waitFor(() => {
      expect(screen.getByTestId("ai-system-kpi-panel")).toBeTruthy();
    });
    expect(screen.getByRole("heading", { name: "Incident-Rate" })).toBeTruthy();
    expect(screen.getByText("Wert erfassen / aktualisieren")).toBeTruthy();
  });
});

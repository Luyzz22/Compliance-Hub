import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  fetchList: vi.fn(),
  fetchDetail: vi.fn(),
  createReport: vi.fn(),
  fetchReadiness: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAiComplianceBoardReports: mocks.fetchList,
    fetchAiComplianceBoardReportDetail: mocks.fetchDetail,
    createAiComplianceBoardReport: mocks.createReport,
    fetchTenantReadinessScore: mocks.fetchReadiness,
  };
});

vi.mock("@/lib/config", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/config")>();
  return {
    ...actual,
    featureReadinessScore: () => true,
    featureLlmEnabled: () => false,
    featureLlmExplain: () => false,
  };
});

import { AiComplianceBoardReportClient } from "./AiComplianceBoardReportClient";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AiComplianceBoardReportClient", () => {
  const readinessPayload = {
    tenant_id: "t1",
    score: 50,
    level: "managed" as const,
    interpretation: "Kurz.",
    dimensions: {
      setup: { normalized: 0.5, score_0_100: 50 },
      coverage: { normalized: 0.5, score_0_100: 50 },
      kpi: { normalized: 0.5, score_0_100: 50 },
      gaps: { normalized: 0.5, score_0_100: 50 },
      reporting: { normalized: 0.5, score_0_100: 50 },
    },
  };

  it("lädt Historie und zeigt letzten Report", async () => {
    mocks.fetchReadiness.mockResolvedValue(readinessPayload);
    mocks.fetchList.mockResolvedValue([
      {
        id: "rep-1",
        title: "Test Report",
        audience_type: "board",
        created_at: "2026-01-15T12:00:00.000Z",
      },
    ]);
    mocks.fetchDetail.mockResolvedValue({
      id: "rep-1",
      tenant_id: "t1",
      title: "Test Report",
      audience_type: "board",
      created_at: "2026-01-15T12:00:00.000Z",
      rendered_markdown: "## Executive Overview\n\nHallo.",
      raw_payload: {},
    });

    render(<AiComplianceBoardReportClient tenantId="t1" />);

    await waitFor(() => {
      expect(screen.getByTestId("board-report-history")).toBeTruthy();
    });
    expect(screen.getByTestId("board-readiness-card")).toBeTruthy();
    expect(screen.getAllByText("Test Report").length).toBeGreaterThanOrEqual(1);
  });

  it("rendert die Markdown-Section AI Performance & Risk KPIs", async () => {
    mocks.fetchReadiness.mockResolvedValue(readinessPayload);
    mocks.fetchList.mockResolvedValue([
      {
        id: "rep-kpi",
        title: "Mit KPI",
        audience_type: "board",
        created_at: "2026-01-15T12:00:00.000Z",
      },
    ]);
    mocks.fetchDetail.mockResolvedValue({
      id: "rep-kpi",
      tenant_id: "t1",
      title: "Mit KPI",
      audience_type: "board",
      created_at: "2026-01-15T12:00:00.000Z",
      rendered_markdown:
        "## Executive Overview\n\nKurz.\n\n## AI Performance & Risk KPIs\n\nStub KPI Abschnitt.\n",
      raw_payload: {},
    });

    render(<AiComplianceBoardReportClient tenantId="t1" />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "AI Performance & Risk KPIs" }),
      ).toBeTruthy();
    });
  });

  it("ruft beim Generieren den API-Endpoint auf", async () => {
    mocks.fetchReadiness.mockResolvedValue(readinessPayload);
    mocks.fetchList.mockResolvedValue([]);
    mocks.createReport.mockResolvedValue({
      report_id: "new-1",
      title: "Neu",
      rendered_markdown: "# x",
      coverage_snapshot: [],
      created_at: "2026-01-15T12:00:00.000Z",
      audience_type: "board",
    });
    mocks.fetchDetail.mockResolvedValue({
      id: "new-1",
      tenant_id: "t1",
      title: "Neu",
      audience_type: "board",
      created_at: "2026-01-15T12:00:00.000Z",
      rendered_markdown: "# x",
      raw_payload: {},
    });

    render(<AiComplianceBoardReportClient tenantId="t1" />);

    fireEvent.click(screen.getByTestId("board-report-open-wizard"));
    fireEvent.click(screen.getByTestId("board-report-generate"));

    await waitFor(() => {
      expect(mocks.createReport).toHaveBeenCalledWith(
        "t1",
        expect.objectContaining({ audience_type: "board", language: "de" }),
      );
    });
  });
});

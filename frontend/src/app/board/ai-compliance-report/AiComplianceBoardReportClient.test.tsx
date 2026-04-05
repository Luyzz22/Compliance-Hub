import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TenantWorkspaceMetaDto } from "@/lib/api";
import type { UseWorkspaceModeResult } from "@/hooks/useWorkspaceMode";
import { resetWorkspaceTelemetryDebounceForTests } from "@/lib/workspaceTelemetry";

function tenantMeta(over: Partial<TenantWorkspaceMetaDto> = {}): TenantWorkspaceMetaDto {
  return {
    tenant_id: "t1",
    display_name: "X",
    is_demo: false,
    demo_playground: false,
    mutation_blocked: false,
    workspace_mode: "production",
    mode_label: "",
    mode_hint: "",
    demo_mode_feature_enabled: false,
    ...over,
  };
}

const mocks = vi.hoisted(() => ({
  fetchList: vi.fn(),
  fetchDetail: vi.fn(),
  createReport: vi.fn(),
  fetchReadiness: vi.fn(),
  useWorkspaceMode: vi.fn((tenantId?: string | null): UseWorkspaceModeResult => {
    void tenantId;
    return {
      meta: tenantMeta(),
      loading: false,
      error: null,
      mutationBlocked: false,
      isDemoTenant: false,
      isPlaygroundTenant: false,
      refetch: vi.fn(),
      workspaceMode: "production",
      modeLabel: "",
      modeHint: "",
      mutationsBlocked: false,
      isDemo: false,
      isProduction: true,
      isPlayground: false,
      isPlaygroundWritable: false,
      docsUrl: "",
    };
  }),
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

vi.mock("@/hooks/useWorkspaceMode", () => ({
  useWorkspaceMode: (tenantId?: string | null) => mocks.useWorkspaceMode(tenantId),
}));

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

beforeEach(() => {
  resetWorkspaceTelemetryDebounceForTests();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })),
  );
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  mocks.useWorkspaceMode.mockImplementation((tenantId?: string | null): UseWorkspaceModeResult => {
    void tenantId;
    return {
      meta: tenantMeta(),
      loading: false,
      error: null,
      mutationBlocked: false,
      isDemoTenant: false,
      isPlaygroundTenant: false,
      refetch: vi.fn(),
      workspaceMode: "production",
      modeLabel: "",
      modeHint: "",
      mutationsBlocked: false,
      isDemo: false,
      isProduction: true,
      isPlayground: false,
      isPlaygroundWritable: false,
      docsUrl: "",
    };
  });
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

  it("zeigt Demo-read-only-Hinweis und deaktiviert den Report-CTA bei mutationsBlocked", async () => {
    mocks.useWorkspaceMode.mockReturnValue({
      meta: tenantMeta({ workspace_mode: "demo", mutation_blocked: true, is_demo: true }),
      loading: false,
      error: null,
      mutationBlocked: true,
      isDemoTenant: true,
      isPlaygroundTenant: false,
      refetch: vi.fn(),
      workspaceMode: "demo" as const,
      modeLabel: "Demo",
      modeHint: "Hint",
      mutationsBlocked: true,
      isDemo: true,
      isProduction: false,
      isPlayground: false,
      isPlaygroundWritable: false,
      docsUrl: "",
    });
    mocks.fetchReadiness.mockResolvedValue(readinessPayload);
    mocks.fetchList.mockResolvedValue([]);

    render(<AiComplianceBoardReportClient tenantId="t1" />);

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeTruthy();
    });
    expect(screen.getByRole("status").textContent).toContain("read-only");

    const cta = screen.getByTestId("board-report-open-wizard") as HTMLButtonElement;
    expect(cta.disabled).toBe(true);
    expect(cta.textContent).toContain("Demo-Report");
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

  it("sendet genau ein board_reports_overview-Telemetrie-Event beim Mount", async () => {
    const fetchSpy = vi.mocked(globalThis.fetch);
    mocks.fetchReadiness.mockResolvedValue(readinessPayload);
    mocks.fetchList.mockResolvedValue([]);

    render(<AiComplianceBoardReportClient tenantId="t1" />);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const telemetryCalls = fetchSpy.mock.calls.filter((c) => c[0] === "/api/workspace/feature-used");
    expect(telemetryCalls.length).toBe(1);
    const init = telemetryCalls[0][1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      tenant_id: "t1",
      feature_name: "board_reports_overview",
      workspace_mode: "production",
      route_name: "/board/ai-compliance-report",
    });
    expect(body).not.toHaveProperty("display_name");
  });
});

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AIImpactAssessmentPortfolioResponseDto } from "@/lib/api";

const { serverSessionApiFetch } = vi.hoisted(() => ({
  serverSessionApiFetch: vi.fn(),
}));

vi.mock("@/lib/serverBackendApi", () => ({ serverSessionApiFetch }));

vi.mock("@/components/tenant/ImpactAssessmentWorkspace", () => ({
  ImpactAssessmentWorkspace: ({
    tenantId,
    initialData,
  }: {
    tenantId: string;
    initialData: AIImpactAssessmentPortfolioResponseDto;
  }) => (
    <div data-testid="impact-workspace">
      {tenantId}:{initialData.summary.total_systems}
    </div>
  ),
}));

import ImpactAssessmentsPage from "./page";

const portfolio: AIImpactAssessmentPortfolioResponseDto = {
  tenant_id: "session-bound-tenant",
  generated_at_utc: "2026-08-11T12:00:00Z",
  readiness_score_pct: 0,
  posture: "scope_incomplete",
  framework_version: "2026-08",
  source_urls: { gdpr: "https://example.test/gdpr", eu_ai_act: "https://example.test/ai-act" },
  legal_disclaimer_de: "Keine Rechtsberatung.",
  summary: {
    total_systems: 2,
    assessed_systems: 0,
    scope_open_count: 2,
    in_review_count: 0,
    approved_count: 0,
    high_residual_risk_count: 0,
    consultation_open_count: 0,
    overdue_review_count: 0,
  },
  systems: [],
};

describe("ImpactAssessmentsPage", () => {
  beforeEach(() => {
    serverSessionApiFetch.mockReset();
    serverSessionApiFetch.mockResolvedValue(
      new Response(JSON.stringify(portfolio), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("lädt den Erstzustand ausschließlich über die angemeldete Serversession", async () => {
    render(await ImpactAssessmentsPage());

    expect(serverSessionApiFetch).toHaveBeenCalledWith("/api/v1/impact-assessments");
    expect(screen.getByTestId("impact-workspace").textContent).toBe(
      "session-bound-tenant:2",
    );
  });

  it("bricht bei einer abgewiesenen Session ohne Fallback-Mandant ab", async () => {
    serverSessionApiFetch.mockResolvedValue(new Response(null, { status: 401 }));

    await expect(ImpactAssessmentsPage()).rejects.toThrow(
      "Impact Assessment API returned 401",
    );
  });
});

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { fetchReadiness } = vi.hoisted(() => ({
  fetchReadiness: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchTenantReadinessScore: fetchReadiness,
    postTenantReadinessScoreExplain: vi.fn(),
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

vi.mock("@/lib/workspaceTenantClient", () => ({
  openWorkspaceTenantAndGo: vi.fn(),
}));

import {
  DEMO_HINT_READINESS_CARD,
  getReadinessCopy,
  READINESS_PRODUCT_TITLE,
} from "@/lib/governanceMaturityDeCopy";

import { BoardReadinessCard } from "./BoardReadinessCard";

afterEach(() => {
  cleanup();
});

describe("BoardReadinessCard", () => {
  it("renders score and dimension bars", async () => {
    fetchReadiness.mockResolvedValue({
      tenant_id: "t-board",
      score: 63,
      level: "managed",
      interpretation: "Ihr aktueller AI & Compliance Readiness Score liegt bei 63/100.",
      dimensions: {
        setup: { normalized: 0.6, score_0_100: 60 },
        coverage: { normalized: 0.5, score_0_100: 50 },
        kpi: { normalized: 0.4, score_0_100: 40 },
        gaps: { normalized: 0.7, score_0_100: 70 },
        reporting: { normalized: 0.3, score_0_100: 30 },
      },
    });

    render(<BoardReadinessCard tenantId="t-board" />);

    await waitFor(() => {
      expect(screen.getByTestId("board-readiness-score-value").textContent).toContain("63");
    });
    expect(screen.getByTestId("readiness-dim-setup")).toBeTruthy();
    expect(screen.getByTestId("readiness-dim-coverage")).toBeTruthy();
  });

  it.each([
    ["basic", "Basis"],
    ["managed", "Etabliert"],
    ["embedded", "Integriert"],
  ] as const)("renders readiness level %s as %s (static)", async (level, deLabel) => {
    fetchReadiness.mockResolvedValue({
      tenant_id: "t-x",
      score: 50,
      level,
      interpretation: "Test.",
      dimensions: {
        setup: { normalized: 0.5, score_0_100: 50 },
        coverage: { normalized: 0.5, score_0_100: 50 },
        kpi: { normalized: 0.5, score_0_100: 50 },
        gaps: { normalized: 0.5, score_0_100: 50 },
        reporting: { normalized: 0.5, score_0_100: 50 },
      },
    });

    render(<BoardReadinessCard tenantId="t-x" />);

    await waitFor(() => {
      expect(screen.getByTestId("board-readiness-level-label").textContent).toBe(deLabel);
    });
    const el = screen.getByTestId("board-readiness-level-label");
    expect(el.getAttribute("title")).toBe(getReadinessCopy(level).levelWithRegTooltip);
  });

  it("shows demo banner copy for demo tenants (static readiness)", () => {
    render(
      <BoardReadinessCard
        tenantId="t-demo"
        isDemoTenant
        staticReadiness={{
          tenant_id: "t-demo",
          score: 40,
          level: "basic",
          interpretation: "Demo.",
          dimensions: {
            setup: { normalized: 0.4, score_0_100: 40 },
            coverage: { normalized: 0.4, score_0_100: 40 },
            kpi: { normalized: 0.4, score_0_100: 40 },
            gaps: { normalized: 0.4, score_0_100: 40 },
            reporting: { normalized: 0.4, score_0_100: 40 },
          },
        }}
      />,
    );

    expect(screen.getByText(DEMO_HINT_READINESS_CARD)).toBeTruthy();
    const card = screen.getByTestId("board-readiness-card");
    expect(card.textContent).toContain(READINESS_PRODUCT_TITLE);
  });
});

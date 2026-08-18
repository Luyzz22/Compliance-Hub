import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  cleanup();
});

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
];

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    postCrossRegulationLlmGapAssistant: vi.fn().mockResolvedValue({
      tenant_id: "t1",
      gap_count_used: 3,
      suggestions: [
        {
          requirement_ids: [1],
          frameworks: ["eu_ai_act"],
          recommendation_type: "new_control",
          suggested_control_name: "KI-Risikoprozess",
          suggested_control_description: "Dokumentierter Prozess gemäß Art. 9 EU AI Act.",
          rationale: "Pflichten mit hoher Kritikalität ohne vollständige Deckung.",
          priority: "hoch",
          suggested_owner_role: "CISO",
          suggested_actions: ["Workshop planen"],
        },
      ],
    }),
  };
});

import { CrossRegulationLlmGapPanel } from "./CrossRegulationLlmGapPanel";

describe("CrossRegulationLlmGapPanel", () => {
  it("blendet Vorschläge nach Mock-API ein", async () => {
    render(<CrossRegulationLlmGapPanel tenantId="t1" requirements={requirements} />);
    fireEvent.click(screen.getByTestId("llm-gap-analyze"));
    await waitFor(() => {
      expect(screen.getByTestId("llm-gap-suggestions")).toBeTruthy();
    });
    expect(screen.getByText("KI-Risikoprozess")).toBeTruthy();
  });
});

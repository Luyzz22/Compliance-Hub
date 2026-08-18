import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/workspaceTenantServer", () => ({
  getWorkspaceTenantIdServer: async () => "ags-page-tenant",
}));

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featureAiGovernanceSetupWizard: () => true,
    featureAiKpiKri: () => true,
    featureCrossRegulationDashboard: () => true,
    featureCrossRegulationLlmAssist: () => false,
    featureAiComplianceBoardReport: () => true,
  };
});

vi.mock("@/lib/api", () => ({
  fetchTenantAiGovernanceSetup: vi.fn().mockResolvedValue({
    tenant_id: "ags-page-tenant",
    tenant_kind: null,
    compliance_scopes: [],
    governance_roles: {},
    active_frameworks: [],
    steps_marked_complete: [],
    flags: {},
    progress_steps: [],
  }),
}));

import AiGovernanceSetupPage from "./page";

describe("AiGovernanceSetupPage", () => {
  it("lädt Setup und rendert den Wizard", async () => {
    const node = await AiGovernanceSetupPage();
    render(node);

    expect(screen.getByTestId("ai-governance-setup-wizard")).toBeTruthy();
    expect(screen.getByTestId("wizard-step-1")).toBeTruthy();
  });
});

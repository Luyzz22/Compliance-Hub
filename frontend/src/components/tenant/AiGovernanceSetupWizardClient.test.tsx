import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { TenantAiGovernanceSetupDto } from "@/lib/api";

import { AiGovernanceSetupWizardClient } from "./AiGovernanceSetupWizardClient";

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featureAiKpiKri: () => true,
    featureCrossRegulationDashboard: () => true,
    featureCrossRegulationLlmAssist: () => false,
    featureAiComplianceBoardReport: () => true,
  };
});

vi.mock("@/hooks/useWorkspaceTenantMeta", () => ({
  useWorkspaceTenantMeta: () => ({
    meta: null,
    loading: false,
    error: null,
    mutationBlocked: false,
    isDemoTenant: false,
    isPlaygroundTenant: false,
    refetch: vi.fn(),
  }),
}));

describe("AiGovernanceSetupWizardClient", () => {
  const initial: TenantAiGovernanceSetupDto = {
    tenant_id: "wizard-tenant-1",
    tenant_kind: null,
    compliance_scopes: [],
    governance_roles: {},
    active_frameworks: [],
    steps_marked_complete: [],
    flags: {},
    progress_steps: [],
  };

  it("rendert Wizard mit Schritt 1 und Stepper", () => {
    render(<AiGovernanceSetupWizardClient tenantId="wizard-tenant-1" initialSetup={initial} />);

    expect(screen.getByTestId("ai-governance-setup-wizard")).toBeTruthy();
    expect(screen.getByTestId("wizard-stepper")).toBeTruthy();
    expect(screen.getByTestId("wizard-step-1")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /AI Governance Setup/i })).toBeTruthy();
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { postDemoTenantSeed, fetchDemoTenantTemplates } = vi.hoisted(() => ({
  postDemoTenantSeed: vi.fn(),
  fetchDemoTenantTemplates: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  fetchDemoTenantTemplates,
  postDemoTenantSeed,
}));

vi.mock("@/lib/workspaceTenantClient", () => ({
  openWorkspaceTenantAndGoComplianceOverview: vi.fn(),
}));

import { DemoTenantSetupPanel } from "./DemoTenantSetupPanel";

const oneTemplate = [
  {
    key: "kritis_energy",
    name: "KRITIS-Energieversorger",
    description: "Demo-Szenario.",
    industry: "Energie",
    segment: "KRITIS",
    country: "DE",
    nis2_scope: true,
    ai_act_high_risk_focus: true,
  },
];

describe("DemoTenantSetupPanel", () => {
  it("loads templates and calls postDemoTenantSeed with tenant id", async () => {
    fetchDemoTenantTemplates.mockResolvedValue(oneTemplate);
    postDemoTenantSeed.mockResolvedValue({
      template_key: "kritis_energy",
      tenant_id: "demo-x",
      ai_systems_count: 4,
      governance_actions_count: 5,
      evidence_files_count: 3,
      nis2_kpi_rows_count: 6,
      policy_rows_count: 4,
      classifications_count: 4,
      advisor_linked: false,
    });

    render(<DemoTenantSetupPanel defaultTenantId="demo-x" />);

    await waitFor(() => {
      expect(fetchDemoTenantTemplates).toHaveBeenCalled();
    });

    expect(screen.getByRole("button", { name: /Demo-Daten einspielen/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Demo-Daten einspielen/i }));

    await waitFor(() => {
      expect(postDemoTenantSeed).toHaveBeenCalledWith({
        template_key: "kritis_energy",
        tenant_id: "demo-x",
        advisor_id: undefined,
      });
    });

    expect(await screen.findByText(/Demo-Setup abgeschlossen/i)).toBeTruthy();
  });
});

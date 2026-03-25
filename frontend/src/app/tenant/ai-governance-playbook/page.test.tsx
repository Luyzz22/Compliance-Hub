import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/workspaceTenantServer", () => ({
  getWorkspaceTenantIdServer: async () => "playbook-tenant-1",
}));

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featureAiGovernancePlaybook: () => true,
    featureAiGovernanceSetupWizard: () => true,
    featureCrossRegulationDashboard: () => true,
  };
});

import AiGovernancePlaybookPage from "./page";

describe("AiGovernancePlaybookPage", () => {
  it("zeigt RACI, Phasenplan und Deep-Links wenn Feature aktiv ist", async () => {
    const node = await AiGovernancePlaybookPage();
    render(node);

    expect(screen.getByRole("heading", { name: /AI Governance Playbook/i })).toBeTruthy();
    expect(screen.getByTestId("playbook-raci")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Governance-Rollen.*RACI/i })).toBeTruthy();
    expect(screen.getByTestId("playbook-phases")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Phasenplan/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Frameworks konsolidieren/i })).toBeTruthy();

    expect(screen.getByText(/playbook-tenant-1/)).toBeTruthy();

    expect(
      screen.getByRole("link", { name: /AI-Systeme importieren/i }).getAttribute("href"),
    ).toBe("/tenant/ai-systems");
    expect(
      screen.getByRole("link", { name: /Readiness-Dashboard prüfen/i }).getAttribute("href"),
    ).toBe("/board/eu-ai-act-readiness");
    expect(screen.getByRole("link", { name: /Kern-Policies anlegen/i }).getAttribute("href")).toBe(
      "/tenant/policies",
    );

    const pilotLinks = screen.getAllByTestId("playbook-pilot-link");
    expect(pilotLinks.length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByRole("link", { name: /Compliance-Übersicht \/ Setup/i }).getAttribute("href"),
    ).toBe("/tenant/compliance-overview");

    expect(screen.getByTestId("playbook-setup-wizard-cta")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /Jetzt geführtes Setup starten/i }).getAttribute("href"),
    ).toBe("/tenant/ai-governance-setup");
  });
});

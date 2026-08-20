import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { postDemoAzureGovernanceBrief } from "@/lib/api";

import { DemoAzureGovernanceBriefPanel } from "./DemoAzureGovernanceBriefPanel";

vi.mock("@/lib/api", () => ({
  postDemoAzureGovernanceBrief: vi.fn(),
}));

const postBrief = vi.mocked(postDemoAzureGovernanceBrief);

describe("DemoAzureGovernanceBriefPanel", () => {
  afterEach(cleanup);

  beforeEach(() => {
    postBrief.mockReset();
  });

  it("sendet nur das ausgewählte feste Szenario und zeigt den Human-Review-Vertrag", async () => {
    postBrief.mockResolvedValue({
      scenario: "supplier_risk",
      provider: "azure_openai",
      model_id: "gpt-enterprise",
      title: "Synthetisches Lieferanten-Briefing",
      executive_summary:
        "Das ausschließlich synthetische Szenario benötigt vor einer Freigabe belastbare Nachweise.",
      recommended_actions: [
        "Ausstiegsverfahren fachlich prüfen",
        "Unterauftragnehmer nachvollziehbar bestätigen",
        "Änderungskontrolle dokumentiert freigeben",
      ],
      human_review_note: "Eine Fachperson muss den Entwurf vor jeder Verwendung prüfen.",
      input_tokens_est: 41,
      output_tokens_est: 72,
      data_class: "public",
      synthetic_data_only: true,
    });
    render(<DemoAzureGovernanceBriefPanel tenantId="demo-tenant-1" />);

    fireEvent.click(screen.getByRole("button", { name: /Lieferantenrisiko/i }));
    fireEvent.click(screen.getByRole("button", { name: /Executive Briefing erzeugen/i }));

    await waitFor(() => {
      expect(postBrief).toHaveBeenCalledWith("demo-tenant-1", "supplier_risk");
    });
    expect(await screen.findByText("Synthetisches Lieferanten-Briefing")).toBeTruthy();
    expect(screen.getByText(/Fachprüfung offen/i)).toBeTruthy();
    expect(screen.getByText(/Synthetisch bestätigt/i)).toBeTruthy();
  });

  it("kommuniziert Providerfehler ohne einen stillen Fallback", async () => {
    postBrief.mockRejectedValue(new Error("Azure-Demopfad nicht verfügbar."));
    render(<DemoAzureGovernanceBriefPanel tenantId="demo-tenant-2" />);

    fireEvent.click(screen.getByRole("button", { name: /Executive Briefing erzeugen/i }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Azure-Demopfad nicht verfügbar.",
    );
    expect(screen.queryByText(/Synthetisch bestätigt/i)).toBeNull();
  });

  it("unterstützt die feste Szenarioauswahl per Tastatur", () => {
    render(<DemoAzureGovernanceBriefPanel tenantId="demo-tenant-3" />);
    const incident = screen.getByRole("button", { name: /Incident Readiness/i });

    fireEvent.keyDown(incident, { key: "Enter" });

    expect(incident.getAttribute("aria-pressed")).toBe("true");
  });
});

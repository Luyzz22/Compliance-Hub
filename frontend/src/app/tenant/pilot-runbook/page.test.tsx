import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/workspaceTenantServer", () => ({
  getWorkspaceTenantIdServer: async () => "pilot-tenant-x",
}));

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featurePilotRunbook: () => true,
  };
});

import PilotRunbookPage from "./page";

describe("PilotRunbookPage", () => {
  it("rendert Zielbild und Wochenplan", async () => {
    const node = await PilotRunbookPage();
    render(node);
    expect(screen.getByRole("heading", { name: /Pilot-Runbook/i })).toBeTruthy();
    expect(screen.getByText(/pilot-tenant-x/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Zielbild/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Wochenplan/i })).toBeTruthy();
  });
});

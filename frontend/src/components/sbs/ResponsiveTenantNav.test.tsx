import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/sbs/TenantNav", () => ({
  TenantNav: ({ workspaceTenantId }: { workspaceTenantId: string }) => (
    <nav>{workspaceTenantId}</nav>
  ),
}));

import { ResponsiveTenantNav } from "./ResponsiveTenantNav";

describe("ResponsiveTenantNav", () => {
  it("ist mobil zunächst kompakt und exponiert einen kontrollierten Bereich", () => {
    render(<ResponsiveTenantNav workspaceTenantId="tenant-dach" />);

    const button = screen.getByRole("button", { name: "Workspace-Bereiche" });
    const controlledId = button.getAttribute("aria-controls");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(controlledId).toBeTruthy();
    expect(document.getElementById(controlledId ?? "")?.className).toContain("hidden");

    fireEvent.click(button);

    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(document.getElementById(controlledId ?? "")?.className).toContain("block");
    expect(screen.getByRole("navigation").textContent).toBe("tenant-dach");
  });
});

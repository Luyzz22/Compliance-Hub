import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceShellModeBanner } from "./WorkspaceShellModeBanner";

const mockUse = vi.fn();

vi.mock("@/hooks/useWorkspaceMode", () => ({
  useWorkspaceMode: () => mockUse(),
}));

describe("WorkspaceShellModeBanner", () => {
  it("rendert nichts für production", () => {
    mockUse.mockReturnValue({
      loading: false,
      workspaceMode: "production",
      modeLabel: "Produktiv",
      modeHint: "x",
      docsUrl: "",
    });
    const { container } = render(<WorkspaceShellModeBanner tenantId="t1" />);
    expect(container.firstChild).toBeNull();
  });

  it("zeigt Demo-Banner mit Doku-Link", () => {
    mockUse.mockReturnValue({
      loading: false,
      workspaceMode: "demo",
      modeLabel: "Demo (read-only)",
      modeHint: "Keine Schreibzugriffe.",
      docsUrl: "https://internal.example/demo.md",
    });
    render(<WorkspaceShellModeBanner tenantId="t1" />);
    const el = screen.getByTestId("workspace-shell-mode-banner");
    expect(el.textContent).toContain("Demo (read-only)");
    const a = screen.getByRole("link", { name: "Technische Doku" });
    expect(a.getAttribute("href")).toBe("https://internal.example/demo.md");
  });
});

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DemoWorkspaceBadge } from "./DemoWorkspaceBadge";

const mockUse = vi.fn();

vi.mock("@/hooks/useWorkspaceMode", () => ({
  useWorkspaceMode: () => mockUse(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("DemoWorkspaceBadge", () => {
  it("rendert nichts wenn nicht Demo-Mandant", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: false,
      modeLabel: "",
      modeHint: "",
    });
    const { container } = render(<DemoWorkspaceBadge tenantId="t1" />);
    expect(container.firstChild).toBeNull();
  });

  it("zeigt mode_label aus Workspace-Meta", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: true,
      modeLabel: "Demo (schreibgeschützt)",
      modeHint: "Kurzer Hinweis",
    });
    render(<DemoWorkspaceBadge tenantId="t1" />);
    expect(screen.getByText("Demo (schreibgeschützt)")).toBeTruthy();
  });

  it("zeigt Playground-Label", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: true,
      modeLabel: "Playground",
      modeHint: "Sandbox",
    });
    render(<DemoWorkspaceBadge tenantId="t1" />);
    expect(screen.getByText("Playground")).toBeTruthy();
  });
});

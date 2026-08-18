import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/workspaceTenantServer", () => ({
  getWorkspaceTenantIdServer: async () => "session-tenant",
}));

vi.mock("@/components/demo/DemoWorkspaceBadge", () => ({
  DemoWorkspaceBadge: () => null,
}));

vi.mock("@/components/sbs/ResponsiveTenantNav", () => ({
  ResponsiveTenantNav: ({ workspaceTenantId }: { workspaceTenantId: string }) => (
    <nav data-testid="tenant-nav">{workspaceTenantId}</nav>
  ),
}));

vi.mock("@/components/workspace/TenantWorkspaceShell", () => ({
  TenantWorkspaceShell: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
}));

import TenantLayout from "./layout";

describe("TenantLayout", () => {
  it("bindet die responsive Navigation an den aktiven Workspace", async () => {
    render(await TenantLayout({ children: <div>Arbeitsinhalt</div> }));

    expect(screen.getByTestId("tenant-nav").textContent).toBe("session-tenant");
    expect(screen.getByText("Arbeitsinhalt")).toBeTruthy();
  });
});

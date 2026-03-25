import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DemoWorkspaceBadge } from "./DemoWorkspaceBadge";

const mockUse = vi.fn();

vi.mock("@/hooks/useWorkspaceTenantMeta", () => ({
  useWorkspaceTenantMeta: () => mockUse(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("DemoWorkspaceBadge", () => {
  it("rendert nichts wenn nicht Demo-Mandant", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: false,
      isPlaygroundTenant: false,
      mutationBlocked: false,
    });
    const { container } = render(<DemoWorkspaceBadge tenantId="t1" />);
    expect(container.firstChild).toBeNull();
  });

  it("blendet Demo-Label und read-only-Hinweis ein", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: true,
      isPlaygroundTenant: false,
      mutationBlocked: true,
    });
    render(<DemoWorkspaceBadge tenantId="t1" />);
    const badge = screen.getByText(/Demo/i);
    expect(badge.textContent).toMatch(/read-only/i);
  });

  it("zeigt Playground statt Demo wenn demo_playground", () => {
    mockUse.mockReturnValue({
      loading: false,
      isDemoTenant: true,
      isPlaygroundTenant: true,
      mutationBlocked: false,
    });
    render(<DemoWorkspaceBadge tenantId="t1" />);
    expect(screen.getByText(/Playground/i)).toBeTruthy();
  });
});

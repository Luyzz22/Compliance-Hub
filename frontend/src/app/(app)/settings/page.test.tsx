import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/usage/TenantUsageSummary", () => ({
  TenantUsageSummary: () => <div data-testid="usage" />,
}));

vi.mock("@/components/demo/DemoTenantSetupPanel", () => ({
  DemoTenantSetupPanel: () => null,
}));

vi.mock("@/components/settings/TenantApiKeysPanel", () => ({
  TenantApiKeysPanel: ({ tenantId }: { tenantId: string }) => (
    <div data-testid="api-keys-panel">{tenantId}</div>
  ),
}));

vi.mock("@/lib/workspaceTenantServer", () => ({
  getWorkspaceTenantIdServer: async () => "tenant-overview-001",
}));

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featureDemoSeeding: () => false,
    featureApiKeysUi: () => true,
  };
});

describe("SettingsPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("zeigt API-Keys-Bereich wenn NEXT_PUBLIC_FEATURE_API_KEYS_UI aktiv ist", async () => {
    const Page = (await import("./page")).default;
    const tree = await Page();
    render(tree);
    const panel = screen.getByTestId("api-keys-panel");
    expect(panel.textContent ?? "").toContain("tenant-overview-001");
  });
});

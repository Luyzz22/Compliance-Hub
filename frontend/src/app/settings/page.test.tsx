import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

vi.mock("@/lib/config", async () => {
  const actual = await vi.importActual<typeof import("@/lib/config")>("@/lib/config");
  return {
    ...actual,
    featureDemoSeeding: () => false,
    featureApiKeysUi: () => true,
  };
});

import SettingsPage from "./page";

describe("SettingsPage", () => {
  it("zeigt API-Keys-Bereich wenn NEXT_PUBLIC_FEATURE_API_KEYS_UI aktiv ist", () => {
    render(<SettingsPage />);
    const panel = screen.getByTestId("api-keys-panel");
    expect(panel.textContent ?? "").toContain("tenant-overview-001");
  });
});

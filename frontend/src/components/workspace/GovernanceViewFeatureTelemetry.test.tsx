import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TenantWorkspaceMetaDto } from "@/lib/api";
import { resetWorkspaceTelemetryDebounceForTests } from "@/lib/workspaceTelemetry";

const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

const metaProd: TenantWorkspaceMetaDto = {
  tenant_id: "t1",
  display_name: "Acme",
  is_demo: false,
  demo_playground: false,
  mutation_blocked: false,
  workspace_mode: "production",
  mode_label: "Produktiv",
  mode_hint: "OK",
  demo_mode_feature_enabled: false,
};

const mockUseWorkspaceMode = vi.fn();

vi.mock("@/hooks/useWorkspaceMode", () => ({
  useWorkspaceMode: (tid: string) => mockUseWorkspaceMode(tid),
}));

import { GovernanceViewFeatureTelemetry } from "./GovernanceViewFeatureTelemetry";

beforeEach(() => {
  resetWorkspaceTelemetryDebounceForTests();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.clearAllMocks();
  fetchMock.mockClear();
  mockUseWorkspaceMode.mockReset();
  vi.unstubAllGlobals();
});

describe("GovernanceViewFeatureTelemetry", () => {
  it("sendet kein Event solange Meta lädt", () => {
    mockUseWorkspaceMode.mockReturnValue({
      loading: true,
      meta: null,
      workspaceMode: "production",
    });
    render(
      <GovernanceViewFeatureTelemetry
        tenantId="t1"
        featureName="playbook_overview"
        routeName="/tenant/ai-governance-playbook"
      />,
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sendet genau ein Event nach geladenem Meta", async () => {
    mockUseWorkspaceMode.mockReturnValue({
      loading: false,
      meta: metaProd,
      workspaceMode: "production",
    });
    const { rerender } = render(
      <GovernanceViewFeatureTelemetry
        tenantId="t1"
        featureName="playbook_overview"
        routeName="/tenant/ai-governance-playbook"
      />,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    rerender(
      <GovernanceViewFeatureTelemetry
        tenantId="t1"
        featureName="playbook_overview"
        routeName="/tenant/ai-governance-playbook"
      />,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });
});

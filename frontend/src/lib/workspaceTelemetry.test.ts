import { afterEach, describe, expect, it, vi } from "vitest";

import { resetWorkspaceTelemetryDebounceForTests, trackWorkspaceFeatureUsed } from "./workspaceTelemetry";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  resetWorkspaceTelemetryDebounceForTests();
});

describe("trackWorkspaceFeatureUsed", () => {
  it("POSTet nur Whitelist-Felder an den Proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await trackWorkspaceFeatureUsed({
      tenantId: "tenant-a",
      workspaceMode: "demo",
      featureName: "playbook_overview",
      routeName: "/tenant/ai-governance-playbook",
      frameworkKey: "EU_AI_ACT",
      aiSystemId: "sys-1",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workspace/feature-used");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      tenant_id: "tenant-a",
      workspace_mode: "demo",
      feature_name: "playbook_overview",
      route_name: "/tenant/ai-governance-playbook",
      framework_key: "EU_AI_ACT",
      ai_system_id: "sys-1",
    });
    expect(body).not.toHaveProperty("user_name");
    expect(body).not.toHaveProperty("owner_email");
    expect(body).not.toHaveProperty("free_text");
  });

  it("wirft clientseitig keine Fehler bei Netzwerkfehler", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network")));
    await expect(
      trackWorkspaceFeatureUsed({
        tenantId: "t1",
        workspaceMode: "production",
        featureName: "cross_regulation_summary",
        routeName: "/tenant/cross-regulation-dashboard",
      }),
    ).resolves.toBeUndefined();
  });
});

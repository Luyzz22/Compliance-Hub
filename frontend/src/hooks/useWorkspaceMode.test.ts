import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchTenantWorkspaceMeta } from "@/lib/api";

import { useWorkspaceMode } from "./useWorkspaceMode";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchTenantWorkspaceMeta: vi.fn(),
  };
});

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
});

describe("useWorkspaceMode", () => {
  it("leitet workspaceMode und mutationsBlocked aus Meta ab", async () => {
    vi.mocked(fetchTenantWorkspaceMeta).mockResolvedValue({
      tenant_id: "t1",
      display_name: "X",
      is_demo: true,
      demo_playground: false,
      mutation_blocked: true,
      workspace_mode: "demo",
      mode_label: "Demo RO",
      mode_hint: "Hint",
      demo_mode_feature_enabled: true,
    });

    const { result } = renderHook(() => useWorkspaceMode("t1"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.workspaceMode).toBe("demo");
    expect(result.current.mutationsBlocked).toBe(true);
    expect(result.current.modeLabel).toBe("Demo RO");
    expect(result.current.isDemo).toBe(true);
    expect(result.current.isPlaygroundWritable).toBe(false);
  });

  it("exponiert docsUrl aus NEXT_PUBLIC_WORKSPACE_MODE_DOCS_URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_WORKSPACE_MODE_DOCS_URL", "https://example.com/docs");
    vi.mocked(fetchTenantWorkspaceMeta).mockResolvedValue({
      tenant_id: "t1",
      display_name: "X",
      is_demo: false,
      demo_playground: false,
      mutation_blocked: false,
      workspace_mode: "production",
      mode_label: "Produktiv",
      mode_hint: "OK",
      demo_mode_feature_enabled: false,
    });

    const { result } = renderHook(() => useWorkspaceMode("t1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.docsUrl).toBe("https://example.com/docs");
  });
});

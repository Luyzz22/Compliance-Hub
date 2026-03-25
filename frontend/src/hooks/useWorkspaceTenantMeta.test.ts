import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchTenantWorkspaceMeta } from "@/lib/api";

import { useWorkspaceTenantMeta } from "./useWorkspaceTenantMeta";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchTenantWorkspaceMeta: vi.fn(),
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useWorkspaceTenantMeta", () => {
  it("mapped mutation_blocked und Demo-Flags aus der API", async () => {
    vi.mocked(fetchTenantWorkspaceMeta).mockResolvedValue({
      tenant_id: "tid-1",
      display_name: "D",
      is_demo: true,
      demo_playground: false,
      mutation_blocked: true,
      demo_mode_feature_enabled: true,
    });

    const { result } = renderHook(() => useWorkspaceTenantMeta("tid-1"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.mutationBlocked).toBe(true);
    expect(result.current.isDemoTenant).toBe(true);
    expect(result.current.isPlaygroundTenant).toBe(false);
    expect(result.current.meta?.tenant_id).toBe("tid-1");
  });

  it("bleibt leer ohne tenantId", () => {
    const { result } = renderHook(() => useWorkspaceTenantMeta(""));
    expect(result.current.loading).toBe(false);
    expect(result.current.meta).toBeNull();
    expect(fetchTenantWorkspaceMeta).not.toHaveBeenCalled();
  });
});

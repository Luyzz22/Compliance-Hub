import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";

describe("useFeatureGate", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
    process.env.NEXT_PUBLIC_API_KEY = "test-key";
    process.env.NEXT_PUBLIC_TENANT_ID = "test-tenant";
    // Prevent actual network calls from the useEffect
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 402 })),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    process.env = { ...originalEnv };
  });

  async function loadHook() {
    const mod = await import("./useFeatureGate");
    return mod;
  }

  it("exports NAV_FEATURE_GATES with expected gated paths", async () => {
    const { NAV_FEATURE_GATES } = await loadHook();
    expect(NAV_FEATURE_GATES).toHaveProperty("/board/datev-export");
    expect(NAV_FEATURE_GATES).toHaveProperty("/board/xrechnung-export");
    expect(NAV_FEATURE_GATES).toHaveProperty("/board/gap-analysis");
    expect(NAV_FEATURE_GATES["/board/datev-export"].feature).toBe("datev_export");
    expect(NAV_FEATURE_GATES["/board/datev-export"].requiredPlan).toBe("Professional");
  });

  it("isGated returns true for gated paths in initial state (fail-closed)", async () => {
    const { useFeatureGate } = await loadHook();
    const { result } = renderHook(() => useFeatureGate());
    expect(result.current.isGated("/board/datev-export")).toBe(true);
    expect(result.current.isGated("/board/xrechnung-export")).toBe(true);
    expect(result.current.isGated("/board/gap-analysis")).toBe(true);
  });

  it("isGated returns false for non-gated paths", async () => {
    const { useFeatureGate } = await loadHook();
    const { result } = renderHook(() => useFeatureGate());
    expect(result.current.isGated("/board/overview")).toBe(false);
    expect(result.current.isGated("/settings")).toBe(false);
    expect(result.current.isGated("/")).toBe(false);
  });

  it("requiredPlanLabel returns correct labels for gated paths", async () => {
    const { useFeatureGate } = await loadHook();
    const { result } = renderHook(() => useFeatureGate());
    expect(result.current.requiredPlanLabel("/board/datev-export")).toBe("Professional");
    expect(result.current.requiredPlanLabel("/board/xrechnung-export")).toBe("Enterprise");
    expect(result.current.requiredPlanLabel("/board/gap-analysis")).toBe("Professional");
  });

  it("requiredPlanLabel defaults to Professional for unknown paths", async () => {
    const { useFeatureGate } = await loadHook();
    const { result } = renderHook(() => useFeatureGate());
    expect(result.current.requiredPlanLabel("/unknown")).toBe("Professional");
  });
});

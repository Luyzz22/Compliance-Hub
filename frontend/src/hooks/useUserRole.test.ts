import { describe, expect, it, vi, afterEach } from "vitest";

// We test the exported RBAC helpers directly – the hook is thin enough
// that we can just assert the logic with different env values.

describe("useUserRole RBAC helpers", () => {
  const originalEnv = process.env.NEXT_PUBLIC_OPA_USER_ROLE;

  afterEach(() => {
    vi.resetModules();
    if (originalEnv === undefined) {
      delete process.env.NEXT_PUBLIC_OPA_USER_ROLE;
    } else {
      process.env.NEXT_PUBLIC_OPA_USER_ROLE = originalEnv;
    }
  });

  async function loadHelpers() {
    // Dynamic import to pick up changed env var
    const mod = await import("./useUserRole");
    return mod;
  }

  it("shows admin for tenant_admin", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "tenant_admin";
    const { useCanSeeAdmin } = await loadHelpers();
    expect(useCanSeeAdmin()).toBe(true);
  });

  it("hides admin for viewer", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "viewer";
    const { useCanSeeAdmin } = await loadHelpers();
    expect(useCanSeeAdmin()).toBe(false);
  });

  it("shows reporting for board_member", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "board_member";
    const { useCanSeeReporting } = await loadHelpers();
    expect(useCanSeeReporting()).toBe(true);
  });

  it("hides reporting for viewer", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "viewer";
    const { useCanSeeReporting } = await loadHelpers();
    expect(useCanSeeReporting()).toBe(false);
  });

  it("hides everything when no role is set (fail-closed / SSR safe)", async () => {
    delete process.env.NEXT_PUBLIC_OPA_USER_ROLE;
    const { useCanSeeAdmin, useCanSeeReporting, useCanSeeAiSystems } =
      await loadHelpers();
    expect(useCanSeeAdmin()).toBe(false);
    expect(useCanSeeReporting()).toBe(false);
    expect(useCanSeeAiSystems()).toBe(false);
  });

  it("hides AI systems for viewer", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "viewer";
    const { useCanSeeAiSystems } = await loadHelpers();
    expect(useCanSeeAiSystems()).toBe(false);
  });

  it("shows AI systems for ciso", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "ciso";
    const { useCanSeeAiSystems } = await loadHelpers();
    expect(useCanSeeAiSystems()).toBe(true);
  });

  it("board_member sees reporting but not admin", async () => {
    process.env.NEXT_PUBLIC_OPA_USER_ROLE = "board_member";
    const { useCanSeeAdmin, useCanSeeReporting } = await loadHelpers();
    expect(useCanSeeReporting()).toBe(true);
    expect(useCanSeeAdmin()).toBe(false);
  });
});

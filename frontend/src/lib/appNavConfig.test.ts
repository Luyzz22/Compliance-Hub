import { describe, expect, it } from "vitest";

import {
  ADMIN_NAV_ITEMS,
  AUTH_NAV_ITEMS,
  BOARD_NAV_ITEMS,
  BRAND_TAGLINE,
  REPORTING_NAV_ITEMS,
  WORKSPACE_NAV_ITEMS,
} from "./appNavConfig";

describe("appNavConfig", () => {
  it("exports BOARD_NAV_ITEMS with expected structure", () => {
    expect(BOARD_NAV_ITEMS.length).toBeGreaterThanOrEqual(6);
    for (const item of BOARD_NAV_ITEMS) {
      expect(item.href).toMatch(/^\/board\//);
      expect(item.label.length).toBeGreaterThan(0);
    }
  });

  it("exports WORKSPACE_NAV_ITEMS with expected structure", () => {
    expect(WORKSPACE_NAV_ITEMS.length).toBeGreaterThanOrEqual(7);
    for (const item of WORKSPACE_NAV_ITEMS) {
      expect(item.href).toMatch(/^\/tenant\//);
      expect(item.label.length).toBeGreaterThan(0);
    }
  });

  it("exports REPORTING_NAV_ITEMS covering enterprise modules", () => {
    expect(REPORTING_NAV_ITEMS.length).toBeGreaterThanOrEqual(5);
    const hrefs = REPORTING_NAV_ITEMS.map((i) => i.href);
    expect(hrefs).toContain("/board/executive-dashboard");
    expect(hrefs).toContain("/board/gap-analysis");
    expect(hrefs).toContain("/board/datev-export");
  });

  it("exports ADMIN_NAV_ITEMS with admin paths", () => {
    expect(ADMIN_NAV_ITEMS.length).toBeGreaterThanOrEqual(4);
    for (const item of ADMIN_NAV_ITEMS) {
      expect(item.href).toMatch(/^\/admin\//);
    }
  });

  it("exports AUTH_NAV_ITEMS with auth paths", () => {
    expect(AUTH_NAV_ITEMS.length).toBeGreaterThanOrEqual(2);
    const hrefs = AUTH_NAV_ITEMS.map((i) => i.href);
    expect(hrefs).toContain("/auth/login");
    expect(hrefs).toContain("/auth/register");
  });

  it("has no duplicate hrefs across all nav groups", () => {
    const allHrefs = [
      ...BOARD_NAV_ITEMS,
      ...WORKSPACE_NAV_ITEMS,
      ...REPORTING_NAV_ITEMS,
      ...ADMIN_NAV_ITEMS,
      ...AUTH_NAV_ITEMS,
    ].map((i) => i.href);
    const unique = new Set(allHrefs);
    expect(unique.size).toBe(allHrefs.length);
  });

  it("exports BRAND_TAGLINE", () => {
    expect(BRAND_TAGLINE).toContain("GRC");
  });
});

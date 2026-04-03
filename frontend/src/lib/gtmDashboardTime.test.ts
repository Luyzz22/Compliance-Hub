import { describe, expect, it } from "vitest";

import {
  isoInWindow,
  utcDayKeyFromMs,
  utcWeekStartMondayFromMs,
  windowBoundsMs,
} from "@/lib/gtmDashboardTime";

describe("gtmDashboardTime", () => {
  it("windowBoundsMs spans correct length", () => {
    const now = 1_700_000_000_000;
    const w = windowBoundsMs(7, now);
    expect(w.end - w.start).toBe(7 * 24 * 60 * 60 * 1000);
  });

  it("isoInWindow respects bounds", () => {
    const start = Date.parse("2026-04-01T00:00:00.000Z");
    const end = Date.parse("2026-04-10T23:59:59.999Z");
    expect(isoInWindow("2026-04-05T12:00:00.000Z", start, end)).toBe(true);
    expect(isoInWindow("2026-03-01T12:00:00.000Z", start, end)).toBe(false);
  });

  it("utcDayKeyFromMs", () => {
    expect(utcDayKeyFromMs(Date.parse("2026-06-15T14:00:00.000Z"))).toBe("2026-06-15");
  });

  it("utcWeekStartMondayFromMs returns Monday UTC", () => {
    const wed = Date.parse("2026-04-01T12:00:00.000Z");
    expect(utcWeekStartMondayFromMs(wed)).toBe("2026-03-30");
  });
});

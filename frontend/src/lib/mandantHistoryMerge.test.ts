import { describe, expect, it } from "vitest";

import {
  daysSinceValidIso,
  isNonEmptyUnparsableIso,
  maxIsoTimestamps,
} from "@/lib/mandantHistoryMerge";

describe("mandantHistoryMerge", () => {
  it("maxIsoTimestamps picks later ISO timestamp", () => {
    expect(maxIsoTimestamps("2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z")).toBe("2026-06-01T00:00:00Z");
    expect(maxIsoTimestamps(null, "2026-01-01T00:00:00Z")).toBe("2026-01-01T00:00:00Z");
  });

  it("maxIsoTimestamps ignores invalid ISO and prefers parseable side", () => {
    expect(maxIsoTimestamps("2026-01-01T00:00:00Z", "not-a-date")).toBe("2026-01-01T00:00:00Z");
    expect(maxIsoTimestamps("not-a-date", "2026-01-01T00:00:00Z")).toBe("2026-01-01T00:00:00Z");
    expect(maxIsoTimestamps("also-bad", "not-a-date")).toBe(null);
  });

  it("isNonEmptyUnparsableIso detects legacy garbage", () => {
    expect(isNonEmptyUnparsableIso("")).toBe(false);
    expect(isNonEmptyUnparsableIso("   ")).toBe(false);
    expect(isNonEmptyUnparsableIso(null)).toBe(false);
    expect(isNonEmptyUnparsableIso("2026-01-01T00:00:00Z")).toBe(false);
    expect(isNonEmptyUnparsableIso("not-iso")).toBe(true);
  });

  it("daysSinceValidIso returns null for empty or unparsable", () => {
    const now = Date.parse("2026-06-15T12:00:00Z");
    expect(daysSinceValidIso("", now)).toBe(null);
    expect(daysSinceValidIso("garbage", now)).toBe(null);
    expect(daysSinceValidIso("2026-06-10T12:00:00Z", now)).toBe(5);
  });
});

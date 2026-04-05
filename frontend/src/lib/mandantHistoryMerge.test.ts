import { describe, expect, it } from "vitest";

import { maxIsoTimestamps } from "@/lib/mandantHistoryMerge";

describe("mandantHistoryMerge", () => {
  it("picks later ISO timestamp", () => {
    expect(maxIsoTimestamps("2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z")).toBe("2026-06-01T00:00:00Z");
    expect(maxIsoTimestamps(null, "2026-01-01T00:00:00Z")).toBe("2026-01-01T00:00:00Z");
  });
});

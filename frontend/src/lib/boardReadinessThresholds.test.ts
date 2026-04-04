import { describe, expect, it } from "vitest";

import { trafficFromRatio, worstTraffic } from "@/lib/boardReadinessThresholds";

describe("boardReadinessThresholds", () => {
  it("marks green at or above 0.75", () => {
    expect(trafficFromRatio(0.75)).toBe("green");
    expect(trafficFromRatio(0.9)).toBe("green");
  });

  it("marks red below 0.45", () => {
    expect(trafficFromRatio(0.44)).toBe("red");
    expect(trafficFromRatio(0)).toBe("red");
  });

  it("marks amber in the band", () => {
    expect(trafficFromRatio(0.5)).toBe("amber");
    expect(trafficFromRatio(0.74)).toBe("amber");
  });

  it("treats null ratio as amber", () => {
    expect(trafficFromRatio(null)).toBe("amber");
  });

  it("picks worst traffic", () => {
    expect(worstTraffic("green", "amber")).toBe("amber");
    expect(worstTraffic("amber", "red")).toBe("red");
    expect(worstTraffic("green", "green")).toBe("green");
  });
});

import { describe, expect, it } from "vitest";

import {
  getActivityCopy,
  getMonitoringCopy,
  getReadinessCopy,
  indexLevelLabelDe,
  parseIndexLevel,
  parseReadinessLevel,
  readinessLevelLabelDe,
  readinessPortfolioBadgeTooltip,
} from "./governanceMaturityDeCopy";

describe("governanceMaturityDeCopy helpers", () => {
  it("parses readiness API levels", () => {
    expect(parseReadinessLevel("basic")).toBe("basic");
    expect(parseReadinessLevel("MANAGED")).toBe("managed");
    expect(parseReadinessLevel("unknown")).toBeNull();
  });

  it("getReadinessCopy returns German labels", () => {
    expect(getReadinessCopy("basic").levelLabelDe).toBe("Basis");
    expect(getReadinessCopy("managed").levelLabelDe).toBe("Etabliert");
    expect(getReadinessCopy("embedded").levelLabelDe).toBe("Integriert");
  });

  it("readinessLevelLabelDe falls back for unknown", () => {
    expect(readinessLevelLabelDe("custom")).toBe("custom");
  });

  it("parses index levels for GAI/OAMI", () => {
    expect(parseIndexLevel("low")).toBe("low");
    expect(parseIndexLevel("HIGH")).toBe("high");
    expect(parseIndexLevel(null)).toBeNull();
  });

  it("getActivityCopy and getMonitoringCopy share index labels", () => {
    expect(getActivityCopy("medium").levelLabelDe).toBe("Mittel");
    expect(getMonitoringCopy("medium").levelLabelDe).toBe("Mittel");
    expect(getMonitoringCopy("high").fullName).toContain("OAMI");
  });

  it("indexLevelLabelDe handles empty and unknown", () => {
    expect(indexLevelLabelDe(null)).toBe("–");
    expect(indexLevelLabelDe("weird")).toBe("weird");
  });

  it("readinessPortfolioBadgeTooltip uses copy reg hint", () => {
    const t = readinessPortfolioBadgeTooltip("managed");
    expect(t).toContain("Etabliert");
    expect(t).toContain("0–100");
  });
});

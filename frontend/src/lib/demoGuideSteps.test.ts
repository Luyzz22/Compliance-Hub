import { describe, expect, it } from "vitest";

import { DEMO_GUIDE_STEPS, demoStepIndexForPath } from "./demoGuideSteps";

describe("demoStepIndexForPath", () => {
  it("matcht Board KPIs", () => {
    expect(demoStepIndexForPath("/board/kpis")).toBe(0);
  });

  it("matcht Hochrisiko-System-Detail unter Präfix ai-systems", () => {
    const idx = DEMO_GUIDE_STEPS.findIndex((s) => s.id === "highrisk");
    expect(demoStepIndexForPath("/tenant/ai-systems/sys-1")).toBe(idx);
  });
});

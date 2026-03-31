import { describe, expect, it } from "vitest";

import { portfolioHealth } from "./advisorPortfolioHealth";

describe("portfolioHealth", () => {
  it("marks critical below 0.5 readiness", () => {
    expect(portfolioHealth(0.49, 1)).toBe("critical");
  });

  it("marks attention for low readiness or setup", () => {
    expect(portfolioHealth(0.55, 0.9)).toBe("attention");
    expect(portfolioHealth(0.8, 0.4)).toBe("attention");
  });

  it("marks on track otherwise", () => {
    expect(portfolioHealth(0.8, 0.8)).toBe("on_track");
  });
});

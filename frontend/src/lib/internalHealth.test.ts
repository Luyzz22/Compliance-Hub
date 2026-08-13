import { describe, expect, it } from "vitest";

import { governanceServiceHealthHint, mapInternalHealthJson } from "./internalHealth";

describe("internal health policy signal", () => {
  it("maps the backend policy engine signal explicitly", () => {
    expect(
      mapInternalHealthJson({
        app: "up",
        db: "up",
        policy_engine: "degraded",
        external_ai_provider: "up",
        timestamp: "2026-08-12T12:00:00Z",
      }),
    ).toEqual({
      app: "up",
      db: "up",
      policyEngine: "degraded",
      externalAiProvider: "up",
      timestamp: "2026-08-12T12:00:00Z",
    });
  });

  it("raises an operational hint when policy decisions are unavailable", () => {
    const hint = governanceServiceHealthHint({
      app: "up",
      db: "up",
      policyEngine: "down",
      externalAiProvider: "up",
    });

    expect(hint).toContain("Policy-Entscheidungen");
    expect(hint).toContain("verantwortliche Betriebsrolle");
  });
});

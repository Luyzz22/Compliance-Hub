import { describe, expect, it } from "vitest";

import {
  csrfTokensMatch,
  hasAllowedMutationOrigin,
  parseLoginBody,
} from "./sessionSecurity";

describe("session security", () => {
  it("fails closed for missing, invalid, and cross-origin mutation origins", () => {
    expect(
      hasAllowedMutationOrigin(
        "https://complywithai.de/api/auth/login",
        null,
        "https://complywithai.de",
        true,
      ),
    ).toBe(false);
    expect(
      hasAllowedMutationOrigin(
        "https://complywithai.de/api/auth/login",
        "https://attacker.example",
        "https://complywithai.de",
        true,
      ),
    ).toBe(false);
    expect(
      hasAllowedMutationOrigin(
        "https://complywithai.de/api/auth/login",
        "https://complywithai.de",
        "https://complywithai.de",
        true,
      ),
    ).toBe(true);
  });

  it("requires configured origin in production and permits request origin locally", () => {
    expect(
      hasAllowedMutationOrigin(
        "http://localhost:3000/api/auth/login",
        "http://localhost:3000",
        undefined,
        false,
      ),
    ).toBe(true);
    expect(
      hasAllowedMutationOrigin(
        "https://complywithai.de/api/auth/login",
        "https://complywithai.de",
        undefined,
        true,
      ),
    ).toBe(false);
  });

  it("compares CSRF values and rejects malformed login input", () => {
    expect(csrfTokensMatch("secret", "secret")).toBe(true);
    expect(csrfTokensMatch("secret", "different")).toBe(false);
    expect(csrfTokensMatch(undefined, "secret")).toBe(false);
    expect(parseLoginBody("not-json")).toBeNull();
    expect(parseLoginBody(JSON.stringify({ email: "x@example.com" }))).toBeNull();
    expect(
      parseLoginBody(
        JSON.stringify({
          email: " person@example.com ",
          password: "Password123",
          tenant_id: " tenant-a ",
        }),
      ),
    ).toEqual({
      email: "person@example.com",
      password: "Password123",
      tenant_id: "tenant-a",
    });
  });
});

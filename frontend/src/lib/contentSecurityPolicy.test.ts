import { describe, expect, it } from "vitest";

import {
  buildContentSecurityPolicy,
  createCspNonce,
} from "@/lib/contentSecurityPolicy";

describe("content security policy", () => {
  it("builds a strict production policy without inline or eval bypasses", () => {
    const nonce = createCspNonce();
    const policy = buildContentSecurityPolicy({
      nonce,
      development: false,
      apiBaseUrl: "https://api.complywithai.de/v1",
    });

    expect(policy).toContain(`script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`);
    expect(policy).toContain(`style-src 'self' 'nonce-${nonce}'`);
    expect(policy).toContain("script-src-attr 'none'");
    expect(policy).toContain("style-src-attr 'none'");
    expect(policy).toContain("connect-src 'self' https://api.complywithai.de");
    expect(policy).toContain("upgrade-insecure-requests");
    expect(policy).toContain("report-uri /api/security/csp-report");
    expect(policy).toContain("report-to csp-endpoint");
    expect(policy).not.toContain("unsafe-inline");
    expect(policy).not.toContain("unsafe-eval");
  });

  it("allows only the development runtime exception and websocket transport", () => {
    const policy = buildContentSecurityPolicy({
      nonce: createCspNonce(),
      development: true,
    });

    expect(policy).toContain("'unsafe-eval'");
    expect(policy).toContain("connect-src 'self' ws:");
    expect(policy).not.toContain("unsafe-inline");
    expect(policy).not.toContain("upgrade-insecure-requests");
    expect(policy).not.toContain("report-uri");
    expect(policy).not.toContain("report-to");
  });

  it("rejects malformed nonces and non-http API origins", () => {
    expect(() =>
      buildContentSecurityPolicy({ nonce: "attacker'; script-src *", development: false }),
    ).toThrow("CSP nonce");

    const policy = buildContentSecurityPolicy({
      nonce: createCspNonce(),
      development: false,
      apiBaseUrl: "javascript:alert(1)",
    });
    expect(policy).toContain("connect-src 'self'");
    expect(policy).not.toContain("javascript:");
  });
});

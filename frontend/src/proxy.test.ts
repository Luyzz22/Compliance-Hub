import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "@/proxy";

afterEach(() => {
  vi.unstubAllEnvs();
});

function nonceFrom(policy: string): string {
  const match = policy.match(/'nonce-([^']+)'/);
  if (!match) throw new Error("CSP nonce missing");
  return match[1];
}

describe("proxy CSP boundary", () => {
  it("generates a unique nonce and non-cacheable policy per request", () => {
    vi.stubEnv("NODE_ENV", "production");
    const first = proxy(new NextRequest("https://complywithai.de/"));
    const second = proxy(new NextRequest("https://complywithai.de/"));
    const firstPolicy = first.headers.get("content-security-policy") ?? "";
    const secondPolicy = second.headers.get("content-security-policy") ?? "";

    expect(firstPolicy).not.toContain("unsafe-inline");
    expect(firstPolicy).not.toContain("unsafe-eval");
    expect(nonceFrom(firstPolicy)).not.toBe(nonceFrom(secondPolicy));
    expect(first.headers.get("cache-control")).toBe("private, no-store");
    expect(first.headers.get("reporting-endpoints")).toBe(
      'csp-endpoint="/api/security/csp-report"',
    );
  });

  it("retains the strict policy on authentication redirects", () => {
    vi.stubEnv("NODE_ENV", "production");
    const response = proxy(
      new NextRequest("https://complywithai.de/tenant/governance/overview"),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/auth/login");
    expect(response.headers.get("content-security-policy")).toContain(
      "style-src-attr 'none'",
    );
    expect(response.headers.get("reporting-endpoints")).toBe(
      'csp-endpoint="/api/security/csp-report"',
    );
  });

  it("does not configure violation delivery for development-only policies", () => {
    vi.stubEnv("NODE_ENV", "development");
    const response = proxy(new NextRequest("http://localhost:3000/"));

    expect(response.headers.get("content-security-policy")).not.toContain("report-to");
    expect(response.headers.has("reporting-endpoints")).toBe(false);
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "@/app/api/security/csp-report/route";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CSP reporting route", () => {
  it("logs only the minimized security event and returns no content", async () => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const payload = JSON.stringify({
      "csp-report": {
        "document-uri": "https://complywithai.de/private?email=person@example.com",
        "blocked-uri": "https://cdn.example/payload.js?secret=1",
        "effective-directive": "script-src-elem",
        "script-sample": "document.cookie",
        disposition: "enforce",
        "status-code": 200,
      },
    });
    const response = await POST(
      new Request("https://complywithai.de/api/security/csp-report", {
        method: "POST",
        headers: { "content-type": "application/csp-report" },
        body: payload,
      }),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(warning).toHaveBeenCalledOnce();
    const log = warning.mock.calls.flat().join(" ");
    expect(log).toContain("script-src-elem");
    expect(log).not.toContain("person@example.com");
    expect(log).not.toContain("document.cookie");
    expect(log).not.toContain("secret=1");
  });

  it("rejects unsupported, malformed and oversized input without logging", async () => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const unsupported = await POST(
      new Request("https://complywithai.de/api/security/csp-report", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      }),
    );
    const malformed = await POST(
      new Request("https://complywithai.de/api/security/csp-report", {
        method: "POST",
        headers: { "content-type": "application/reports+json" },
        body: "{",
      }),
    );
    const oversized = await POST(
      new Request("https://complywithai.de/api/security/csp-report", {
        method: "POST",
        headers: {
          "content-type": "application/csp-report",
          "content-length": String(17 * 1024),
        },
        body: "{}",
      }),
    );
    const chunkedOversized = await POST(
      new Request("https://complywithai.de/api/security/csp-report", {
        method: "POST",
        headers: { "content-type": "application/csp-report" },
        body: "x".repeat(17 * 1024),
      }),
    );

    expect(unsupported.status).toBe(415);
    expect(malformed.status).toBe(400);
    expect(oversized.status).toBe(413);
    expect(chunkedOversized.status).toBe(413);
    expect(warning).not.toHaveBeenCalled();
  });

  it("allows only POST", async () => {
    const response = GET();
    expect(response.status).toBe(405);
    expect(response.headers.get("allow")).toBe("POST");
  });
});

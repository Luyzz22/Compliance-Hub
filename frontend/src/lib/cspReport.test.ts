import { describe, expect, it } from "vitest";

import { sanitizeCspReports } from "@/lib/cspReport";

describe("CSP report data minimization", () => {
  it("accepts legacy reports and removes paths, queries, referrers and samples", () => {
    const [report] = sanitizeCspReports({
      "csp-report": {
        "document-uri": "https://complywithai.de/tenant/acme?email=person@example.com",
        referrer: "https://identity.example/private/account",
        "blocked-uri": "https://cdn.attacker.example/script.js?token=secret",
        "effective-directive": "script-src-elem",
        "source-file": "https://complywithai.de/_next/static/chunk.js?build=secret",
        "script-sample": "alert(document.cookie)",
        "status-code": 200,
        disposition: "enforce",
      },
    });

    expect(report).toEqual({
      event: "csp_violation",
      disposition: "enforce",
      effective_directive: "script-src-elem",
      document_origin: "https://complywithai.de",
      blocked_resource: "https://cdn.attacker.example",
      source_origin: "https://complywithai.de",
      status_code: 200,
    });
    expect(JSON.stringify(report)).not.toContain("person@example.com");
    expect(JSON.stringify(report)).not.toContain("document.cookie");
    expect(JSON.stringify(report)).not.toContain("token=secret");
  });

  it("accepts Reporting API batches and caps attacker-controlled values", () => {
    const reports = sanitizeCspReports([
      {
        type: "csp-violation",
        url: "https://complywithai.de/settings?tenant=secret",
        body: {
          documentURL: "https://complywithai.de/settings?tenant=secret",
          blockedURL: "inline",
          effectiveDirective: "STYLE-SRC-ELEM",
          disposition: "report",
          statusCode: 999,
        },
      },
      { type: "deprecation", body: { message: "ignored" } },
    ]);

    expect(reports).toEqual([
      {
        event: "csp_violation",
        disposition: "report",
        effective_directive: "style-src-elem",
        document_origin: "https://complywithai.de",
        blocked_resource: "inline",
        source_origin: null,
        status_code: null,
      },
    ]);
  });
});

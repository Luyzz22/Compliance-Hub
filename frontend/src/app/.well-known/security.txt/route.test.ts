import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/.well-known/security.txt/route";

describe("security.txt", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("publishes a current RFC 9116 contact document", async () => {
    vi.stubEnv("COMPLIANCEHUB_SECURITY_CONTACT", "mailto:security@complywithai.de");

    const response = GET();
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/plain");
    expect(body).toContain("Contact: mailto:security@complywithai.de");
    expect(body).toContain(
      "Canonical: https://complywithai.de/.well-known/security.txt",
    );
    expect(new Date(body.match(/Expires: (.+)/)?.[1] ?? 0).getTime()).toBeGreaterThan(
      Date.now(),
    );
  });
});

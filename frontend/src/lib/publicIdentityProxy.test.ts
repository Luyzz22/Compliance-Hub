import { NextRequest } from "next/server";

import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyPublicIdentityMutation } from "@/lib/publicIdentityProxy";

const BFF_SECRET = "bff-secret-with-at-least-thirty-two-bytes";

function request(
  path: string,
  body: Record<string, unknown>,
  origin = "https://app.complywithai.de",
  ip = "203.0.113.10",
): NextRequest {
  return new NextRequest(`https://app.complywithai.de${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: origin,
      "x-forwarded-for": ip,
    },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("public identity same-origin BFF", () => {
  it("rejects cross-origin mutations before contacting the backend", async () => {
    const backendFetch = vi.fn();
    vi.stubGlobal("fetch", backendFetch);
    vi.stubEnv("COMPLIANCEHUB_APP_ORIGIN", "https://app.complywithai.de");

    const response = await proxyPublicIdentityMutation(
      request(
        "/api/auth/register",
        { email: "person@example.de", password: "SecurePassword123" },
        "https://attacker.invalid",
      ),
      "register",
    );

    expect(response.status).toBe(403);
    expect(backendFetch).not.toHaveBeenCalled();
  });

  it("disables local registration and password reset in enterprise production", async () => {
    const backendFetch = vi.fn();
    vi.stubGlobal("fetch", backendFetch);
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");

    const response = await proxyPublicIdentityMutation(
      request(
        "/api/auth/register",
        { email: "person@example.de", password: "SecurePassword123" },
      ),
      "register",
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ error: "local_identity_disabled" });
    expect(backendFetch).not.toHaveBeenCalled();
  });

  it("also disables local identity when Node runs in production", async () => {
    const backendFetch = vi.fn();
    vi.stubGlobal("fetch", backendFetch);
    vi.stubEnv("NODE_ENV", "production");

    const response = await proxyPublicIdentityMutation(
      request("/api/auth/password-reset/request", { email: "person@example.de" }),
      "password_reset_request",
    );

    expect(response.status).toBe(404);
    expect(backendFetch).not.toHaveBeenCalled();
  });

  it("forwards only to the fixed internal identity path with the BFF credential", async () => {
    const backendFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ user_id: "user-1", email: "person@example.de" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", backendFetch);
    vi.stubEnv("COMPLIANCEHUB_APP_ORIGIN", "https://app.complywithai.de");
    vi.stubEnv("COMPLIANCEHUB_API_BASE_URL", "http://backend:8000");
    vi.stubEnv("COMPLIANCEHUB_BFF_SHARED_SECRET", BFF_SECRET);

    const response = await proxyPublicIdentityMutation(
      request(
        "/api/auth/register",
        { email: "person@example.de", password: "SecurePassword123" },
      ),
      "register",
    );

    expect(response.status).toBe(201);
    expect(response.headers.get("cache-control")).toContain("no-store");
    expect(backendFetch).toHaveBeenCalledOnce();
    const [url, init] = backendFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://backend:8000/api/v1/auth/register");
    expect(new Headers(init.headers).get("x-bff-secret")).toBe(BFF_SECRET);
  });

  it("rate-limits repeated reset requests per pseudonymized network key", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async () =>
        new Response(JSON.stringify({ message: "accepted" }), { status: 200 }),
      ),
    );
    vi.stubEnv("COMPLIANCEHUB_APP_ORIGIN", "https://app.complywithai.de");
    vi.stubEnv("COMPLIANCEHUB_API_BASE_URL", "http://backend:8000");

    const responses = [];
    for (let index = 0; index < 6; index += 1) {
      responses.push(
        await proxyPublicIdentityMutation(
          request(
            "/api/auth/password-reset/request",
            { email: "person@example.de" },
            "https://app.complywithai.de",
            "203.0.113.77",
          ),
          "password_reset_request",
        ),
      );
    }

    expect(responses.slice(0, 5).every((response) => response.status === 200)).toBe(true);
    expect(responses[5].status).toBe(429);
    expect(responses[5].headers.get("retry-after")).toBeTruthy();
  });
});

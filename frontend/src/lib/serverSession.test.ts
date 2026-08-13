import { NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "@/lib/authConstants";
import {
  clearSessionCookies,
  complianceApiBaseUrl,
  setSessionCookies,
} from "@/lib/serverSession";
import { WORKSPACE_TENANT_COOKIE } from "@/lib/workspaceTenantConstants";

describe("server session cookies", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("binds the production BFF to an explicit internal backend host", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("COMPLIANCEHUB_API_ALLOWED_HOSTS", "backend");
    vi.stubEnv("COMPLIANCEHUB_API_BASE_URL", "http://backend:8000");
    expect(complianceApiBaseUrl()).toBe("http://backend:8000");

    vi.stubEnv("COMPLIANCEHUB_API_BASE_URL", "https://attacker.example");
    expect(() => complianceApiBaseUrl()).toThrow("must be listed");
  });

  it("bindet die sichtbare Workspace-Auswahl an den authentifizierten Mandanten", () => {
    const response = NextResponse.json({ ok: true });

    setSessionCookies(
      response,
      "session-token",
      "2099-01-01T00:00:00Z",
      "tenant/dach",
    );

    expect(response.cookies.get(SESSION_COOKIE_NAME)?.value).toBe("session-token");
    expect(response.cookies.get(CSRF_COOKIE_NAME)?.value).toBeTruthy();
    expect(response.cookies.get(WORKSPACE_TENANT_COOKIE)?.value).toBe(
      "tenant%2Fdach",
    );
  });

  it("entfernt beim Session-Ende auch die Workspace-Auswahl", () => {
    const response = NextResponse.json({ ok: true });

    clearSessionCookies(response);

    expect(response.cookies.get(SESSION_COOKIE_NAME)?.value).toBe("");
    expect(response.cookies.get(CSRF_COOKIE_NAME)?.value).toBe("");
    expect(response.cookies.get(WORKSPACE_TENANT_COOKIE)?.value).toBe("");
  });
});

import { NextRequest } from "next/server";

import { afterEach, describe, expect, it, vi } from "vitest";

import { GET as identityStatus } from "@/app/api/auth/entra/status/route";
import { POST as passwordLogin } from "@/app/api/auth/login/route";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("enterprise production identity policy", () => {
  it("fails closed when Entra is unavailable", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("COMPLIANCEHUB_ENTRA_ENABLED", "false");

    const response = identityStatus();
    const body = await response.json();

    expect(body).toMatchObject({
      enabled: false,
      passwordLoginEnabled: false,
      selfRegistrationEnabled: false,
    });
  });

  it("rejects direct password-login API calls without contacting the backend", async () => {
    const backendFetch = vi.fn();
    vi.stubGlobal("fetch", backendFetch);
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");

    const response = await passwordLogin(
      new NextRequest("https://app.complywithai.de/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Origin: "https://app.complywithai.de",
        },
        body: JSON.stringify({
          email: "person@example.de",
          password: "SecurePassword123",
        }),
      }),
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toMatchObject({ error: "password_login_disabled" });
    expect(backendFetch).not.toHaveBeenCalled();
  });

  it("opens password login only for the fully attested synthetic read-only profile", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "pilot");
    vi.stubEnv("COMPLIANCEHUB_RELEASE_PROFILE", "synthetic_demo");
    vi.stubEnv("COMPLIANCEHUB_FEATURE_DEMO_MODE", "true");
    vi.stubEnv("COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS", "true");
    vi.stubEnv("COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED", "true");
    vi.stubEnv("COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED", "true");
    vi.stubEnv("COMPLIANCEHUB_SELF_REGISTRATION_ENABLED", "false");
    vi.stubEnv("COMPLIANCEHUB_PUBLIC_DEMO_ENABLED", "false");
    vi.stubEnv("COMPLIANCEHUB_ENTRA_ENABLED", "false");

    const response = identityStatus();
    await expect(response.json()).resolves.toMatchObject({
      enabled: false,
      passwordLoginEnabled: true,
      selfRegistrationEnabled: false,
    });
  });

  it("keeps password login closed when one synthetic safety attestation is missing", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "pilot");
    vi.stubEnv("COMPLIANCEHUB_RELEASE_PROFILE", "synthetic_demo");
    vi.stubEnv("COMPLIANCEHUB_FEATURE_DEMO_MODE", "true");
    vi.stubEnv("COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS", "false");
    vi.stubEnv("COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED", "true");
    vi.stubEnv("COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED", "true");

    const response = identityStatus();
    await expect(response.json()).resolves.toMatchObject({
      passwordLoginEnabled: false,
      selfRegistrationEnabled: false,
    });
  });
});

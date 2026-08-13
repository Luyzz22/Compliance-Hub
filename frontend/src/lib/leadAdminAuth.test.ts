import { createHmac } from "node:crypto";
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createLeadAdminSessionToken,
  isLeadAdminOrGtmAlertSecretAuthorized,
  isLeadAdminAuthorized,
  leadAdminCredentialIsValid,
  leadAdminIsConfigured,
  leadAdminCookieOptions,
  verifyLeadAdminSession,
} from "@/lib/leadAdminAuth";

const SECRET = "lead-admin-secret-with-at-least-thirty-two-bytes";
const directories: string[] = [];

function configureMountedSecret(): void {
  const directory = mkdtempSync(join(tmpdir(), "compliancehub-admin-secret-"));
  directories.push(directory);
  const path = join(directory, "lead-admin-secret");
  writeFileSync(path, `${SECRET}\n`, { mode: 0o400 });
  chmodSync(path, 0o400);
  vi.stubEnv("LEAD_ADMIN_SECRET_FILE", path);
  vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
}

function configureGtmMountedSecret(): void {
  const directory = mkdtempSync(join(tmpdir(), "compliancehub-gtm-secret-"));
  directories.push(directory);
  const path = join(directory, "gtm-secret");
  writeFileSync(path, `${SECRET}\n`, { mode: 0o400 });
  chmodSync(path, 0o400);
  vi.stubEnv("GTM_ALERT_SECRET_FILE", path);
  vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
}

afterEach(() => {
  vi.unstubAllEnvs();
  for (const directory of directories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

describe("lead admin credential boundary", () => {
  it("validates the mounted credential without exposing it", () => {
    configureMountedSecret();
    expect(leadAdminIsConfigured()).toBe(true);
    expect(leadAdminCredentialIsValid(SECRET)).toBe(true);
    expect(leadAdminCredentialIsValid(`${SECRET}-wrong`)).toBe(false);
  });

  it("accepts a bearer credential and rejects query credentials in production", () => {
    configureMountedSecret();
    const bearerRequest = new Request("https://app.example.invalid/admin", {
      headers: { Authorization: `Bearer ${SECRET}` },
    });
    const queryRequest = new Request(
      `https://app.example.invalid/admin?secret=${encodeURIComponent(SECRET)}`,
    );

    expect(isLeadAdminAuthorized(bearerRequest)).toBe(true);
    expect(isLeadAdminAuthorized(queryRequest)).toBe(false);
  });

  it("rejects a direct production secret", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv("LEAD_ADMIN_SECRET", SECRET);
    expect(() => leadAdminIsConfigured()).toThrow("forbidden in production");
  });

  it("uses a strict, secure and bounded admin session", () => {
    configureMountedSecret();
    vi.stubEnv("COMPLIANCEHUB_SESSION_TTL_MINUTES", "9999");

    const token = createLeadAdminSessionToken();

    expect(token).not.toBeNull();
    expect(verifyLeadAdminSession(token)).toBe(true);
    expect(leadAdminCookieOptions()).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: "strict",
      maxAge: 480 * 60,
    });
  });

  it("accepts only a fresh HMAC signature for GTM automation", () => {
    configureGtmMountedSecret();
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const path = "/api/admin/gtm/alert-check";
    const signature = createHmac("sha256", SECRET)
      .update(`GET\n${path}\n${timestamp}`)
      .digest("hex");
    const signed = new Request(`https://app.example.invalid${path}`, {
      headers: {
        "X-ComplianceHub-Timestamp": timestamp,
        "X-ComplianceHub-Signature": `v1=${signature}`,
      },
    });
    const leakedBearer = new Request(`https://app.example.invalid${path}`, {
      headers: { Authorization: `Bearer ${SECRET}` },
    });

    expect(isLeadAdminOrGtmAlertSecretAuthorized(signed)).toBe(true);
    expect(isLeadAdminOrGtmAlertSecretAuthorized(leakedBearer)).toBe(false);
  });

  it("rejects expired GTM automation signatures", () => {
    configureGtmMountedSecret();
    const timestamp = (Math.floor(Date.now() / 1000) - 301).toString();
    const path = "/api/admin/gtm/health-snapshot";
    const signature = createHmac("sha256", SECRET)
      .update(`GET\n${path}\n${timestamp}`)
      .digest("hex");
    const request = new Request(`https://app.example.invalid${path}`, {
      headers: {
        "X-ComplianceHub-Timestamp": timestamp,
        "X-ComplianceHub-Signature": `v1=${signature}`,
      },
    });

    expect(isLeadAdminOrGtmAlertSecretAuthorized(request)).toBe(false);
  });
});

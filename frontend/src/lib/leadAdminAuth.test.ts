import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createLeadAdminSessionToken,
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
});

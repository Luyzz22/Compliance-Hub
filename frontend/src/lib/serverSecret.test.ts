import {
  chmodSync,
  mkdtempSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import { readServerSecret } from "@/lib/serverSecret";

const ENV_NAME = "TEST_SERVER_SECRET";
const FILE_ENV_NAME = "TEST_SERVER_SECRET_FILE";
const directories: string[] = [];

function secretFile(mode = 0o400): string {
  const directory = mkdtempSync(join(tmpdir(), "compliancehub-secret-"));
  directories.push(directory);
  const path = join(directory, "secret");
  writeFileSync(path, "a-secret-with-at-least-32-bytes-value\n", { mode });
  chmodSync(path, mode);
  return path;
}

afterEach(() => {
  vi.unstubAllEnvs();
  for (const directory of directories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

describe("server secret boundary", () => {
  it("reads an approved mounted file and trims its trailing newline", () => {
    const path = secretFile();
    vi.stubEnv(FILE_ENV_NAME, path);

    expect(
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
        minimumBytes: 32,
        required: true,
      }),
    ).toBe("a-secret-with-at-least-32-bytes-value");
  });

  it("rejects broad file permissions", () => {
    vi.stubEnv(FILE_ENV_NAME, secretFile(0o644));

    expect(() =>
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
      }),
    ).toThrow("mode 0400 or 0600");
  });

  it("rejects symlinks and oversized mounted secrets", () => {
    const target = secretFile();
    const directory = mkdtempSync(join(tmpdir(), "compliancehub-secret-link-"));
    directories.push(directory);
    const link = join(directory, "secret-link");
    symlinkSync(target, link);
    vi.stubEnv(FILE_ENV_NAME, link);

    expect(() =>
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
      }),
    ).toThrow("regular file, not a symlink");

    const oversized = join(directory, "oversized");
    writeFileSync(oversized, "x".repeat(64 * 1024 + 1), { mode: 0o400 });
    vi.stubEnv(FILE_ENV_NAME, oversized);
    expect(() =>
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
      }),
    ).toThrow("invalid secret-file size");
  });

  it("rejects direct secret values in production", () => {
    vi.stubEnv("COMPLIANCEHUB_RELEASE_CHANNEL", "production");
    vi.stubEnv(ENV_NAME, "direct-secret-value");

    expect(() =>
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
      }),
    ).toThrow("is forbidden in production");
  });

  it("rejects ambiguous direct and file configuration", () => {
    vi.stubEnv(ENV_NAME, "direct-secret-value");
    vi.stubEnv(FILE_ENV_NAME, secretFile());

    expect(() =>
      readServerSecret({
        environmentVariable: ENV_NAME,
        fileEnvironmentVariable: FILE_ENV_NAME,
      }),
    ).toThrow("are mutually exclusive");
  });
});

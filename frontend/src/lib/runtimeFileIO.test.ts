import { GetObjectCommand, PutObjectCommand, type S3Client } from "@aws-sdk/client-s3";
import type { PoolClient } from "pg";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  __setS3RuntimeClientFactoryForTests,
  appendRuntimeTextFile,
  isRuntimeStorageNotFoundError,
  readRuntimeTextFile,
  resolveRuntimeStorageBackend,
  runtimeBlobNameFromPath,
  withRuntimeStorageLock,
  writeRuntimeTextFile,
} from "@/lib/runtimeFileIO";
import { __setRuntimePostgresPoolFactoryForTests } from "@/lib/runtimePostgres";

afterEach(async () => {
  __setS3RuntimeClientFactoryForTests(null);
  __setRuntimePostgresPoolFactoryForTests(null);
  vi.unstubAllEnvs();
});

function memoryS3Client(): { client: Pick<S3Client, "send">; objects: Map<string, Buffer> } {
  const objects = new Map<string, Buffer>();
  const client = {
    async send(command: GetObjectCommand | PutObjectCommand) {
      if (command instanceof GetObjectCommand) {
        const value = objects.get(String(command.input.Key));
        if (!value) throw { name: "NoSuchKey" };
        return {
          Body: {
            async transformToByteArray() {
              return value;
            },
          },
        };
      }
      if (command instanceof PutObjectCommand) {
        objects.set(String(command.input.Key), Buffer.from(command.input.Body as Uint8Array));
        return {};
      }
      throw new Error("Unexpected S3 command");
    },
  } as unknown as Pick<S3Client, "send">;
  return { client, objects };
}

function configureS3Runtime(): void {
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "s3");
  vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_PREFIX", "compliancehub/runtime/v1");
  vi.stubEnv("COMPLIANCEHUB_S3_ENDPOINT", "http://minio.internal");
  vi.stubEnv("COMPLIANCEHUB_S3_REGION", "fsn1");
  vi.stubEnv("COMPLIANCEHUB_S3_BUCKET", "compliancehub-runtime");
  vi.stubEnv("COMPLIANCEHUB_S3_ACCESS_KEY_FILE", "/run/secrets/s3-access-key");
  vi.stubEnv("COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE", "/run/secrets/s3-secret-key");
  vi.stubEnv("POSTGRES_HOST", "postgres.internal");
  vi.stubEnv("POSTGRES_DATABASE", "compliancehub");
  vi.stubEnv("POSTGRES_USER", "compliancehub-runtime");
  vi.stubEnv("POSTGRES_PASSWORD_FILE", "/run/secrets/postgres-password");
  const client = {
    query: vi.fn(async () => ({ rows: [] })),
    release: vi.fn(),
  } as unknown as PoolClient;
  __setRuntimePostgresPoolFactoryForTests(() => ({
    connect: vi.fn(async () => client),
  }));
}

describe("runtime storage policy", () => {
  it("defaults to local only outside production and fails closed in production", () => {
    expect(resolveRuntimeStorageBackend({ NODE_ENV: "development" })).toBe("local");
    expect(() => resolveRuntimeStorageBackend({ NODE_ENV: "production" })).toThrow(
      "must be s3",
    );
    expect(
      resolveRuntimeStorageBackend({
        NODE_ENV: "production",
        COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND: "s3",
      }),
    ).toBe("s3");
    expect(() =>
      resolveRuntimeStorageBackend({
        NODE_ENV: "production",
        COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND: "azure_blob",
      }),
    ).toThrow("Unsupported runtime storage backend");
    expect(() =>
      resolveRuntimeStorageBackend({
        NODE_ENV: "production",
        COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND: "local",
      }),
    ).toThrow("forbidden");
  });

  it("maps local and temporary paths to traversal-free blob names", () => {
    const env = { COMPLIANCEHUB_RUNTIME_STORAGE_PREFIX: "tenant-a/runtime/v1" };
    expect(runtimeBlobNameFromPath("/workspace/data/state.json", env, "/workspace")).toBe(
      "tenant-a/runtime/v1/data/state.json",
    );
    expect(runtimeBlobNameFromPath("/tmp/compliancehub-state.json", env, "/workspace")).toBe(
      "tenant-a/runtime/v1/compliancehub-state.json",
    );
    expect(() =>
      runtimeBlobNameFromPath("/tmp/state.json", {
        COMPLIANCEHUB_RUNTIME_STORAGE_PREFIX: "../escape",
      }),
    ).toThrow("Invalid runtime storage prefix");
  });
});

describe("runtime storage I/O", () => {
  it("uses S3-compatible object storage with PostgreSQL advisory locking", async () => {
    configureS3Runtime();
    const memory = memoryS3Client();
    __setS3RuntimeClientFactoryForTests(() => memory.client);
    const statePath = "/tmp/compliancehub-s3-state.jsonl";

    await expect(readRuntimeTextFile(statePath)).rejects.toSatisfy(
      isRuntimeStorageNotFoundError,
    );
    await writeRuntimeTextFile(statePath, "first\n");
    await appendRuntimeTextFile(statePath, "second\n");

    expect(await readRuntimeTextFile(statePath)).toBe("first\nsecond\n");
    expect([...memory.objects.keys()]).toEqual([
      "compliancehub/runtime/v1/compliancehub-s3-state.jsonl",
    ]);
  });

  it("keeps non-production local state process-local and appends records", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "local");
    const path = "/tmp/compliancehub-runtime-process-local-state.jsonl";

    await writeRuntimeTextFile(path, "first\n");
    await appendRuntimeTextFile(path, "second\n");

    expect(await readRuntimeTextFile(path)).toBe("first\nsecond\n");
  });

  it("serializes local read-modify-write sections", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "local");
    const order: string[] = [];
    const path = "/tmp/compliancehub-lock-test.json";

    await Promise.all([
      withRuntimeStorageLock(path, async () => {
        order.push("first:start");
        await new Promise((resolve) => setTimeout(resolve, 5));
        order.push("first:end");
      }),
      withRuntimeStorageLock(path, async () => {
        order.push("second:start");
        order.push("second:end");
      }),
    ]);

    expect(order).toEqual(["first:start", "first:end", "second:start", "second:end"]);
  });

});

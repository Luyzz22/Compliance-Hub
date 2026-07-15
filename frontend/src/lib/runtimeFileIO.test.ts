import type { ContainerClient } from "@azure/storage-blob";
import { mkdtemp, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  __setAzureContainerClientFactoryForTests,
  appendRuntimeTextFile,
  isRuntimeStorageNotFoundError,
  readRuntimeTextFile,
  resolveAzureAuthMode,
  resolveRuntimeStorageBackend,
  runtimeBlobNameFromPath,
  withRuntimeStorageLock,
  writeRuntimeTextFile,
} from "@/lib/runtimeFileIO";

const temporaryDirectories: string[] = [];

afterEach(async () => {
  __setAzureContainerClientFactoryForTests(null);
  vi.unstubAllEnvs();
  await Promise.all(temporaryDirectories.splice(0).map((path) => rm(path, { recursive: true })));
});

function memoryContainer(): { client: ContainerClient; blobs: Map<string, Buffer> } {
  const blobs = new Map<string, Buffer>();
  const leases = new Set<string>();
  const client = {
    getBlockBlobClient(name: string) {
      return {
        async downloadToBuffer(_offset: number, count: number) {
          const value = blobs.get(name);
          if (!value) throw { statusCode: 404, code: "BlobNotFound" };
          return value.subarray(0, count);
        },
        async uploadData(content: Buffer, options?: { conditions?: { ifNoneMatch?: string } }) {
          if (options?.conditions?.ifNoneMatch === "*" && blobs.has(name)) {
            throw { statusCode: 412, code: "ConditionNotMet" };
          }
          blobs.set(name, Buffer.from(content));
          return {};
        },
        getBlobLeaseClient() {
          return {
            async acquireLease() {
              if (leases.has(name)) throw { statusCode: 409, code: "LeaseAlreadyPresent" };
              leases.add(name);
              return {};
            },
            async releaseLease() {
              leases.delete(name);
              return {};
            },
          };
        },
      };
    },
    getAppendBlobClient(name: string) {
      return {
        async createIfNotExists() {
          if (!blobs.has(name)) blobs.set(name, Buffer.alloc(0));
          return { succeeded: true };
        },
        async appendBlock(content: Buffer) {
          blobs.set(name, Buffer.concat([blobs.get(name) ?? Buffer.alloc(0), content]));
          return {};
        },
      };
    },
  } as unknown as ContainerClient;
  return { client, blobs };
}

describe("runtime storage policy", () => {
  it("defaults to local only outside production and fails closed in production", () => {
    expect(resolveRuntimeStorageBackend({ NODE_ENV: "development" })).toBe("local");
    expect(() => resolveRuntimeStorageBackend({ NODE_ENV: "production" })).toThrow(
      "must be azure_blob",
    );
    expect(() =>
      resolveRuntimeStorageBackend({
        NODE_ENV: "production",
        COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND: "local",
      }),
    ).toThrow("forbidden");
  });

  it("selects passwordless Azure authentication modes", () => {
    expect(resolveAzureAuthMode({ NODE_ENV: "development" })).toBe("default");
    expect(resolveAzureAuthMode({ NODE_ENV: "production" })).toBe("managed_identity");
    expect(resolveAzureAuthMode({ NODE_ENV: "production", VERCEL: "1" })).toBe(
      "vercel_oidc",
    );
    expect(() =>
      resolveAzureAuthMode({
        NODE_ENV: "production",
        COMPLIANCEHUB_RUNTIME_STORAGE_AUTH: "default",
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
  it("writes local files atomically with private permissions and appends records", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "local");
    const directory = await mkdtemp(join(tmpdir(), "compliancehub-runtime-"));
    temporaryDirectories.push(directory);
    const path = join(directory, "state.jsonl");

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

  it("uses Azure block and append blobs and distinguishes absent objects", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "azure_blob");
    const memory = memoryContainer();
    __setAzureContainerClientFactoryForTests(() => memory.client);
    const statePath = "/tmp/compliancehub-state.json";
    const logPath = "/tmp/compliancehub-events.jsonl";

    await expect(readRuntimeTextFile(statePath)).rejects.toSatisfy(
      isRuntimeStorageNotFoundError,
    );
    await writeRuntimeTextFile(statePath, '{"ok":true}\n');
    await appendRuntimeTextFile(logPath, '{"event":1}\n');
    await appendRuntimeTextFile(logPath, '{"event":2}\n');

    expect(await readRuntimeTextFile(statePath)).toBe('{"ok":true}\n');
    expect(await readRuntimeTextFile(logPath)).toBe('{"event":1}\n{"event":2}\n');
    expect([...memory.blobs.keys()]).toEqual([
      "compliancehub/runtime/v1/compliancehub-state.json",
      "compliancehub/runtime/v1/compliancehub-events.jsonl",
    ]);
  });

  it("does not misclassify a missing Azure container as an empty object", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "azure_blob");
    const client = {
      getBlockBlobClient() {
        return {
          async downloadToBuffer() {
            throw { statusCode: 404, code: "ContainerNotFound" };
          },
        };
      },
    } as unknown as ContainerClient;
    __setAzureContainerClientFactoryForTests(() => client);

    await expect(readRuntimeTextFile("/tmp/state.json")).rejects.toMatchObject({
      name: "RuntimeStorageOperationError",
      message: "Runtime storage read failed",
    });
  });

  it("serializes Azure read-modify-write sections with blob leases", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "azure_blob");
    const memory = memoryContainer();
    __setAzureContainerClientFactoryForTests(() => memory.client);
    const order: string[] = [];
    const path = "/tmp/compliancehub-lease-test.json";

    await Promise.all([
      withRuntimeStorageLock(path, async () => {
        order.push("first:start");
        await new Promise((resolve) => setTimeout(resolve, 15));
        order.push("first:end");
      }),
      withRuntimeStorageLock(path, async () => {
        order.push("second:start");
        order.push("second:end");
      }),
    ]);

    expect(order).toEqual(["first:start", "first:end", "second:start", "second:end"]);
    expect([...memory.blobs.keys()].some((name) => name.includes("/locks/"))).toBe(true);
  });
});

import type { PoolClient, PoolConfig } from "pg";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  __setRuntimePostgresPoolFactoryForTests,
  resolveAzurePostgresConfig,
  resolveRelationalRuntimeBackend,
  withPlatformRuntimePostgres,
  withTenantRuntimePostgres,
} from "@/lib/runtimePostgres";

type QueryCall = { text: string; values?: unknown[] };

function configureAzurePostgres(): void {
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND", "azure_postgres");
  vi.stubEnv("AZURE_POSTGRES_HOST", "compliancehub.postgres.database.azure.com");
  vi.stubEnv("AZURE_POSTGRES_DATABASE", "compliancehub");
  vi.stubEnv("AZURE_POSTGRES_USER", "compliancehub-runtime");
  vi.stubEnv("COMPLIANCEHUB_RUNTIME_STORAGE_AUTH", "default");
}

function installFakePool(
  queryImplementation?: (text: string, values?: unknown[]) => Promise<{ rows: unknown[] }>,
): {
  calls: QueryCall[];
  release: ReturnType<typeof vi.fn>;
  config: () => PoolConfig;
} {
  const calls: QueryCall[] = [];
  const release = vi.fn();
  let capturedConfig: PoolConfig | undefined;
  const query = vi.fn(async (text: string, values?: unknown[]) => {
    calls.push({ text, values });
    return queryImplementation ? queryImplementation(text, values) : { rows: [] };
  });
  const client = { query, release } as unknown as PoolClient;
  __setRuntimePostgresPoolFactoryForTests((config) => {
    capturedConfig = config;
    return { connect: vi.fn(async () => client) };
  });
  return {
    calls,
    release,
    config: () => {
      if (!capturedConfig) throw new Error("Pool was not initialized");
      return capturedConfig;
    },
  };
}

afterEach(() => {
  __setRuntimePostgresPoolFactoryForTests(null);
  vi.unstubAllEnvs();
});

describe("relational runtime policy", () => {
  it("defaults to local only outside production and fails closed in production", () => {
    expect(resolveRelationalRuntimeBackend({ NODE_ENV: "development" })).toBe("local");
    expect(() => resolveRelationalRuntimeBackend({ NODE_ENV: "production" })).toThrow(
      "must be azure_postgres",
    );
    expect(() =>
      resolveRelationalRuntimeBackend({
        NODE_ENV: "production",
        COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND: "local",
      }),
    ).toThrow("forbidden");
  });

  it("accepts only an Azure PostgreSQL endpoint on the TLS port", () => {
    expect(
      resolveAzurePostgresConfig({
        AZURE_POSTGRES_HOST: "governance.postgres.database.azure.com",
        AZURE_POSTGRES_DATABASE: "compliancehub",
        AZURE_POSTGRES_USER: "runtime-principal",
      }),
    ).toMatchObject({
      host: "governance.postgres.database.azure.com",
      port: 5432,
      database: "compliancehub",
      user: "runtime-principal",
    });
    expect(() =>
      resolveAzurePostgresConfig({
        AZURE_POSTGRES_HOST: "attacker.example",
        AZURE_POSTGRES_DATABASE: "compliancehub",
        AZURE_POSTGRES_USER: "runtime-principal",
      }),
    ).toThrow("Azure PostgreSQL hostname");
    expect(() =>
      resolveAzurePostgresConfig({
        AZURE_POSTGRES_HOST: "governance.postgres.database.azure.com",
        AZURE_POSTGRES_PORT: "5433",
        AZURE_POSTGRES_DATABASE: "compliancehub",
        AZURE_POSTGRES_USER: "runtime-principal",
      }),
    ).toThrow("must be 5432");
    expect(() =>
      resolveAzurePostgresConfig({
        AZURE_POSTGRES_HOST: "governance.postgres.database.azure.com",
        AZURE_POSTGRES_DATABASE: "compliancehub",
        AZURE_POSTGRES_USER: "azure_pg_admin",
      }),
    ).toThrow("administrator identities are forbidden");
  });
});

describe("relational runtime transactions", () => {
  it("sets tenant and actor context locally and enforces TLS verification", async () => {
    configureAzurePostgres();
    const fake = installFakePool();

    const result = await withTenantRuntimePostgres(
      "tenant-a",
      "frontend:test",
      async (client) => {
        await client.query("SELECT tenant_id FROM example WHERE tenant_id = $1", [
          "tenant-a",
        ]);
        return "ok";
      },
    );

    expect(result).toBe("ok");
    expect(fake.calls.map((call) => call.text)).toEqual([
      "BEGIN READ WRITE",
      "SET LOCAL statement_timeout = '10s'",
      "SET LOCAL lock_timeout = '3s'",
      "SELECT set_config('compliancehub.tenant_id', $1, true)",
      "SELECT set_config('compliancehub.platform_access', $1, true)",
      "SELECT set_config('compliancehub.actor_id', $1, true)",
      "SELECT tenant_id FROM example WHERE tenant_id = $1",
      "COMMIT",
    ]);
    expect(fake.calls[3]?.values).toEqual(["tenant-a"]);
    expect(fake.calls[4]?.values).toEqual(["false"]);
    expect(fake.calls[5]?.values).toEqual(["frontend:test"]);
    expect(fake.release).toHaveBeenCalledWith(false);
    expect(fake.config().ssl).toMatchObject({ rejectUnauthorized: true });
    expect(fake.config().password).toBeTypeOf("function");
    expect(fake.config()).not.toHaveProperty("connectionString");
  });

  it("marks platform transactions explicitly and rolls back failures", async () => {
    configureAzurePostgres();
    const fake = installFakePool();

    await expect(
      withPlatformRuntimePostgres("frontend:test", async () => {
        throw new Error("sensitive database detail");
      }),
    ).rejects.toMatchObject({
      name: "RuntimePostgresOperationError",
      message: "Runtime PostgreSQL operation failed",
    });

    expect(fake.calls[3]?.values).toEqual(["__platform__"]);
    expect(fake.calls[4]?.values).toEqual(["true"]);
    expect(fake.calls.at(-1)?.text).toBe("ROLLBACK");
    expect(fake.release).toHaveBeenCalledWith(false);
  });

  it("does not expose connection failure details through the public error message", async () => {
    configureAzurePostgres();
    __setRuntimePostgresPoolFactoryForTests(() => ({
      connect: vi.fn(async () => {
        throw new Error("host and principal detail");
      }),
    }));

    await expect(
      withTenantRuntimePostgres("tenant-a", "frontend:test", async () => undefined),
    ).rejects.toMatchObject({
      name: "RuntimePostgresOperationError",
      message: "Runtime PostgreSQL operation failed",
    });
  });

  it("rejects invalid tenant and actor identifiers before opening a connection", async () => {
    configureAzurePostgres();
    const factory = vi.fn();
    __setRuntimePostgresPoolFactoryForTests(factory);

    expect(() =>
      withTenantRuntimePostgres("../tenant", "frontend:test", async () => undefined),
    ).toThrow("Invalid tenant identifier");
    expect(() =>
      withPlatformRuntimePostgres("invalid actor!", async () => undefined),
    ).toThrow("Invalid runtime database actor");
    expect(factory).not.toHaveBeenCalled();
  });
});

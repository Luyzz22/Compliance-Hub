import "server-only";

import { isAbsolute } from "node:path";
import { Pool, type PoolClient, type PoolConfig } from "pg";

import { readMountedServerSecretFile } from "@/lib/serverSecret";

const DATABASE_PATTERN = /^[A-Za-z_][A-Za-z0-9_-]{0,62}$/;
const TENANT_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$/;
const ACTOR_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;
const HOST_PATTERN = /^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:]+\])$/;
const FORBIDDEN_RUNTIME_USERS = new Set([
  "postgres",
  "azure_pg_admin",
  "azuresu",
  "root",
]);

export type RelationalRuntimeBackend = "local" | "postgres";
type RuntimeEnvironment = Readonly<Record<string, string | undefined>>;
type RuntimePostgresPool = Pick<Pool, "connect">;

export type RuntimePostgresConfig = Readonly<{
  host: string;
  port: number;
  database: string;
  user: string;
  passwordFile: string;
  sslCa?: string;
}>;

export class RuntimePostgresConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RuntimePostgresConfigurationError";
  }
}

export class RuntimePostgresOperationError extends Error {
  constructor(cause: unknown) {
    super("Runtime PostgreSQL operation failed", { cause });
    this.name = "RuntimePostgresOperationError";
  }
}

function isProductionRuntime(env: RuntimeEnvironment): boolean {
  return (
    env.NODE_ENV === "production" ||
    env.COMPLIANCEHUB_RELEASE_CHANNEL === "production"
  );
}

function requiredEnv(name: string, env: RuntimeEnvironment): string {
  const value = env[name]?.trim();
  if (!value) throw new RuntimePostgresConfigurationError(`${name} is required`);
  return value;
}

export function resolveRelationalRuntimeBackend(
  env: RuntimeEnvironment = process.env,
): RelationalRuntimeBackend {
  const configured = env.COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND?.trim().toLowerCase();
  if (configured === "postgres") return "postgres";
  if (configured === "local") {
    if (isProductionRuntime(env)) {
      throw new RuntimePostgresConfigurationError(
        "Local relational runtime storage is forbidden in production",
      );
    }
    return "local";
  }
  if (configured) {
    throw new RuntimePostgresConfigurationError(
      "Unsupported relational runtime backend",
    );
  }
  if (isProductionRuntime(env)) {
    throw new RuntimePostgresConfigurationError(
      "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND must be postgres in production",
    );
  }
  return "local";
}

function allowedPostgresHosts(env: RuntimeEnvironment): Set<string> {
  return new Set(
    (env.COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  );
}

export function resolveRuntimePostgresConfig(
  env: RuntimeEnvironment = process.env,
): RuntimePostgresConfig {
  const host = requiredEnv("POSTGRES_HOST", env).toLowerCase();
  if (!HOST_PATTERN.test(host) || host.includes("..")) {
    throw new RuntimePostgresConfigurationError("Invalid PostgreSQL hostname");
  }
  if (isProductionRuntime(env) && !allowedPostgresHosts(env).has(host)) {
    throw new RuntimePostgresConfigurationError(
      "POSTGRES_HOST must be explicitly listed in COMPLIANCEHUB_POSTGRES_ALLOWED_HOSTS",
    );
  }
  const port = Number(env.POSTGRES_PORT?.trim() || "5432");
  if (!Number.isSafeInteger(port) || port < 1 || port > 65535) {
    throw new RuntimePostgresConfigurationError("Invalid PostgreSQL port");
  }

  const database = requiredEnv("POSTGRES_DATABASE", env);
  if (!DATABASE_PATTERN.test(database)) {
    throw new RuntimePostgresConfigurationError("Invalid Azure PostgreSQL database name");
  }

  const user = requiredEnv("POSTGRES_USER", env);
  if (user.length > 256 || /[\u0000-\u001f\u007f]/.test(user)) {
    throw new RuntimePostgresConfigurationError("Invalid Azure PostgreSQL user");
  }
  if (FORBIDDEN_RUNTIME_USERS.has(user.toLowerCase())) {
    throw new RuntimePostgresConfigurationError(
      "PostgreSQL administrator identities are forbidden for application runtime",
    );
  }

  const passwordFile = requiredEnv("POSTGRES_PASSWORD_FILE", env);
  if (!isAbsolute(passwordFile)) {
    throw new RuntimePostgresConfigurationError("POSTGRES_PASSWORD_FILE must be absolute");
  }
  const sslCa = env.POSTGRES_SSL_CA_PEM?.trim();
  return {
    host,
    port,
    database,
    user,
    passwordFile,
    ...(sslCa ? { sslCa } : {}),
  };
}

async function readPostgresPassword(path: string): Promise<string> {
  try {
    return readMountedServerSecretFile({
      fileVariable: "POSTGRES_PASSWORD_FILE",
      filePath: path,
      minimumBytes: 32,
      maximumBytes: 4096,
    });
  } catch (error) {
    throw new RuntimePostgresConfigurationError(
      `Unable to read POSTGRES_PASSWORD_FILE: ${error instanceof Error ? error.name : "Error"}`,
    );
  }
}

function assertTenantId(tenantId: string): string {
  const normalized = tenantId.trim();
  if (!TENANT_ID_PATTERN.test(normalized)) {
    throw new RuntimePostgresConfigurationError("Invalid tenant identifier");
  }
  return normalized;
}

function assertActorId(actorId: string): string {
  const normalized = actorId.trim();
  if (!ACTOR_ID_PATTERN.test(normalized)) {
    throw new RuntimePostgresConfigurationError("Invalid runtime database actor");
  }
  return normalized;
}

let runtimePostgresPool: RuntimePostgresPool | null = null;
let runtimePostgresPoolFactoryForTests:
  | ((config: PoolConfig) => RuntimePostgresPool)
  | null = null;

export function __setRuntimePostgresPoolFactoryForTests(
  factory: ((config: PoolConfig) => RuntimePostgresPool) | null,
): void {
  if (process.env.NODE_ENV !== "test") {
    throw new Error("Runtime PostgreSQL pool factory is test-only");
  }
  runtimePostgresPoolFactoryForTests = factory;
  runtimePostgresPool = null;
}

function getRuntimePostgresPool(): RuntimePostgresPool {
  if (runtimePostgresPool) return runtimePostgresPool;

  const database = resolveRuntimePostgresConfig();
  const config: PoolConfig = {
    host: database.host,
    port: database.port,
    database: database.database,
    user: database.user,
    password: () => readPostgresPassword(database.passwordFile),
    ssl: {
      rejectUnauthorized: true,
      ...(database.sslCa ? { ca: database.sslCa } : {}),
    },
    application_name: "compliancehub-frontend-runtime",
    max: 4,
    min: 0,
    connectionTimeoutMillis: 5_000,
    idleTimeoutMillis: 10_000,
    maxLifetimeSeconds: 30 * 60,
    query_timeout: 15_000,
  };

  if (runtimePostgresPoolFactoryForTests) {
    runtimePostgresPool = runtimePostgresPoolFactoryForTests(config);
    return runtimePostgresPool;
  }

  const pool = new Pool(config);
  pool.on("error", () => {
    console.error("[runtime.postgres.pool_error]");
  });
  runtimePostgresPool = pool;
  return runtimePostgresPool;
}

async function withRuntimePostgresTransaction<T>(
  scope: { tenantId: string; platformAccess: boolean; actorId: string },
  operation: (client: PoolClient) => Promise<T>,
): Promise<T> {
  let client: PoolClient;
  try {
    client = await getRuntimePostgresPool().connect();
  } catch (error) {
    if (error instanceof RuntimePostgresConfigurationError) throw error;
    throw new RuntimePostgresOperationError(error);
  }
  let transactionOpen = false;
  let destroyClient = false;
  try {
    await client.query("BEGIN READ WRITE");
    transactionOpen = true;
    await client.query("SET LOCAL statement_timeout = '10s'");
    await client.query("SET LOCAL lock_timeout = '3s'");
    await client.query(
      "SELECT set_config('compliancehub.tenant_id', $1, true)",
      [scope.tenantId],
    );
    await client.query(
      "SELECT set_config('compliancehub.platform_access', $1, true)",
      [scope.platformAccess ? "true" : "false"],
    );
    await client.query(
      "SELECT set_config('compliancehub.actor_id', $1, true)",
      [scope.actorId],
    );
    const result = await operation(client);
    await client.query("COMMIT");
    transactionOpen = false;
    return result;
  } catch (error) {
    if (transactionOpen) {
      try {
        await client.query("ROLLBACK");
      } catch {
        destroyClient = true;
      }
    }
    if (
      error instanceof RuntimePostgresConfigurationError ||
      error instanceof RuntimePostgresOperationError
    ) {
      throw error;
    }
    throw new RuntimePostgresOperationError(error);
  } finally {
    client.release(destroyClient);
  }
}

export function withTenantRuntimePostgres<T>(
  tenantId: string,
  actorId: string,
  operation: (client: PoolClient) => Promise<T>,
): Promise<T> {
  return withRuntimePostgresTransaction(
    {
      tenantId: assertTenantId(tenantId),
      platformAccess: false,
      actorId: assertActorId(actorId),
    },
    operation,
  );
}

export function withPlatformRuntimePostgres<T>(
  actorId: string,
  operation: (client: PoolClient) => Promise<T>,
): Promise<T> {
  return withRuntimePostgresTransaction(
    {
      tenantId: "__platform__",
      platformAccess: true,
      actorId: assertActorId(actorId),
    },
    operation,
  );
}

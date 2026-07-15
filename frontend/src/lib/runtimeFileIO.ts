import "server-only";

import {
  ClientAssertionCredential,
  DefaultAzureCredential,
  ManagedIdentityCredential,
} from "@azure/identity";
import {
  BlobServiceClient,
  type ContainerClient,
} from "@azure/storage-blob";
import { getVercelOidcToken } from "@vercel/oidc";
import { createHash, randomUUID } from "node:crypto";
import {
  appendFile,
  chmod,
  mkdir,
  readFile,
  rename,
  unlink,
  writeFile,
} from "node:fs/promises";
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  sep,
} from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

const RUNTIME_DOCUMENT_MAX_BYTES = 32 * 1024 * 1024;
const RUNTIME_APPEND_MAX_BYTES = 256 * 1024;
const DEFAULT_BLOB_PREFIX = "compliancehub/runtime/v1";
const ACCOUNT_NAME_PATTERN = /^[a-z0-9]{3,24}$/;
const CONTAINER_NAME_PATTERN = /^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$/;
const PREFIX_PATTERN = /^[a-z0-9](?:[a-z0-9/_-]{0,126}[a-z0-9])?$/;

type RuntimeStorageBackend = "local" | "azure_blob";
type AzureAuthMode = "managed_identity" | "vercel_oidc" | "default";
type RuntimeEnvironment = Readonly<Record<string, string | undefined>>;

export class RuntimeStorageNotFoundError extends Error {
  constructor() {
    super("Runtime storage object not found");
    this.name = "RuntimeStorageNotFoundError";
  }
}

export class RuntimeStorageConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RuntimeStorageConfigurationError";
  }
}

export class RuntimeStorageOperationError extends Error {
  constructor(operation: "read" | "write" | "append" | "lock", cause: unknown) {
    super(`Runtime storage ${operation} failed`, { cause });
    this.name = "RuntimeStorageOperationError";
  }
}

export function isRuntimeStorageNotFoundError(
  error: unknown,
): error is RuntimeStorageNotFoundError {
  return error instanceof RuntimeStorageNotFoundError;
}

export function absoluteRuntimeFilePath(path: string): string {
  if (!isAbsolute(path)) {
    throw new RuntimeStorageConfigurationError("Runtime file paths must be absolute");
  }
  return path;
}

function isProductionRuntime(env: RuntimeEnvironment): boolean {
  return env.NODE_ENV === "production" || Boolean(env.VERCEL);
}

export function resolveRuntimeStorageBackend(
  env: RuntimeEnvironment = process.env,
): RuntimeStorageBackend {
  const configured = env.COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND?.trim().toLowerCase();
  if (configured === "azure_blob") return "azure_blob";
  if (configured === "local") {
    if (isProductionRuntime(env)) {
      throw new RuntimeStorageConfigurationError(
        "Local runtime storage is forbidden in production",
      );
    }
    return "local";
  }
  if (configured) {
    throw new RuntimeStorageConfigurationError("Unsupported runtime storage backend");
  }
  if (isProductionRuntime(env)) {
    throw new RuntimeStorageConfigurationError(
      "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be azure_blob in production",
    );
  }
  return "local";
}

export function resolveAzureAuthMode(
  env: RuntimeEnvironment = process.env,
): AzureAuthMode {
  const configured = env.COMPLIANCEHUB_RUNTIME_STORAGE_AUTH?.trim().toLowerCase();
  if (
    configured === "managed_identity" ||
    configured === "vercel_oidc" ||
    configured === "default"
  ) {
    if (configured === "default" && isProductionRuntime(env)) {
      throw new RuntimeStorageConfigurationError(
        "Default Azure credential chaining is forbidden in production",
      );
    }
    return configured;
  }
  if (configured) {
    throw new RuntimeStorageConfigurationError("Unsupported Azure authentication mode");
  }
  if (env.VERCEL) return "vercel_oidc";
  if (env.NODE_ENV === "production") return "managed_identity";
  return "default";
}

function requiredEnv(name: string, env: RuntimeEnvironment): string {
  const value = env[name]?.trim();
  if (!value) {
    throw new RuntimeStorageConfigurationError(`${name} is required`);
  }
  return value;
}

function blobPrefix(env: RuntimeEnvironment): string {
  const prefix = env.COMPLIANCEHUB_RUNTIME_STORAGE_PREFIX?.trim() || DEFAULT_BLOB_PREFIX;
  if (!PREFIX_PATTERN.test(prefix) || prefix.includes("..") || prefix.includes("//")) {
    throw new RuntimeStorageConfigurationError("Invalid runtime storage prefix");
  }
  return prefix;
}

function encodeBlobPath(path: string): string {
  return path
    .split(sep)
    .filter(Boolean)
    .map((part) => encodeURIComponent(part))
    .join("/");
}

export function runtimeBlobNameFromPath(
  path: string,
  env: RuntimeEnvironment = process.env,
  workingDirectory = process.cwd(),
): string {
  const absolutePath = absoluteRuntimeFilePath(path);
  const cwdRelative = relative(workingDirectory, absolutePath);
  const isWithinCwd =
    cwdRelative !== "" &&
    cwdRelative !== ".." &&
    !cwdRelative.startsWith(`..${sep}`) &&
    !isAbsolute(cwdRelative);
  const logicalName = isWithinCwd
    ? encodeBlobPath(cwdRelative)
    : dirname(absolutePath) === "/tmp"
      ? encodeURIComponent(basename(absolutePath))
      : `external/${createHash("sha256").update(absolutePath).digest("hex").slice(0, 24)}/${encodeURIComponent(basename(absolutePath))}`;
  if (!logicalName) {
    throw new RuntimeStorageConfigurationError("Runtime storage object name is empty");
  }
  return `${blobPrefix(env)}/${logicalName}`;
}

function isNotFoundCause(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { code?: unknown; statusCode?: unknown };
  return (
    candidate.code === "ENOENT" ||
    (candidate.statusCode === 404 && candidate.code === "BlobNotFound")
  );
}

function isExistingLockBlob(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { code?: unknown; statusCode?: unknown };
  return (
    (candidate.statusCode === 409 && candidate.code === "BlobAlreadyExists") ||
    (candidate.statusCode === 412 && candidate.code === "ConditionNotMet")
  );
}

function isLeaseBusy(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { code?: unknown; statusCode?: unknown };
  return (
    candidate.statusCode === 409 &&
    (candidate.code === "LeaseAlreadyPresent" ||
      candidate.code === "LeaseIsBreakingAndCannotBeAcquired")
  );
}

function assertContentSize(
  content: Buffer,
  limit: number,
  operation: "write" | "append",
): void {
  if (content.byteLength > limit) {
    throw new RuntimeStorageOperationError(
      operation,
      new Error("Runtime object exceeds size limit"),
    );
  }
}

async function ensureParentDirectory(path: string): Promise<void> {
  await mkdir(/* turbopackIgnore: true */ dirname(path), {
    recursive: true,
    mode: 0o700,
  });
}

async function readLocalTextFile(path: string): Promise<string> {
  try {
    const content = await readFile(/* turbopackIgnore: true */ path);
    if (content.byteLength > RUNTIME_DOCUMENT_MAX_BYTES) {
      throw new Error("Runtime object exceeds read limit");
    }
    return content.toString("utf8");
  } catch (error) {
    if (isNotFoundCause(error)) throw new RuntimeStorageNotFoundError();
    throw new RuntimeStorageOperationError("read", error);
  }
}

async function writeLocalTextFile(path: string, content: Buffer): Promise<void> {
  const temporaryPath = `${path}.${randomUUID()}.tmp`;
  try {
    await ensureParentDirectory(path);
    await writeFile(/* turbopackIgnore: true */ temporaryPath, content, {
      flag: "wx",
      mode: 0o600,
    });
    await rename(
      /* turbopackIgnore: true */ temporaryPath,
      /* turbopackIgnore: true */ path,
    );
  } catch (error) {
    await unlink(/* turbopackIgnore: true */ temporaryPath).catch(() => undefined);
    throw new RuntimeStorageOperationError("write", error);
  }
}

async function appendLocalTextFile(path: string, content: Buffer): Promise<void> {
  try {
    await ensureParentDirectory(path);
    await appendFile(/* turbopackIgnore: true */ path, content, {
      mode: 0o600,
    });
    await chmod(/* turbopackIgnore: true */ path, 0o600);
  } catch (error) {
    throw new RuntimeStorageOperationError("append", error);
  }
}

let azureContainerClient: ContainerClient | null = null;
let azureContainerClientFactoryForTests: (() => ContainerClient) | null = null;

export function __setAzureContainerClientFactoryForTests(
  factory: (() => ContainerClient) | null,
): void {
  if (process.env.NODE_ENV !== "test") {
    throw new Error("Azure runtime storage test factory is test-only");
  }
  azureContainerClientFactoryForTests = factory;
  azureContainerClient = null;
}

function getAzureContainerClient(): ContainerClient {
  if (azureContainerClient) return azureContainerClient;
  if (azureContainerClientFactoryForTests) {
    azureContainerClient = azureContainerClientFactoryForTests();
    return azureContainerClient;
  }

  const accountName = requiredEnv("AZURE_STORAGE_ACCOUNT_NAME", process.env);
  const containerName = requiredEnv("AZURE_STORAGE_CONTAINER_NAME", process.env);
  if (!ACCOUNT_NAME_PATTERN.test(accountName)) {
    throw new RuntimeStorageConfigurationError("Invalid Azure Storage account name");
  }
  if (!CONTAINER_NAME_PATTERN.test(containerName)) {
    throw new RuntimeStorageConfigurationError("Invalid Azure Blob container name");
  }

  const authMode = resolveAzureAuthMode();
  const credential = (() => {
    if (authMode === "managed_identity") {
      const clientId = process.env.AZURE_CLIENT_ID?.trim();
      return new ManagedIdentityCredential(clientId ? { clientId } : undefined);
    }
    if (authMode === "vercel_oidc") {
      return new ClientAssertionCredential(
        requiredEnv("AZURE_TENANT_ID", process.env),
        requiredEnv("AZURE_CLIENT_ID", process.env),
        getVercelOidcToken,
      );
    }
    return new DefaultAzureCredential();
  })();

  const serviceClient = new BlobServiceClient(
    `https://${accountName}.blob.core.windows.net`,
    credential,
  );
  azureContainerClient = serviceClient.getContainerClient(containerName);
  return azureContainerClient;
}

async function readAzureTextFile(path: string): Promise<string> {
  try {
    const blob = getAzureContainerClient().getBlockBlobClient(
      runtimeBlobNameFromPath(path),
    );
    const content = await blob.downloadToBuffer(0, RUNTIME_DOCUMENT_MAX_BYTES + 1);
    if (content.byteLength > RUNTIME_DOCUMENT_MAX_BYTES) {
      throw new Error("Runtime object exceeds read limit");
    }
    return content.toString("utf8");
  } catch (error) {
    if (isNotFoundCause(error)) throw new RuntimeStorageNotFoundError();
    throw new RuntimeStorageOperationError("read", error);
  }
}

async function writeAzureTextFile(path: string, content: Buffer): Promise<void> {
  try {
    const blob = getAzureContainerClient().getBlockBlobClient(
      runtimeBlobNameFromPath(path),
    );
    await blob.uploadData(content, {
      blobHTTPHeaders: {
        blobCacheControl: "private, no-store",
        blobContentType: "application/json; charset=utf-8",
      },
    });
  } catch (error) {
    throw new RuntimeStorageOperationError("write", error);
  }
}

async function appendAzureTextFile(path: string, content: Buffer): Promise<void> {
  try {
    const blob = getAzureContainerClient().getAppendBlobClient(
      runtimeBlobNameFromPath(path),
    );
    await blob.createIfNotExists({
      blobHTTPHeaders: {
        blobCacheControl: "private, no-store",
        blobContentType: "application/x-ndjson; charset=utf-8",
      },
    });
    await blob.appendBlock(content, content.byteLength);
  } catch (error) {
    throw new RuntimeStorageOperationError("append", error);
  }
}

const localLockTails = new Map<string, Promise<void>>();

async function withLocalRuntimeStorageLock<T>(
  path: string,
  operation: () => Promise<T>,
): Promise<T> {
  const previous = localLockTails.get(path) ?? Promise.resolve();
  let release: () => void = () => undefined;
  const current = new Promise<void>((resolve) => {
    release = resolve;
  });
  const tail = previous.then(() => current);
  localLockTails.set(path, tail);
  await previous;
  try {
    return await operation();
  } finally {
    release();
    if (localLockTails.get(path) === tail) localLockTails.delete(path);
  }
}

async function withAzureRuntimeStorageLock<T>(
  path: string,
  operation: () => Promise<T>,
): Promise<T> {
  const objectName = runtimeBlobNameFromPath(path);
  const lockName = `${blobPrefix(process.env)}/locks/${createHash("sha256").update(objectName).digest("hex")}.lock`;
  const lockBlob = getAzureContainerClient().getBlockBlobClient(lockName);
  try {
    await lockBlob.uploadData(Buffer.alloc(0), {
      conditions: { ifNoneMatch: "*" },
      blobHTTPHeaders: {
        blobCacheControl: "private, no-store",
        blobContentType: "application/octet-stream",
      },
    });
  } catch (error) {
    if (!isExistingLockBlob(error)) {
      throw new RuntimeStorageOperationError("lock", error);
    }
  }

  const lease = lockBlob.getBlobLeaseClient(randomUUID());
  let acquired = false;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      await lease.acquireLease(60);
      acquired = true;
      break;
    } catch (error) {
      if (!isLeaseBusy(error)) {
        throw new RuntimeStorageOperationError("lock", error);
      }
      await sleep(50 + attempt * 25);
    }
  }
  if (!acquired) {
    throw new RuntimeStorageOperationError("lock", new Error("Azure Blob lease timeout"));
  }

  let operationError: unknown;
  try {
    return await operation();
  } catch (error) {
    operationError = error;
    throw error;
  } finally {
    try {
      await lease.releaseLease();
    } catch (error) {
      if (!operationError) throw new RuntimeStorageOperationError("lock", error);
    }
  }
}

export function withRuntimeStorageLock<T>(
  path: string,
  operation: () => Promise<T>,
): Promise<T> {
  const absolutePath = absoluteRuntimeFilePath(path);
  return resolveRuntimeStorageBackend() === "azure_blob"
    ? withAzureRuntimeStorageLock(absolutePath, operation)
    : withLocalRuntimeStorageLock(absolutePath, operation);
}

export function readRuntimeTextFile(path: string): Promise<string> {
  const absolutePath = absoluteRuntimeFilePath(path);
  return resolveRuntimeStorageBackend() === "azure_blob"
    ? readAzureTextFile(absolutePath)
    : readLocalTextFile(absolutePath);
}

export function writeRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const buffer = Buffer.from(content, "utf8");
  assertContentSize(buffer, RUNTIME_DOCUMENT_MAX_BYTES, "write");
  return resolveRuntimeStorageBackend() === "azure_blob"
    ? writeAzureTextFile(absolutePath, buffer)
    : writeLocalTextFile(absolutePath, buffer);
}

export function appendRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const buffer = Buffer.from(content, "utf8");
  assertContentSize(buffer, RUNTIME_APPEND_MAX_BYTES, "append");
  return resolveRuntimeStorageBackend() === "azure_blob"
    ? appendAzureTextFile(absolutePath, buffer)
    : appendLocalTextFile(absolutePath, buffer);
}

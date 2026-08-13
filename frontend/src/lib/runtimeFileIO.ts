import "server-only";

import {
  GetObjectCommand,
  PutObjectCommand,
  S3Client,
  type S3ClientConfig,
} from "@aws-sdk/client-s3";
import { createHash } from "node:crypto";
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  sep,
} from "node:path";
import { withPlatformRuntimePostgres } from "@/lib/runtimePostgres";
import { readMountedServerSecretFile } from "@/lib/serverSecret";

const RUNTIME_DOCUMENT_MAX_BYTES = 32 * 1024 * 1024;
const RUNTIME_APPEND_MAX_BYTES = 256 * 1024;
const DEFAULT_BLOB_PREFIX = "compliancehub/runtime/v1";
const S3_BUCKET_NAME_PATTERN = /^[a-z0-9](?:[a-z0-9.-]{1,61}[a-z0-9])?$/;
const PREFIX_PATTERN = /^[a-z0-9](?:[a-z0-9/_-]{0,126}[a-z0-9])?$/;

type RuntimeStorageBackend = "local" | "s3";
type RuntimeEnvironment = Readonly<Record<string, string | undefined>>;
type S3RuntimeClient = Pick<S3Client, "send">;

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
  return (
    env.NODE_ENV === "production" ||
    env.COMPLIANCEHUB_RELEASE_CHANNEL === "production"
  );
}

export function resolveRuntimeStorageBackend(
  env: RuntimeEnvironment = process.env,
): RuntimeStorageBackend {
  const configured = env.COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND?.trim().toLowerCase();
  if (configured === "s3") return "s3";
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
      "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND must be s3 in production",
    );
  }
  return "local";
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

const developmentRuntimeObjects = new Map<string, Buffer>();

async function readLocalTextFile(path: string): Promise<string> {
  const content = developmentRuntimeObjects.get(path);
  if (!content) throw new RuntimeStorageNotFoundError();
  if (content.byteLength > RUNTIME_DOCUMENT_MAX_BYTES) {
    throw new RuntimeStorageOperationError(
      "read",
      new Error("Runtime object exceeds read limit"),
    );
  }
  return content.toString("utf8");
}

async function writeLocalTextFile(path: string, content: Buffer): Promise<void> {
  developmentRuntimeObjects.set(path, Buffer.from(content));
}

async function appendLocalTextFile(path: string, content: Buffer): Promise<void> {
  const previous = developmentRuntimeObjects.get(path) ?? Buffer.alloc(0);
  const combined = Buffer.concat([previous, content]);
  assertContentSize(combined, RUNTIME_DOCUMENT_MAX_BYTES, "append");
  developmentRuntimeObjects.set(path, combined);
}

const DEFAULT_HETZNER_S3_HOSTS = new Set([
  "fsn1.your-objectstorage.com",
  "nbg1.your-objectstorage.com",
]);

function resolveS3Endpoint(env: RuntimeEnvironment): URL {
  let endpoint: URL;
  try {
    endpoint = new URL(requiredEnv("COMPLIANCEHUB_S3_ENDPOINT", env));
  } catch {
    throw new RuntimeStorageConfigurationError("COMPLIANCEHUB_S3_ENDPOINT must be a valid URL");
  }
  if (
    endpoint.username ||
    endpoint.password ||
    endpoint.pathname !== "/" ||
    endpoint.search ||
    endpoint.hash
  ) {
    throw new RuntimeStorageConfigurationError(
      "COMPLIANCEHUB_S3_ENDPOINT must be a bare origin without credentials",
    );
  }
  if (isProductionRuntime(env) && endpoint.protocol !== "https:") {
    throw new RuntimeStorageConfigurationError(
      "COMPLIANCEHUB_S3_ENDPOINT must use HTTPS in production",
    );
  }
  const allowedHosts = new Set([
    ...DEFAULT_HETZNER_S3_HOSTS,
    ...(env.COMPLIANCEHUB_S3_ALLOWED_HOSTS || "")
      .split(",")
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean),
  ]);
  if (isProductionRuntime(env) && !allowedHosts.has(endpoint.hostname.toLowerCase())) {
    throw new RuntimeStorageConfigurationError(
      "S3 endpoint host is not in COMPLIANCEHUB_S3_ALLOWED_HOSTS",
    );
  }
  return endpoint;
}

async function readSecretFile(name: string, env: RuntimeEnvironment): Promise<string> {
  const path = requiredEnv(name, env);
  try {
    return readMountedServerSecretFile({
      fileVariable: name,
      filePath: path,
      maximumBytes: 4096,
    });
  } catch (error) {
    throw new RuntimeStorageConfigurationError(
      `${name} cannot be read (${error instanceof Error ? error.name : "Error"})`,
    );
  }
}

function s3Bucket(env: RuntimeEnvironment): string {
  const bucket = requiredEnv("COMPLIANCEHUB_S3_BUCKET", env).toLowerCase();
  if (!S3_BUCKET_NAME_PATTERN.test(bucket) || bucket.includes("..")) {
    throw new RuntimeStorageConfigurationError("Invalid S3 bucket name");
  }
  return bucket;
}

let s3RuntimeClient: S3RuntimeClient | null = null;
let s3RuntimeClientFactoryForTests: ((config: S3ClientConfig) => S3RuntimeClient) | null = null;

export function __setS3RuntimeClientFactoryForTests(
  factory: ((config: S3ClientConfig) => S3RuntimeClient) | null,
): void {
  if (process.env.NODE_ENV !== "test") {
    throw new Error("S3 runtime storage test factory is test-only");
  }
  s3RuntimeClientFactoryForTests = factory;
  s3RuntimeClient = null;
}

function getS3RuntimeClient(): S3RuntimeClient {
  if (s3RuntimeClient) return s3RuntimeClient;
  const endpoint = resolveS3Endpoint(process.env);
  const config: S3ClientConfig = {
    endpoint: endpoint.origin,
    region: requiredEnv("COMPLIANCEHUB_S3_REGION", process.env),
    forcePathStyle: process.env.COMPLIANCEHUB_S3_FORCE_PATH_STYLE === "true",
    credentials: async () => ({
      accessKeyId: await readSecretFile("COMPLIANCEHUB_S3_ACCESS_KEY_FILE", process.env),
      secretAccessKey: await readSecretFile(
        "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE",
        process.env,
      ),
    }),
  };
  s3RuntimeClient = s3RuntimeClientFactoryForTests
    ? s3RuntimeClientFactoryForTests(config)
    : new S3Client(config);
  return s3RuntimeClient;
}

function isS3NotFoundCause(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { name?: unknown; Code?: unknown; $metadata?: { httpStatusCode?: number } };
  return (
    candidate.name === "NoSuchKey" ||
    candidate.Code === "NoSuchKey" ||
    (candidate.name === "NotFound" && candidate.$metadata?.httpStatusCode === 404)
  );
}

async function readS3TextFile(path: string): Promise<string> {
  try {
    const response = await getS3RuntimeClient().send(
      new GetObjectCommand({
        Bucket: s3Bucket(process.env),
        Key: runtimeBlobNameFromPath(path),
      }),
    );
    if (!response.Body) throw new Error("S3 object response has no body");
    const content = Buffer.from(await response.Body.transformToByteArray());
    if (content.byteLength > RUNTIME_DOCUMENT_MAX_BYTES) {
      throw new Error("Runtime object exceeds read limit");
    }
    return content.toString("utf8");
  } catch (error) {
    if (isS3NotFoundCause(error)) throw new RuntimeStorageNotFoundError();
    throw new RuntimeStorageOperationError("read", error);
  }
}

async function writeS3TextFile(path: string, content: Buffer): Promise<void> {
  try {
    await getS3RuntimeClient().send(
      new PutObjectCommand({
        Bucket: s3Bucket(process.env),
        Key: runtimeBlobNameFromPath(path),
        Body: content,
        CacheControl: "private, no-store",
        ContentType: "application/json; charset=utf-8",
      }),
    );
  } catch (error) {
    throw new RuntimeStorageOperationError("write", error);
  }
}

async function withS3RuntimeStorageLock<T>(
  path: string,
  operation: () => Promise<T>,
): Promise<T> {
  const objectName = runtimeBlobNameFromPath(path);
  return withPlatformRuntimePostgres("system:runtime-storage-lock", async (client) => {
    await client.query("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [objectName]);
    return operation();
  });
}

async function appendS3TextFile(path: string, content: Buffer): Promise<void> {
  await withS3RuntimeStorageLock(path, async () => {
    let previous = Buffer.alloc(0);
    try {
      previous = Buffer.from(await readS3TextFile(path), "utf8");
    } catch (error) {
      if (!isRuntimeStorageNotFoundError(error)) throw error;
    }
    const combined = Buffer.concat([previous, content]);
    assertContentSize(combined, RUNTIME_DOCUMENT_MAX_BYTES, "append");
    await writeS3TextFile(path, combined);
  });
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

export function withRuntimeStorageLock<T>(
  path: string,
  operation: () => Promise<T>,
): Promise<T> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const backend = resolveRuntimeStorageBackend();
  if (backend === "s3") return withS3RuntimeStorageLock(absolutePath, operation);
  return withLocalRuntimeStorageLock(absolutePath, operation);
}

export function readRuntimeTextFile(path: string): Promise<string> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const backend = resolveRuntimeStorageBackend();
  if (backend === "s3") return readS3TextFile(absolutePath);
  return readLocalTextFile(absolutePath);
}

export function writeRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const buffer = Buffer.from(content, "utf8");
  assertContentSize(buffer, RUNTIME_DOCUMENT_MAX_BYTES, "write");
  const backend = resolveRuntimeStorageBackend();
  if (backend === "s3") return writeS3TextFile(absolutePath, buffer);
  return writeLocalTextFile(absolutePath, buffer);
}

export function appendRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  const buffer = Buffer.from(content, "utf8");
  assertContentSize(buffer, RUNTIME_APPEND_MAX_BYTES, "append");
  const backend = resolveRuntimeStorageBackend();
  if (backend === "s3") return appendS3TextFile(absolutePath, buffer);
  return appendLocalTextFile(absolutePath, buffer);
}

import "server-only";

import {
  closeSync,
  constants,
  fstatSync,
  openSync,
  readSync,
} from "node:fs";
import { isAbsolute } from "node:path";

const MAX_SECRET_BYTES = 64 * 1024;
const APPROVED_SECRET_MODES = new Set([0o400, 0o600]);

export class ServerSecretConfigurationError extends Error {}

type ServerSecretOptions = {
  environmentVariable: string;
  fileEnvironmentVariable: string;
  minimumBytes?: number;
  required?: boolean;
};

type MountedServerSecretFileOptions = {
  fileVariable: string;
  filePath: string;
  minimumBytes?: number;
  maximumBytes?: number;
};

function productionRuntime(): boolean {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production"
  );
}

export function readMountedServerSecretFile(
  options: MountedServerSecretFileOptions,
): string {
  const { fileVariable, filePath } = options;
  const minimumBytes = options.minimumBytes ?? 1;
  const maximumBytes = options.maximumBytes ?? MAX_SECRET_BYTES;
  if (
    !Number.isSafeInteger(minimumBytes) ||
    !Number.isSafeInteger(maximumBytes) ||
    minimumBytes < 1 ||
    maximumBytes < minimumBytes ||
    maximumBytes > MAX_SECRET_BYTES
  ) {
    throw new ServerSecretConfigurationError(
      `${fileVariable} has an invalid secret-size policy`,
    );
  }
  if (!isAbsolute(filePath)) {
    throw new ServerSecretConfigurationError(
      `${fileVariable} must contain an absolute path`,
    );
  }

  let descriptor: number | null = null;
  try {
    if (typeof constants.O_NOFOLLOW !== "number") {
      throw new ServerSecretConfigurationError(
        `${fileVariable} requires O_NOFOLLOW support`,
      );
    }
    try {
      descriptor = openSync(filePath, constants.O_RDONLY | constants.O_NOFOLLOW);
    } catch {
      throw new ServerSecretConfigurationError(
        `${fileVariable} must reference an accessible regular file, not a symlink`,
      );
    }
    const openedMetadata = fstatSync(descriptor);
    const openedMode = openedMetadata.mode & 0o777;
    if (!openedMetadata.isFile()) {
      throw new ServerSecretConfigurationError(
        `${fileVariable} must reference a regular file`,
      );
    }
    if (!APPROVED_SECRET_MODES.has(openedMode)) {
      throw new ServerSecretConfigurationError(
        `${fileVariable} must use mode 0400 or 0600`,
      );
    }
    if (openedMetadata.size < 1 || openedMetadata.size > maximumBytes) {
      throw new ServerSecretConfigurationError(
        `${fileVariable} has an invalid secret-file size`,
      );
    }
    const content = Buffer.alloc(maximumBytes + 1);
    let totalBytes = 0;
    while (totalBytes <= maximumBytes) {
      const bytesRead = readSync(
        descriptor,
        content,
        totalBytes,
        content.byteLength - totalBytes,
        null,
      );
      if (bytesRead === 0) break;
      totalBytes += bytesRead;
    }
    const finalMetadata = fstatSync(descriptor);
    if (
      totalBytes > maximumBytes ||
      totalBytes !== openedMetadata.size ||
      finalMetadata.dev !== openedMetadata.dev ||
      finalMetadata.ino !== openedMetadata.ino ||
      finalMetadata.size !== openedMetadata.size ||
      !APPROVED_SECRET_MODES.has(finalMetadata.mode & 0o777)
    ) {
      throw new ServerSecretConfigurationError(
        `${fileVariable} changed during secure read`,
      );
    }
    const value = content.subarray(0, totalBytes).toString("utf8").trim();
    if (Buffer.byteLength(value, "utf8") < minimumBytes) {
      throw new ServerSecretConfigurationError(
        `${fileVariable} must contain at least ${minimumBytes} bytes`,
      );
    }
    return value;
  } finally {
    if (descriptor !== null) closeSync(descriptor);
  }
}

export function readServerSecret(options: ServerSecretOptions): string | null {
  const directValue = process.env[options.environmentVariable]?.trim() || "";
  const filePath = process.env[options.fileEnvironmentVariable]?.trim() || "";

  if (directValue && filePath) {
    throw new ServerSecretConfigurationError(
      `${options.environmentVariable} and ${options.fileEnvironmentVariable} are mutually exclusive`,
    );
  }
  if (productionRuntime() && directValue) {
    throw new ServerSecretConfigurationError(
      `${options.environmentVariable} is forbidden in production; use ${options.fileEnvironmentVariable}`,
    );
  }

  const value = filePath
    ? readMountedServerSecretFile({
        fileVariable: options.fileEnvironmentVariable,
        filePath,
        minimumBytes: options.minimumBytes,
      })
    : directValue;
  if (!value) {
    if (options.required) {
      throw new ServerSecretConfigurationError(
        `${options.fileEnvironmentVariable} is required`,
      );
    }
    return null;
  }

  const minimumBytes = options.minimumBytes ?? 1;
  if (Buffer.byteLength(value, "utf8") < minimumBytes) {
    throw new ServerSecretConfigurationError(
      `${options.fileEnvironmentVariable} must contain at least ${minimumBytes} bytes`,
    );
  }
  return value;
}

export function serverSecretIsConfigured(
  environmentVariable: string,
  fileEnvironmentVariable: string,
): boolean {
  if (productionRuntime()) {
    return Boolean(process.env[fileEnvironmentVariable]?.trim());
  }
  return Boolean(
    process.env[fileEnvironmentVariable]?.trim() ||
      process.env[environmentVariable]?.trim(),
  );
}

import "server-only";

import { appendFile, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname, isAbsolute } from "node:path";

export function absoluteRuntimeFilePath(path: string): string {
  if (!isAbsolute(path)) {
    throw new Error("Runtime file paths must be absolute");
  }
  return path;
}

async function ensureParentDirectory(path: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  await mkdir(/* turbopackIgnore: true */ dirname(absolutePath), { recursive: true });
}

export function readRuntimeTextFile(path: string): Promise<string> {
  const absolutePath = absoluteRuntimeFilePath(path);
  return readFile(/* turbopackIgnore: true */ absolutePath, "utf8");
}

export async function writeRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  await ensureParentDirectory(absolutePath);
  await writeFile(/* turbopackIgnore: true */ absolutePath, content, "utf8");
}

export async function appendRuntimeTextFile(path: string, content: string): Promise<void> {
  const absolutePath = absoluteRuntimeFilePath(path);
  await ensureParentDirectory(absolutePath);
  await appendFile(/* turbopackIgnore: true */ absolutePath, content, "utf8");
}

export function replaceRuntimeFile(source: string, destination: string): Promise<void> {
  const absoluteSource = absoluteRuntimeFilePath(source);
  const absoluteDestination = absoluteRuntimeFilePath(destination);
  return rename(
    /* turbopackIgnore: true */ absoluteSource,
    /* turbopackIgnore: true */ absoluteDestination,
  );
}

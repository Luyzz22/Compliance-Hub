#!/usr/bin/env node
/**
 * Wave 32 – GTM Alert-Check für selbst betriebenen Cron bzw. n8n HTTP-Request.
 *
 * Env:
 *   COMPLIANCEHUB_BASE_URL  z. B. https://app.example.com (ohne Slash am Ende)
 *   GTM_ALERT_SECRET_FILE oder LEAD_ADMIN_SECRET_FILE (OpenBao-Mount)
 *
 * Exit 0 immer, wenn HTTP OK; stderr bei Fehler.
 */

import { constants, closeSync, fstatSync, lstatSync, openSync, readFileSync } from "node:fs";
import { isAbsolute } from "node:path";

function readSecretFile(variableName) {
  const path = process.env[variableName]?.trim() || "";
  if (!path || !isAbsolute(path)) {
    throw new Error(`${variableName} must contain an absolute path`);
  }
  const metadata = lstatSync(path);
  const mode = metadata.mode & 0o777;
  if (!metadata.isFile() || metadata.isSymbolicLink() || ![0o400, 0o600].includes(mode)) {
    throw new Error(`${variableName} must reference a regular 0400/0600 file`);
  }
  const descriptor = openSync(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
  try {
    const opened = fstatSync(descriptor);
    if (opened.dev !== metadata.dev || opened.ino !== metadata.ino) {
      throw new Error(`${variableName} changed during validation`);
    }
    if (opened.size > 16_384) {
      throw new Error(`${variableName} exceeds the 16 KiB secret-file limit`);
    }
    return readFileSync(descriptor, "utf8").trim();
  } finally {
    closeSync(descriptor);
  }
}

const base = (process.env.COMPLIANCEHUB_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const production = process.env.COMPLIANCEHUB_RELEASE_CHANNEL === "production";
const directSecret = (process.env.GTM_ALERT_SECRET || process.env.LEAD_ADMIN_SECRET || "").trim();
if (production && directSecret) {
  console.error("gtm-alert-check: direct secrets are forbidden in production");
  process.exit(1);
}
let secret = directSecret;
try {
  if (!secret) {
    const fileVariable = process.env.GTM_ALERT_SECRET_FILE?.trim()
      ? "GTM_ALERT_SECRET_FILE"
      : "LEAD_ADMIN_SECRET_FILE";
    secret = readSecretFile(fileVariable);
  }
} catch (error) {
  console.error("gtm-alert-check:", error instanceof Error ? error.message : String(error));
  process.exit(1);
}
if (secret.length < 32) {
  console.error("gtm-alert-check: secret must contain at least 32 bytes");
  process.exit(1);
}

const url = new URL("/api/admin/gtm/alert-check", base);
if (production && url.protocol !== "https:") {
  console.error("gtm-alert-check: COMPLIANCEHUB_BASE_URL must use HTTPS in production");
  process.exit(1);
}

const res = await fetch(url, {
  method: "GET",
  redirect: "manual",
  headers: { Authorization: `Bearer ${secret}` },
});
const text = await res.text();
let json;
try {
  json = JSON.parse(text);
} catch {
  console.error("gtm-alert-check: non-JSON response", res.status, text.slice(0, 500));
  process.exit(1);
}

if (!res.ok) {
  console.error("gtm-alert-check: HTTP", res.status, json);
  process.exit(1);
}

console.log(JSON.stringify({ ok: json.ok, fired: json.fired, counts: json.counts }, null, 2));
if (json.summary_de) console.log(json.summary_de);
if (json.fired && json.findings?.length) {
  process.exitCode = 2;
}

import "server-only";

import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";

import { safeReturnTo } from "@/lib/safeReturnTo";

const VERSION = "v1";
const AAD = Buffer.from("compliancehub:entra-transaction:v1", "utf8");
const MAX_AGE_MS = 10 * 60 * 1000;
const MAX_CLOCK_SKEW_MS = 60 * 1000;

export type EntraTransaction = {
  state: string;
  nonce: string;
  codeVerifier: string;
  returnTo: string;
  providerId: string;
  createdAt: number;
};

function keyFromSecret(secret: string): Buffer {
  if (Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error(
      "COMPLIANCEHUB_AUTH_TRANSACTION_SECRET must contain 32 bytes",
    );
  }
  return createHash("sha256").update(secret, "utf8").digest();
}

function canonicalBase64Url(value: string): Buffer | null {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return null;
  const decoded = Buffer.from(value, "base64url");
  return decoded.toString("base64url") === value ? decoded : null;
}

function transactionIsValid(
  value: unknown,
  now: number,
): value is EntraTransaction {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<EntraTransaction>;
  return (
    typeof item.state === "string" &&
    item.state.length >= 32 &&
    item.state.length <= 256 &&
    typeof item.nonce === "string" &&
    item.nonce.length >= 32 &&
    item.nonce.length <= 256 &&
    typeof item.codeVerifier === "string" &&
    item.codeVerifier.length >= 43 &&
    item.codeVerifier.length <= 128 &&
    typeof item.returnTo === "string" &&
    item.returnTo === safeReturnTo(item.returnTo) &&
    typeof item.providerId === "string" &&
    /^[0-9a-f-]{36}$/i.test(item.providerId) &&
    typeof item.createdAt === "number" &&
    Number.isSafeInteger(item.createdAt) &&
    item.createdAt <= now + MAX_CLOCK_SKEW_MS &&
    now - item.createdAt <= MAX_AGE_MS
  );
}

export function sealEntraTransaction(
  transaction: EntraTransaction,
  secret: string,
): string {
  if (!transactionIsValid(transaction, transaction.createdAt)) {
    throw new Error("Invalid Entra transaction");
  }
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", keyFromSecret(secret), iv);
  cipher.setAAD(AAD);
  const ciphertext = Buffer.concat([
    cipher.update(JSON.stringify(transaction), "utf8"),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();
  return [VERSION, iv, tag, ciphertext]
    .map((part) =>
      typeof part === "string" ? part : part.toString("base64url"),
    )
    .join(".");
}

export function openEntraTransaction(
  sealed: string,
  secret: string,
  now = Date.now(),
): EntraTransaction | null {
  const parts = sealed.split(".");
  if (parts.length !== 4 || parts[0] !== VERSION || sealed.length > 4096)
    return null;
  try {
    const iv = canonicalBase64Url(parts[1]);
    const tag = canonicalBase64Url(parts[2]);
    const ciphertext = canonicalBase64Url(parts[3]);
    if (!iv || !tag || !ciphertext) return null;
    if (iv.length !== 12 || tag.length !== 16 || ciphertext.length === 0)
      return null;
    const decipher = createDecipheriv("aes-256-gcm", keyFromSecret(secret), iv);
    decipher.setAAD(AAD);
    decipher.setAuthTag(tag);
    const plaintext = Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);
    const parsed: unknown = JSON.parse(plaintext.toString("utf8"));
    return transactionIsValid(parsed, now) ? parsed : null;
  } catch {
    return null;
  }
}

export function secureValuesEqual(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left, "utf8");
  const rightBytes = Buffer.from(right, "utf8");
  return (
    leftBytes.length === rightBytes.length &&
    timingSafeEqual(leftBytes, rightBytes)
  );
}

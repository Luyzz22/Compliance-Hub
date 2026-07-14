import { describe, expect, it } from "vitest";

import {
  openEntraTransaction,
  sealEntraTransaction,
  secureValuesEqual,
  type EntraTransaction,
} from "@/lib/entraTransaction";

const SECRET = "entra-transaction-test-secret-at-least-32-bytes";
const NOW = 1_800_000_000_000;

function transaction(
  overrides: Partial<EntraTransaction> = {},
): EntraTransaction {
  return {
    state: "s".repeat(48),
    nonce: "n".repeat(48),
    codeVerifier: "v".repeat(64),
    returnTo: "/board/executive-dashboard",
    providerId: "11111111-1111-4111-8111-111111111111",
    createdAt: NOW,
    ...overrides,
  };
}

describe("Entra transaction envelope", () => {
  it("round-trips a valid encrypted transaction", () => {
    const sealed = sealEntraTransaction(transaction(), SECRET);
    expect(sealed).not.toContain("/board/executive-dashboard");
    expect(openEntraTransaction(sealed, SECRET, NOW)).toEqual(transaction());
  });

  it("rejects tampering, expiry, and unsafe return paths", () => {
    const sealed = sealEntraTransaction(transaction(), SECRET);
    const parts = sealed.split(".");
    parts[3] = `${parts[3][0] === "A" ? "B" : "A"}${parts[3].slice(1)}`;
    expect(openEntraTransaction(parts.join("."), SECRET, NOW)).toBeNull();
    expect(openEntraTransaction(`${sealed}=`, SECRET, NOW)).toBeNull();
    expect(
      openEntraTransaction(sealed, SECRET, NOW + 11 * 60 * 1000),
    ).toBeNull();
    expect(() =>
      sealEntraTransaction(
        transaction({ returnTo: "https://attacker.invalid" }),
        SECRET,
      ),
    ).toThrow("Invalid Entra transaction");
  });

  it("requires a sufficiently long encryption secret", () => {
    expect(() => sealEntraTransaction(transaction(), "short-secret")).toThrow(
      "must contain 32 bytes",
    );
  });

  it("compares protocol values without length-dependent partial matches", () => {
    expect(secureValuesEqual("same", "same")).toBe(true);
    expect(secureValuesEqual("same", "different")).toBe(false);
    expect(secureValuesEqual("same", "same-prefix")).toBe(false);
  });
});

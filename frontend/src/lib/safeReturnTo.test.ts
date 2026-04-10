import { describe, expect, it } from "vitest";

/**
 * Replicate the safeReturnTo logic from the login page for isolated unit testing.
 * This avoids importing the "use client" page module in Node tests.
 */
function safeReturnTo(raw: string | null): string {
  const fallback = "/board";
  if (!raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//")) return fallback;
  if (/^[a-z]+:/i.test(raw)) return fallback;
  try {
    const decoded = decodeURIComponent(raw);
    if (decoded.includes("\n") || decoded.includes("\r")) return fallback;
  } catch {
    return fallback;
  }
  return raw;
}

describe("safeReturnTo (login returnTo validation)", () => {
  it("returns /board when next is null", () => {
    expect(safeReturnTo(null)).toBe("/board");
  });

  it("returns /board when next is empty string", () => {
    expect(safeReturnTo("")).toBe("/board");
  });

  it("accepts a valid relative path", () => {
    expect(safeReturnTo("/board/gap-analysis")).toBe("/board/gap-analysis");
  });

  it("blocks absolute http URL (open redirect)", () => {
    expect(safeReturnTo("https://evil.com")).toBe("/board");
  });

  it("blocks absolute http URL without https", () => {
    expect(safeReturnTo("http://evil.com")).toBe("/board");
  });

  it("blocks protocol-relative URL", () => {
    expect(safeReturnTo("//evil.com")).toBe("/board");
  });

  it("blocks javascript: protocol", () => {
    expect(safeReturnTo("javascript:alert(1)")).toBe("/board");
  });

  it("accepts root path", () => {
    expect(safeReturnTo("/")).toBe("/");
  });

  it("accepts nested relative path", () => {
    expect(safeReturnTo("/tenant/compliance-overview")).toBe(
      "/tenant/compliance-overview",
    );
  });

  it("blocks newline injection in encoded URL", () => {
    expect(safeReturnTo("/board%0aSet-Cookie:evil")).toBe("/board");
  });

  it("blocks carriage return injection", () => {
    expect(safeReturnTo("/board%0d%0aInjected:header")).toBe("/board");
  });
});

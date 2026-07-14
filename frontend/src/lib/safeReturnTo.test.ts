import { describe, expect, it } from "vitest";

import { safeReturnTo } from "./safeReturnTo";

const FALLBACK = "/board/executive-dashboard";

describe("safeReturnTo (login returnTo validation)", () => {
  it("returns the dashboard when next is null", () => {
    expect(safeReturnTo(null)).toBe(FALLBACK);
  });

  it("returns the dashboard when next is empty string", () => {
    expect(safeReturnTo("")).toBe(FALLBACK);
  });

  it("accepts a valid relative path", () => {
    expect(safeReturnTo("/board/gap-analysis")).toBe("/board/gap-analysis");
  });

  it("blocks absolute http URL (open redirect)", () => {
    expect(safeReturnTo("https://evil.com")).toBe(FALLBACK);
  });

  it("blocks absolute http URL without https", () => {
    expect(safeReturnTo("http://evil.com")).toBe(FALLBACK);
  });

  it("blocks protocol-relative URL", () => {
    expect(safeReturnTo("//evil.com")).toBe(FALLBACK);
  });

  it("blocks javascript: protocol", () => {
    expect(safeReturnTo("javascript:alert(1)")).toBe(FALLBACK);
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
    expect(safeReturnTo("/board%0aSet-Cookie:evil")).toBe(FALLBACK);
  });

  it("blocks carriage return injection", () => {
    expect(safeReturnTo("/board%0d%0aInjected:header")).toBe(FALLBACK);
  });

  it("maps the board namespace root to an existing page", () => {
    expect(safeReturnTo("/board")).toBe(FALLBACK);
  });
});

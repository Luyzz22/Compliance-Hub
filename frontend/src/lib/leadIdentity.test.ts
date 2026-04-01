import { describe, expect, it } from "vitest";

import {
  buildLeadAccountKey,
  buildLeadContactKey,
  normalizeLeadCompany,
  normalizeLeadEmail,
} from "@/lib/leadIdentity";

describe("leadIdentity", () => {
  it("normalizes email consistently for contact keys", () => {
    const a = buildLeadContactKey(normalizeLeadEmail("  User@Example.COM "));
    const b = buildLeadContactKey(normalizeLeadEmail("user@example.com"));
    expect(a).toBe(b);
    expect(a.startsWith("ct_v1_")).toBe(true);
  });

  it("uses company hash when company present", () => {
    const k1 = buildLeadAccountKey("  Acme GmbH  ", "x@acme.de");
    const k2 = buildLeadAccountKey("acme gmbh", "y@acme.de");
    expect(k1).toBe(k2);
    expect(k1?.startsWith("ac_v1_co_")).toBe(true);
  });

  it("normalizes company whitespace", () => {
    expect(normalizeLeadCompany("Foo   Bar")).toBe("foo bar");
  });
});

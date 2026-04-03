import { describe, expect, it } from "vitest";

import {
  describePipedriveDealEligibility,
  isLeadPipedriveDealEligible,
} from "@/lib/pipedriveDealEligibility";

const base = {
  business_email: "a@firma.de",
  company: "Acme GmbH",
  segment: "sonstiges" as const,
  owner: "",
  triage_status: "qualified" as const,
};

describe("isLeadPipedriveDealEligible", () => {
  it("requires qualified triage and not spam", () => {
    expect(isLeadPipedriveDealEligible({ ...base, triage_status: "received" })).toBe(false);
    expect(isLeadPipedriveDealEligible({ ...base, triage_status: "spam" })).toBe(false);
    expect(isLeadPipedriveDealEligible({ ...base, triage_status: "qualified" })).toBe(true);
  });

  it("allows enterprise_sap without strong company", () => {
    expect(
      isLeadPipedriveDealEligible({
        ...base,
        company: "x",
        segment: "enterprise_sap",
        triage_status: "qualified",
      }),
    ).toBe(true);
  });

  it("allows owner without company when qualified", () => {
    expect(
      isLeadPipedriveDealEligible({
        ...base,
        company: "n/a",
        owner: "sales",
        segment: "sonstiges",
        triage_status: "qualified",
      }),
    ).toBe(true);
  });

  it("rejects weak company without segment or owner", () => {
    expect(
      isLeadPipedriveDealEligible({
        ...base,
        company: "test",
        segment: "sonstiges",
        owner: "",
        triage_status: "qualified",
      }),
    ).toBe(false);
  });

  it("describe includes eligible true for company path", () => {
    const d = describePipedriveDealEligibility(base);
    expect(d.eligible).toBe(true);
    expect(d.summary).toContain("Firma");
  });
});

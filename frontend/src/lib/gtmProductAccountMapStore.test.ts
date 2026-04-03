import { describe, expect, it } from "vitest";

import { findGtmProductMapEntry, type GtmProductAccountMapState } from "@/lib/gtmProductAccountMapStore";

describe("findGtmProductMapEntry", () => {
  it("matches account_key before domain", () => {
    const map: GtmProductAccountMapState = {
      entries: [
        { tenant_id: "t-domain", domain: "other.com" },
        { tenant_id: "t-key", account_key: "ac_v1_co_abc" },
      ],
    };
    const hit = findGtmProductMapEntry(map, {
      lead_account_key: "ac_v1_co_abc",
      business_email: "x@other.com",
    });
    expect(hit?.tenant_id).toBe("t-key");
  });

  it("matches email domain when no account_key hit", () => {
    const map: GtmProductAccountMapState = {
      entries: [{ tenant_id: "t1", domain: "kunde.de", label: "Kunde" }],
    };
    const hit = findGtmProductMapEntry(map, {
      lead_account_key: null,
      business_email: "Person@KUNDE.DE",
    });
    expect(hit?.tenant_id).toBe("t1");
  });
});

import { describe, expect, it } from "vitest";

import {
  attachContactRollups,
  mergeLeadsWithOps,
  sortInboxItems,
} from "@/lib/leadInboxMerge";
import {
  buildLeadAccountKey,
  buildLeadContactKey,
  normalizeLeadEmail,
} from "@/lib/leadIdentity";
import type { LeadAdminRow } from "@/lib/leadPersistence";
import type { LeadOpsFile } from "@/lib/leadOpsTypes";
import { LEAD_OUTBOUND_SCHEMA_VERSION } from "@/lib/leadOutbound";

function baseRow(over: Partial<LeadAdminRow> & { lead_id: string }): LeadAdminRow {
  const created = "2026-04-01T12:00:00.000Z";
  const email = "n@example.com";
  const ck = buildLeadContactKey(normalizeLeadEmail(email));
  const ak = buildLeadAccountKey("C", email);
  return {
    _kind: "lead_inquiry",
    lead_id: over.lead_id,
    trace_id: "t1",
    status: "received",
    created_at: created,
    outbound: {
      schema_version: LEAD_OUTBOUND_SCHEMA_VERSION,
      lead_id: over.lead_id,
      trace_id: "t1",
      timestamp: created,
      source_page: "/kontakt",
      segment: "sonstiges",
      name: "N",
      business_email: email,
      company: "C",
      message: "Hi",
      route: {
        route_key: "queue_other",
        queue_label: "Other",
        priority: "low",
        sla_bucket: "standard",
      },
      lead_contact_key: ck,
      lead_account_key: ak,
      contact_inquiry_sequence: 1,
      contact_first_seen_at: created,
      contact_latest_seen_at: created,
      duplicate_hint: "none",
    },
    lead_contact_key: ck,
    lead_account_key: ak,
    contact_inquiry_sequence: 1,
    contact_first_seen_at: created,
    contact_latest_seen_at: created,
    duplicate_hint: "none",
    ...over,
  };
}

describe("mergeLeadsWithOps", () => {
  it("marks needs_attention for failed webhook", () => {
    const ops: LeadOpsFile = { version: 1, entries: {} };
    const rows: LeadAdminRow[] = [
      baseRow({
        lead_id: "a",
        webhook_ok: false,
        status: "failed",
      }),
    ];
    const items = mergeLeadsWithOps(rows, ops);
    expect(items[0]?.needs_attention).toBe(true);
    expect(items[0]?.forwarding_status).toBe("failed");
  });

  it("sorts needs_attention before ok leads", () => {
    const ops: LeadOpsFile = { version: 1, entries: {} };
    const rows: LeadAdminRow[] = [
      baseRow({
        lead_id: "old-ok",
        created_at: "2026-04-01T10:00:00.000Z",
        webhook_ok: true,
        status: "forwarded",
      }),
      baseRow({
        lead_id: "new-fail",
        created_at: "2026-04-02T10:00:00.000Z",
        webhook_ok: false,
        status: "failed",
      }),
    ];
    const sorted = sortInboxItems(mergeLeadsWithOps(rows, ops));
    expect(sorted[0]?.lead_id).toBe("new-fail");
    expect(sorted[1]?.lead_id).toBe("old-ok");
  });
});

describe("attachContactRollups", () => {
  it("aggregates submission count for same email contact key", () => {
    const ops: LeadOpsFile = { version: 1, entries: {} };
    const email = "repeat@firma.de";
    const ck = buildLeadContactKey(normalizeLeadEmail(email));
    const ak = buildLeadAccountKey("Firma AG", email);
    const r1 = baseRow({
      lead_id: "l1",
      created_at: "2026-04-01T10:00:00.000Z",
      outbound: {
        ...baseRow({ lead_id: "l1" }).outbound,
        business_email: email,
        company: "Firma AG",
        lead_contact_key: ck,
        lead_account_key: ak,
      },
      lead_contact_key: ck,
      lead_account_key: ak,
    });
    const r2 = baseRow({
      lead_id: "l2",
      created_at: "2026-04-02T10:00:00.000Z",
      outbound: {
        ...baseRow({ lead_id: "l2" }).outbound,
        business_email: email,
        company: "Firma AG",
        lead_contact_key: ck,
        lead_account_key: ak,
        duplicate_hint: "same_email_repeat",
        contact_inquiry_sequence: 2,
      },
      lead_contact_key: ck,
      lead_account_key: ak,
      duplicate_hint: "same_email_repeat",
      contact_inquiry_sequence: 2,
    });
    const allRows = [r1, r2];
    const merged = mergeLeadsWithOps(allRows, ops);
    const rolled = attachContactRollups(merged, allRows, ops);
    const i2 = rolled.find((x) => x.lead_id === "l2");
    expect(i2?.contact_submission_count).toBe(2);
    expect(i2?.contact_inquiry_sequence).toBe(2);
  });
});

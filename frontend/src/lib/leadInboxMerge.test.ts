import { describe, expect, it } from "vitest";

import { mergeLeadsWithOps, sortInboxItems } from "@/lib/leadInboxMerge";
import type { LeadAdminRow } from "@/lib/leadPersistence";
import type { LeadOpsFile } from "@/lib/leadOpsTypes";
import { LEAD_OUTBOUND_SCHEMA_VERSION } from "@/lib/leadOutbound";

function baseRow(over: Partial<LeadAdminRow> & { lead_id: string }): LeadAdminRow {
  const created = "2026-04-01T12:00:00.000Z";
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
      business_email: "n@example.com",
      company: "C",
      message: "Hi",
      route: {
        route_key: "queue_other",
        queue_label: "Other",
        priority: "low",
        sla_bucket: "standard",
      },
    },
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

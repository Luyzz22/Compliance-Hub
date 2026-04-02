import { describe, expect, it } from "vitest";

import { computeLeadSyncIdempotencyKey, LEAD_SYNC_PAYLOAD_VERSION } from "@/lib/leadSyncPayload";

describe("computeLeadSyncIdempotencyKey", () => {
  it("is deterministic for same inputs", () => {
    const a = computeLeadSyncIdempotencyKey(
      "n8n_webhook",
      "550e8400-e29b-41d4-a716-446655440000",
      LEAD_SYNC_PAYLOAD_VERSION,
      "ingest:2026-04-01T12:00:00.000Z",
    );
    const b = computeLeadSyncIdempotencyKey(
      "n8n_webhook",
      "550e8400-e29b-41d4-a716-446655440000",
      LEAD_SYNC_PAYLOAD_VERSION,
      "ingest:2026-04-01T12:00:00.000Z",
    );
    expect(a).toBe(b);
    expect(a.startsWith("idem_")).toBe(true);
    expect(a.length).toBeGreaterThan(10);
  });

  it("differs when target or material revision changes", () => {
    const base = computeLeadSyncIdempotencyKey(
      "n8n_webhook",
      "550e8400-e29b-41d4-a716-446655440000",
      LEAD_SYNC_PAYLOAD_VERSION,
      "ingest:2026-04-01T12:00:00.000Z",
    );
    const otherTarget = computeLeadSyncIdempotencyKey(
      "hubspot_stub",
      "550e8400-e29b-41d4-a716-446655440000",
      LEAD_SYNC_PAYLOAD_VERSION,
      "ingest:2026-04-01T12:00:00.000Z",
    );
    const otherRev = computeLeadSyncIdempotencyKey(
      "n8n_webhook",
      "550e8400-e29b-41d4-a716-446655440000",
      LEAD_SYNC_PAYLOAD_VERSION,
      "ingest:2026-04-01T13:00:00.000Z",
    );
    expect(otherTarget).not.toBe(base);
    expect(otherRev).not.toBe(base);
  });
});

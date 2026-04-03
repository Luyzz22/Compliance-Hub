import type {
  GtmDashboardSnapshot,
  GtmHealthSnapshotPayload,
  GtmSourceVolumeRow,
} from "@/lib/gtmDashboardTypes";

import { evaluateGtmAlertsFromSnapshot } from "@/lib/gtmAlertEvaluator";

function attentionByKind(snapshot: GtmDashboardSnapshot): Record<string, number> {
  const m: Record<string, number> = {};
  for (const a of snapshot.attention) {
    m[a.kind] = (m[a.kind] ?? 0) + 1;
  }
  return m;
}

function breakdownToVolume(rows: GtmDashboardSnapshot["attribution_by_source_30d"]): GtmSourceVolumeRow[] {
  return rows.slice(0, 8).map((r) => ({
    key: r.key,
    label_de: r.label_de,
    inquiries: r.inquiries_30d,
    qualified: r.qualified_30d,
    pipedrive_deals_created: r.pipedrive_deals_created_30d,
  }));
}

export function buildGtmHealthSnapshotPayload(snapshot: GtmDashboardSnapshot): GtmHealthSnapshotPayload {
  const k7 = snapshot.kpis["7d"];
  const k30 = snapshot.kpis["30d"];
  const alerts = evaluateGtmAlertsFromSnapshot(snapshot);

  return {
    generated_at: snapshot.generated_at,
    health_tiles: snapshot.health.tiles.map((t) => ({
      id: t.id,
      label_de: t.label_de,
      status: t.status,
    })),
    health_signal_counts: snapshot.health_signal_counts,
    attention_by_kind: attentionByKind(snapshot),
    ops_hints: snapshot.health.ops_hints.map((h) => ({ id: h.id, count: h.count })),
    kpis: {
      inbound_7d: k7.inbound_inquiries,
      inbound_30d: k30.inbound_inquiries,
      qualified_7d: k7.qualified_leads,
      qualified_30d: k30.qualified_leads,
      deals_7d: k7.pipedrive_deals_created,
      deals_30d: k30.pipedrive_deals_created,
      dead_letter_sync_30d: k30.dead_letter_sync_jobs,
      failed_webhook_30d: k30.failed_webhook_forwards,
    },
    segment_readiness: snapshot.health.segment_readiness.map((s) => ({
      segment: s.segment,
      label_de: s.label_de,
      inquiries_30d: s.inquiries_30d,
      qualified_30d: s.qualified_30d,
      status: s.status,
    })),
    attribution_sources_7d: snapshot.source_volume_by_attribution_7d.slice(0, 8),
    attribution_sources_30d_top: breakdownToVolume(snapshot.attribution_by_source_30d),
    alerts_evaluated: alerts,
  };
}

/**
 * Wave 31 – regelbasierte GTM Health / Readiness (kein Scoring-Modell).
 */

import type {
  GtmAttributionBreakdownRow,
  GtmAttributionHealthRow,
  GtmHealthLayer,
  GtmHealthStatus,
  GtmHealthTile,
  GtmOpsHint,
  GtmSegmentBucket,
  GtmSegmentReadinessRow,
} from "@/lib/gtmDashboardTypes";

import {
  GTM_HEALTH_ATTRIB_NOISE_MAX_QUAL_RATIO,
  GTM_HEALTH_ATTRIB_NOISE_MIN_LEADS,
  GTM_HEALTH_CRM_BAD_RATIO_ISSUE,
  GTM_HEALTH_CRM_BAD_RATIO_MIN_DENOM,
  GTM_HEALTH_CRM_BAD_RATIO_WATCH,
  GTM_HEALTH_DEAL_TO_QUALIFIED_ISSUE,
  GTM_HEALTH_DEAL_TO_QUALIFIED_WATCH,
  GTM_HEALTH_PIPELINE_QUALIFIED_MIN,
  GTM_HEALTH_SEGMENT_QUAL_RATIO_LOW,
  GTM_HEALTH_SEGMENT_VOLUME_MIN,
  GTM_HEALTH_SEGMENT_VOLUME_VERY_LOW,
  GTM_HEALTH_SPAM_RATE_ISSUE,
  GTM_HEALTH_SPAM_RATE_MIN_INBOUND,
  GTM_HEALTH_SPAM_RATE_WATCH,
  GTM_HEALTH_UNTRIAGED_COUNT_ISSUE,
  GTM_HEALTH_UNTRIAGED_COUNT_WATCH,
  GTM_HEALTH_WEBHOOK_RATE_ISSUE,
  GTM_HEALTH_WEBHOOK_RATE_WATCH,
} from "@/lib/gtmHealthThresholds";

export type GtmHealthEngineInput = {
  inbound_30d: number;
  webhook_failed_30d: number;
  spam_30d: number;
  untriaged_over_3d: number;
  crm_dead_letter_30d: number;
  crm_failed_30d: number;
  crm_sent_ok_30d: number;
  qualified_30d: number;
  deals_created_30d: number;
  stuck_failed_crm_sync_24h: number;
  qualified_no_pipedrive_deal_old_7d: number;
  segments: {
    segment: GtmSegmentBucket;
    label_de: string;
    inquiries_30d: number;
    qualified_30d: number;
    hubspot_sent_30d: number;
    pipedrive_touch_30d: number;
    dominant_sources_de: string;
  }[];
  attribution_top_sources: GtmAttributionBreakdownRow[];
};

export function evaluateGtmHealth(input: GtmHealthEngineInput): GtmHealthLayer {
  const whRate = input.inbound_30d > 0 ? input.webhook_failed_30d / input.inbound_30d : 0;
  const spamRate =
    input.inbound_30d >= GTM_HEALTH_SPAM_RATE_MIN_INBOUND
      ? input.spam_30d / input.inbound_30d
      : 0;

  let intakeStatus: GtmHealthStatus = "good";
  if (input.inbound_30d > 0) {
    const spamBad =
      input.inbound_30d >= GTM_HEALTH_SPAM_RATE_MIN_INBOUND &&
      spamRate >= GTM_HEALTH_SPAM_RATE_ISSUE;
    const spamWarn =
      input.inbound_30d >= GTM_HEALTH_SPAM_RATE_MIN_INBOUND &&
      spamRate >= GTM_HEALTH_SPAM_RATE_WATCH;
    if (whRate >= GTM_HEALTH_WEBHOOK_RATE_ISSUE || spamBad) intakeStatus = "issue";
    else if (whRate >= GTM_HEALTH_WEBHOOK_RATE_WATCH || spamWarn) intakeStatus = "watch";
  }

  let triageStatus: GtmHealthStatus = "good";
  if (input.untriaged_over_3d >= GTM_HEALTH_UNTRIAGED_COUNT_ISSUE) triageStatus = "issue";
  else if (input.untriaged_over_3d >= GTM_HEALTH_UNTRIAGED_COUNT_WATCH) triageStatus = "watch";

  const crmDenom =
    input.crm_dead_letter_30d + input.crm_failed_30d + input.crm_sent_ok_30d;
  const crmBad = input.crm_dead_letter_30d + input.crm_failed_30d;
  const crmBadRatio = crmDenom >= GTM_HEALTH_CRM_BAD_RATIO_MIN_DENOM ? crmBad / crmDenom : 0;
  let syncHealthStatus: GtmHealthStatus = "good";
  if (crmDenom >= GTM_HEALTH_CRM_BAD_RATIO_MIN_DENOM) {
    if (crmBadRatio >= GTM_HEALTH_CRM_BAD_RATIO_ISSUE) syncHealthStatus = "issue";
    else if (crmBadRatio >= GTM_HEALTH_CRM_BAD_RATIO_WATCH) syncHealthStatus = "watch";
  }

  let pipelineStatus: GtmHealthStatus = "good";
  let pipelineExplanation =
    "Qualifizierte Leads und Pipedrive-Deals (30 Tage) stehen in einem plausiblen Verhältnis — oder es gibt noch zu wenig Daten.";
  if (input.qualified_30d >= GTM_HEALTH_PIPELINE_QUALIFIED_MIN) {
    const ratio = input.deals_created_30d / input.qualified_30d;
    if (ratio < GTM_HEALTH_DEAL_TO_QUALIFIED_ISSUE) {
      pipelineStatus = "issue";
      pipelineExplanation =
        "Relativ viele qualifizierte Leads, aber wenige neue Pipedrive-Deals im gleichen Fenster — Pipeline-Übergang prüfen.";
    } else if (ratio < GTM_HEALTH_DEAL_TO_QUALIFIED_WATCH) {
      pipelineStatus = "watch";
      pipelineExplanation =
        "Einige qualifizierte Leads ohne entsprechende Deal-Anlage im 30-Tage-Fenster — kein Vorwurf, nur Orientierung.";
    }
  }

  const tiles: GtmHealthTile[] = [
    {
      id: "intake",
      label_de: "Lead-Eingang",
      status: intakeStatus,
      explanation_de:
        intakeStatus === "good"
          ? "Webhook-Fehlerquote und Spam-Anteil (30 Tage) wirken unkritisch. Formular-Uptime wird hier nicht gemessen."
          : intakeStatus === "watch"
            ? "Erhöhte Webhook-Fehler oder Spam-Anteil möglich — Inbox und n8n/Webhook prüfen."
            : "Auffällige Webhook-Fehler oder Spam — technische Route und Dubletten/Noise klären.",
      href: "/admin/leads?forwarding_status=failed",
      link_label_de: "Fehlgeschlagene Weiterleitungen",
    },
    {
      id: "triage",
      label_de: "Triage",
      status: triageStatus,
      explanation_de:
        triageStatus === "good"
          ? "Keine unbearbeiteten „Neu“-Leads älter als 3 Tage."
          : triageStatus === "watch"
            ? "Einige „Neu“-Leads warten länger — kurz durchgehen."
            : "Mehrere „Neu“-Leads hängen — Rückstand droht Chancen zu kosten.",
      href: "/admin/leads?triage_status=received",
      link_label_de: "Neu / unbearbeitet",
    },
    {
      id: "sync",
      label_de: "CRM-Sync",
      status: syncHealthStatus,
      explanation_de:
        syncHealthStatus === "good"
          ? "Anteil fehlgeschlagener/Dead-Letter-CRM-Jobs (30 Tage) ist gering oder es gibt kaum Volumen."
          : syncHealthStatus === "watch"
            ? "CRM-Sync stolpert merklich — Jobs und Secrets prüfen."
            : "Viele fehlgeschlagene oder terminale Sync-Jobs — Downstream stabilisieren.",
      href: "/admin/gtm#gtm-attention",
      link_label_de: "Aufmerksamkeit",
    },
    {
      id: "pipeline",
      label_de: "Pipeline",
      status: pipelineStatus,
      explanation_de: pipelineExplanation,
      href: "/admin/gtm#gtm-segment-readiness",
      link_label_de: "Segment-Readiness",
    },
  ];

  const ops_hints: GtmOpsHint[] = [];
  if (input.untriaged_over_3d > 0) {
    ops_hints.push({
      id: "untriaged_3d",
      count: input.untriaged_over_3d,
      message_de: `${input.untriaged_over_3d} Lead(s) mit Status „Neu“ seit über 3 Tagen — Triage vorschlagen.`,
      href: "/admin/leads?triage_status=received",
    });
  }
  if (input.stuck_failed_crm_sync_24h > 0) {
    ops_hints.push({
      id: "stuck_sync",
      count: input.stuck_failed_crm_sync_24h,
      message_de: `${input.stuck_failed_crm_sync_24h} CRM-Sync-Job(s) fehlgeschlagen, letzter Versuch vor über 24 Stunden — Retry oder Dead Letter prüfen.`,
      href: "/admin/gtm#gtm-attention",
    });
  }
  if (input.qualified_no_pipedrive_deal_old_7d > 0) {
    ops_hints.push({
      id: "qualified_no_deal",
      count: input.qualified_no_pipedrive_deal_old_7d,
      message_de: `${input.qualified_no_pipedrive_deal_old_7d} qualifizierter Lead ohne Pipedrive-Deal, Einreichung älter als 7 Tage (Proxy — Qualifizierungsdatum nicht separat gespeichert).`,
      href: "/admin/leads",
    });
  }

  const segment_readiness: GtmSegmentReadinessRow[] = input.segments.map((s) => {
    const qualRatio = s.inquiries_30d > 0 ? s.qualified_30d / s.inquiries_30d : 0;
    let status: GtmHealthStatus = "good";
    let note_de =
      "Volumen und Qualifikation wirken ausgewogen für die Phase — oder es gibt noch wenig Daten.";

    if (s.segment !== "other" && s.inquiries_30d <= GTM_HEALTH_SEGMENT_VOLUME_VERY_LOW) {
      status = "watch";
      note_de = "Sehr wenige Eingänge — strategischer GTM-Fokus oder Reichweite prüfen.";
    } else if (
      s.inquiries_30d >= GTM_HEALTH_SEGMENT_VOLUME_MIN &&
      qualRatio < GTM_HEALTH_SEGMENT_QUAL_RATIO_LOW
    ) {
      status = "watch";
      note_de = "Viele Eingänge, aber wenig Qualifikation — Angebot, ICP oder Erwartungsmanagement prüfen.";
    }

    return {
      segment: s.segment,
      label_de: s.label_de,
      inquiries_30d: s.inquiries_30d,
      qualified_30d: s.qualified_30d,
      hubspot_sent_30d: s.hubspot_sent_30d,
      pipedrive_touch_30d: s.pipedrive_touch_30d,
      dominant_sources_de: s.dominant_sources_de,
      status,
      note_de,
    };
  });

  const attribution_health_top3: GtmAttributionHealthRow[] = input.attribution_top_sources
    .slice(0, 3)
    .map((row) => {
      const qual_ratio =
        row.inquiries_30d > 0 ? row.qualified_30d / row.inquiries_30d : 0;
      const noise_suspected =
        row.inquiries_30d >= GTM_HEALTH_ATTRIB_NOISE_MIN_LEADS &&
        qual_ratio <= GTM_HEALTH_ATTRIB_NOISE_MAX_QUAL_RATIO;
      return { ...row, qual_ratio, noise_suspected };
    });

  const noiseChannels = attribution_health_top3.filter((r) => r.noise_suspected);
  if (noiseChannels.length > 0) {
    ops_hints.push({
      id: "attrib_noise",
      count: noiseChannels.length,
      message_de: `${noiseChannels.length} starke(r) Kanal(e) mit vielen Leads aber wenig Qualifikation — Zielgruppe oder Bots prüfen (heuristisch).`,
      href: "/admin/gtm#gtm-attribution-health",
    });
  }

  return { tiles, ops_hints, segment_readiness, attribution_health_top3 };
}

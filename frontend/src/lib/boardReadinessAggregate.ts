import "server-only";

import {
  classifyMappedTenantReadiness,
  GTM_READINESS_LABELS_DE,
  type GtmGovernanceSignalsInput,
  type GtmReadinessClass,
} from "@/lib/gtmAccountReadiness";
import type {
  BoardAttentionItem,
  BoardReadinessBanner,
  BoardReadinessClassRollupRow,
  BoardReadinessPayload,
  BoardReadinessPillarBlock,
  BoardReadinessPillarKey,
  BoardReadinessSegmentRollupRow,
  BoardReadinessTraffic,
  BoardReadinessGtmDemandStrip,
} from "@/lib/boardReadinessTypes";
import type { GtmProductBridgePayload } from "@/lib/gtmProductBridgeTypes";
import { BOARD_REPORT_FRESH_DAYS, trafficFromRatio, worstTraffic } from "@/lib/boardReadinessThresholds";
import { isoInWindow, windowBoundsMs } from "@/lib/gtmDashboardTime";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";
import { attachContactRollups, mergeLeadsWithOps } from "@/lib/leadInboxMerge";
import type { LeadInboxItem } from "@/lib/leadInboxTypes";
import { readLeadOpsState } from "@/lib/leadOpsState";
import { readAllLeadRecordsMerged } from "@/lib/leadPersistence";
import {
  findGtmProductMapEntry,
  readGtmProductAccountMap,
  type GtmProductMapEntry,
} from "@/lib/gtmProductAccountMapStore";
import { fetchTenantGovernanceSnapshot } from "@/lib/gtmProductGovernanceFetch";
import { fetchTenantBoardReadinessRaw } from "@/lib/fetchTenantBoardReadinessRaw";
import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";
import {
  boardComplianceReportFresh,
  complianceGapStatus,
  EU_AI_ACT_ART9,
  evidenceBundleComplete,
} from "@/lib/tenantBoardReadinessGaps";

const ART9 = EU_AI_ACT_ART9;

const SEGMENT_LABELS_DE: Record<GtmSegmentBucket, string> = {
  industrie_mittelstand: "Industrie / Mittelstand",
  kanzlei_wp: "Kanzlei / WP",
  enterprise_sap: "Enterprise / SAP",
  other: "Sonstiges",
};

function segmentBucket(seg: string): GtmSegmentBucket {
  if (seg === "industrie_mittelstand") return "industrie_mittelstand";
  if (seg === "kanzlei_wp") return "kanzlei_wp";
  if (seg === "enterprise_sap") return "enterprise_sap";
  return "other";
}

function signalsToInput(
  snap: Awaited<ReturnType<typeof fetchTenantGovernanceSnapshot>>,
  pilot_flag: boolean,
): GtmGovernanceSignalsInput {
  return {
    ai_systems_count: snap.ai_systems_count,
    progress_steps: snap.progress_steps,
    active_frameworks: snap.active_frameworks,
    fetch_ok: snap.fetch_ok,
    pilot_flag,
  };
}

function complianceStatus(
  rows: { requirement_id: string; status: string }[] | undefined,
  reqId: string,
): string | undefined {
  return complianceGapStatus(rows, reqId);
}

function evidenceBundleOk(raw: TenantBoardReadinessRaw, sysId: string): boolean {
  return evidenceBundleComplete(raw, sysId);
}

function boardReportFresh(raw: TenantBoardReadinessRaw, nowMs: number): boolean {
  return boardComplianceReportFresh(raw, nowMs);
}

function isoFrameworksScopes(setup: TenantBoardReadinessRaw["ai_governance_setup"]): {
  fw: string[];
  scopes: string[];
} {
  const fw = (setup?.active_frameworks ?? []).map((x) => x.toLowerCase());
  const scopes = (setup?.compliance_scopes ?? []).map((x) => x.toLowerCase());
  return { fw, scopes };
}

function iso42001ScopeOk(setup: TenantBoardReadinessRaw["ai_governance_setup"]): boolean {
  const { fw, scopes } = isoFrameworksScopes(setup);
  return fw.some((x) => x.includes("42001") || x.includes("iso_42001")) || scopes.some((x) => x.includes("42001"));
}

function nis2RoleOk(setup: TenantBoardReadinessRaw["ai_governance_setup"]): boolean {
  const roles = setup?.governance_roles ?? {};
  return Object.entries(roles).some(([k, v]) => {
    if (!String(v || "").trim()) return false;
    return /ciso|dpo|nis2|incident|security|kritis/i.test(k);
  });
}

/** Pro-Mandant-Pillar-Snapshot für Board Readiness und Kanzlei-Portfolio (Wave 39). */
export type TenantPillarSnapshot = {
  tenant_id: string;
  tenant_label: string | null;
  pilot: boolean;
  primary_segment: GtmSegmentBucket | null;
  readiness_class: GtmReadinessClass;
  raw: TenantBoardReadinessRaw;
  eu: {
    hr_total: number;
    art9_ratio: number | null;
    evidence_ratio: number | null;
    board_fresh: boolean;
    score: number | null;
    status: BoardReadinessTraffic;
    indicators: BoardReadinessPillarBlock["indicators"];
  };
  iso: { score: number | null; status: BoardReadinessTraffic; indicators: BoardReadinessPillarBlock["indicators"] };
  nis2: { score: number | null; status: BoardReadinessTraffic; indicators: BoardReadinessPillarBlock["indicators"] };
  dsgvo: { score: number | null; status: BoardReadinessTraffic; indicators: BoardReadinessPillarBlock["indicators"] };
};

function buildTenantSnapshot(
  tenantId: string,
  mapEntry: GtmProductMapEntry | undefined,
  primary_segment: GtmSegmentBucket | null,
  raw: TenantBoardReadinessRaw,
  govSnap: Awaited<ReturnType<typeof fetchTenantGovernanceSnapshot>>,
  nowMs: number,
): TenantPillarSnapshot {
  const readiness_class = classifyMappedTenantReadiness(
    signalsToInput(govSnap, mapEntry?.pilot === true),
  );

  const hasComplianceDashboard = raw.compliance_dashboard != null;
  const hrIds = hasComplianceDashboard
    ? (raw.compliance_dashboard?.systems ?? [])
        .filter((s) => s.risk_level === "high_risk")
        .map((s) => s.ai_system_id)
    : [];
  const hr_total = hrIds.length;

  let art9_ok = 0;
  let ev_ok = 0;
  for (const id of hrIds) {
    if (complianceStatus(raw.compliance_by_system[id], ART9) === "completed") art9_ok += 1;
    if (evidenceBundleOk(raw, id)) ev_ok += 1;
  }

  const art9_ratio = hr_total ? art9_ok / hr_total : null;
  const evidence_ratio = hr_total ? ev_ok / hr_total : null;
  const board_fresh = hr_total > 0 ? boardReportFresh(raw, nowMs) : true;

  const eu_sub_board: BoardReadinessTraffic = !hasComplianceDashboard
    ? "amber"
    : hr_total === 0
      ? "green"
      : board_fresh
        ? "green"
        : "red";

  const eu_core = worstTraffic(trafficFromRatio(art9_ratio), trafficFromRatio(evidence_ratio));
  const eu_status: BoardReadinessTraffic = !hasComplianceDashboard ? "amber" : worstTraffic(eu_core, eu_sub_board);

  const eu_score =
    !hasComplianceDashboard
      ? null
      : hr_total > 0
        ? Math.round(
            (((art9_ratio ?? 0) + (evidence_ratio ?? 0) + (board_fresh ? 1 : 0)) / 3) * 1000,
          ) / 10
        : null;

  const eu_indicators: BoardReadinessPillarBlock["indicators"] = [
    {
      key: "high_risk_art9_complete_ratio",
      label_de: "High-Risk: Risikomanagement (Art. 9) abgeschlossen",
      value_percent:
        !hasComplianceDashboard ? null : art9_ratio !== null ? Math.round(art9_ratio * 1000) / 10 : null,
      value_count: hr_total ? art9_ok : null,
      value_denominator: hasComplianceDashboard ? hr_total || null : null,
      status: !hasComplianceDashboard ? "amber" : trafficFromRatio(art9_ratio),
      source_api_paths: ["/api/v1/compliance/dashboard", "/api/v1/ai-systems/{id}/compliance"],
    },
    {
      key: "high_risk_evidence_bundle_ratio",
      label_de: "High-Risk: Nachweis-/Doku-Bündel (Art. 11 oder AI-Act-Docs)",
      value_percent:
        !hasComplianceDashboard ? null : evidence_ratio !== null ? Math.round(evidence_ratio * 1000) / 10 : null,
      value_count: hr_total ? ev_ok : null,
      value_denominator: hasComplianceDashboard ? hr_total || null : null,
      status: !hasComplianceDashboard ? "amber" : trafficFromRatio(evidence_ratio),
      source_api_paths: [
        "/api/v1/ai-systems/{id}/compliance",
        "/api/v1/ai-systems/{id}/ai-act-docs",
      ],
    },
    {
      key: "board_report_recency",
      label_de: `Board-Report (${BOARD_REPORT_FRESH_DAYS} Tage)`,
      value_percent:
        !hasComplianceDashboard ? null : hr_total === 0 ? null : board_fresh ? 100 : 0,
      value_count: !hasComplianceDashboard ? null : hr_total > 0 ? (board_fresh ? 1 : 0) : null,
      value_denominator: hasComplianceDashboard && hr_total > 0 ? 1 : null,
      status: eu_sub_board,
      source_api_paths: [`/api/v1/tenants/{tid}/board/ai-compliance-reports`],
    },
  ];

  const scope_ok = iso42001ScopeOk(raw.ai_governance_setup);
  const roles_ok =
    Object.values(raw.ai_governance_setup?.governance_roles ?? {}).filter((v) => String(v || "").trim()).length >= 2;
  const policies_ok = raw.setup_status?.policies_published === true;
  const iso_parts = [scope_ok, roles_ok, policies_ok];
  const iso_score = raw.fetch_ok ? (iso_parts.filter(Boolean).length / 3) * 100 : null;
  const iso_status = trafficFromRatio(iso_score !== null ? iso_score / 100 : null);

  const iso_indicators: BoardReadinessPillarBlock["indicators"] = [
    {
      key: "iso42001_scope_framework",
      label_de: "AI-MS Scope (ISO 42001 Framework/Scope)",
      value_percent: scope_ok ? 100 : 0,
      value_count: scope_ok ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: scope_ok ? "green" : "red",
      source_api_paths: ["/api/v1/tenants/{tid}/ai-governance-setup"],
    },
    {
      key: "iso42001_roles",
      label_de: "Rollen im Setup hinterlegt (≥2 befüllt)",
      value_percent: roles_ok ? 100 : 0,
      value_count: roles_ok ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: roles_ok ? "green" : "amber",
      source_api_paths: ["/api/v1/tenants/{tid}/ai-governance-setup"],
    },
    {
      key: "iso42001_policies",
      label_de: "Policy-Set veröffentlicht (Guided Setup)",
      value_percent: policies_ok ? 100 : 0,
      value_count: policies_ok ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: policies_ok ? "green" : "red",
      source_api_paths: ["/api/v1/tenants/{tid}/setup-status"],
    },
  ];

  const nis2_obl = raw.setup_status?.nis2_kpis_seeded === true;
  const mean = raw.ai_compliance_overview?.nis2_kritis_kpi_mean_percent;
  const obligations_ok = nis2_obl || (mean != null && mean > 0);
  let hr_inc = 0;
  let hr_inc_ok = 0;
  for (const id of hrIds) {
    const row = raw.ai_systems.find((s) => s.id === id);
    if (!row) continue;
    hr_inc += 1;
    if (row.has_incident_runbook) hr_inc_ok += 1;
  }
  const incident_ratio = hr_inc ? hr_inc_ok / hr_inc : null;
  const nis2_parts = [
    obligations_ok,
    nis2RoleOk(raw.ai_governance_setup),
    (incident_ratio ?? 1) >= 0.75 || hr_inc === 0,
  ];
  const nis2_score = raw.fetch_ok ? (nis2_parts.filter(Boolean).length / 3) * 100 : null;
  const nis2_status = trafficFromRatio(nis2_score !== null ? nis2_score / 100 : null);

  const nis2_indicators: BoardReadinessPillarBlock["indicators"] = [
    {
      key: "nis2_obligations_kpi_seed",
      label_de: "NIS2-Pflichten / KPI-Grundlage (gesät oder KPI-Mittelwert)",
      value_percent: obligations_ok ? 100 : 0,
      value_count: obligations_ok ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: obligations_ok ? "green" : "amber",
      source_api_paths: [
        "/api/v1/tenants/{tid}/setup-status",
        "/api/v1/ai-governance/compliance/overview",
      ],
    },
    {
      key: "nis2_contact_roles",
      label_de: "Kontakt-Rollen (CISO/DPO/Incident o.ä.)",
      value_percent: nis2RoleOk(raw.ai_governance_setup) ? 100 : 0,
      value_count: nis2RoleOk(raw.ai_governance_setup) ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: nis2RoleOk(raw.ai_governance_setup) ? "green" : "amber",
      source_api_paths: ["/api/v1/tenants/{tid}/ai-governance-setup"],
    },
    {
      key: "nis2_incident_runbook_high_risk",
      label_de: "Incident-Runbook bei High-Risk-Systemen (Anteil)",
      value_percent: incident_ratio !== null ? Math.round(incident_ratio * 1000) / 10 : null,
      value_count: hr_inc ? hr_inc_ok : null,
      value_denominator: hr_inc || null,
      status: trafficFromRatio(incident_ratio),
      source_api_paths: ["/api/v1/ai-systems"],
    },
  ];

  let dpia_ok = 0;
  for (const id of hrIds) {
    const row = raw.ai_systems.find((s) => s.id === id);
    if (row?.gdpr_dpia_required) dpia_ok += 1;
  }
  const dpia_ratio = hr_total ? dpia_ok / hr_total : null;
  const records_ok =
    raw.setup_status?.evidence_attached === true || raw.setup_status?.classification_completed === true;
  const dsgvo_parts = [
    hr_total === 0 ? true : (dpia_ratio ?? 0) >= 0.85,
    records_ok,
  ];
  const dsgvo_score = raw.fetch_ok ? (dsgvo_parts.filter(Boolean).length / 2) * 100 : null;
  const dsgvo_status = trafficFromRatio(dsgvo_score !== null ? dsgvo_score / 100 : null);

  const dsgvo_indicators: BoardReadinessPillarBlock["indicators"] = [
    {
      key: "dsgvo_dpia_flag_high_risk",
      label_de: "DSFA-Pflicht / Nachweis-Flag bei High-Risk (Anteil mit gdpr_dpia_required)",
      value_percent: dpia_ratio !== null ? Math.round(dpia_ratio * 1000) / 10 : null,
      value_count: hr_total ? dpia_ok : null,
      value_denominator: hr_total || null,
      status: trafficFromRatio(dpia_ratio),
      source_api_paths: ["/api/v1/ai-systems"],
    },
    {
      key: "dsgvo_records_evidence",
      label_de: "Grundaufzeichnungen (Evidenz/Klassifikation laut Setup-Status)",
      value_percent: records_ok ? 100 : 0,
      value_count: records_ok ? 1 : 0,
      value_denominator: raw.fetch_ok ? 1 : null,
      status: records_ok ? "green" : "amber",
      source_api_paths: ["/api/v1/tenants/{tid}/setup-status"],
    },
  ];

  return {
    tenant_id: tenantId,
    tenant_label: mapEntry?.label ?? null,
    pilot: mapEntry?.pilot === true,
    primary_segment,
    readiness_class,
    raw,
    eu: {
      hr_total,
      art9_ratio,
      evidence_ratio,
      board_fresh,
      score: eu_score,
      status: eu_status,
      indicators: eu_indicators,
    },
    iso: { score: iso_score, status: iso_status, indicators: iso_indicators },
    nis2: { score: nis2_score, status: nis2_status, indicators: nis2_indicators },
    dsgvo: { score: dsgvo_score, status: dsgvo_status, indicators: dsgvo_indicators },
  };
}

function aggregatePillarsFromTenants(
  tenants: TenantPillarSnapshot[],
): Record<BoardReadinessPillarKey, BoardReadinessPillarBlock> {
  const keys: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];
  const titles: Record<BoardReadinessPillarKey, string> = {
    eu_ai_act: "EU AI Act",
    iso_42001: "ISO 42001",
    nis2: "NIS2 / KRITIS",
    dsgvo: "DSGVO / Aufzeichnungen",
  };

  const pickIndicators = (
    pillar: "eu" | "iso" | "nis2" | "dsgvo",
  ): BoardReadinessPillarBlock["indicators"] => {
    const first = tenants[0];
    const template = first ? first[pillar].indicators : [];
    return template.map((ind) => {
      const vals: number[] = [];
      let st: BoardReadinessTraffic = "green";
      for (const t of tenants) {
        const match = t[pillar].indicators.find((x) => x.key === ind.key);
        if (!match) continue;
        if (match.value_percent !== null && match.value_percent !== undefined) {
          vals.push(match.value_percent);
        }
        st = worstTraffic(st, match.status);
      }
      const avg = vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null;
      const stFromAvg = trafficFromRatio(avg !== null ? avg / 100 : null);
      return {
        ...ind,
        value_percent: avg,
        value_count: null,
        value_denominator: tenants.length ? tenants.length : null,
        status: worstTraffic(st, stFromAvg),
      };
    });
  };

  const blocks: Record<BoardReadinessPillarKey, BoardReadinessPillarBlock> = {} as Record<
    BoardReadinessPillarKey,
    BoardReadinessPillarBlock
  >;

  if (!tenants.length) {
    for (const k of keys) {
      blocks[k] = {
        pillar: k,
        title_de: titles[k],
        summary_de: "Keine gemappten Mandanten im GTM-Product-Map.",
        status: "amber",
        indicators: [],
      };
    }
    return blocks;
  }

  const euInd = pickIndicators("eu");
  const isoInd = pickIndicators("iso");
  const nisInd = pickIndicators("nis2");
  const dsgInd = pickIndicators("dsgvo");

  const pillarStatus = (inds: BoardReadinessPillarBlock["indicators"]): BoardReadinessTraffic =>
    inds.reduce((a, x) => worstTraffic(a, x.status), "green" as BoardReadinessTraffic);

  blocks.eu_ai_act = {
    pillar: "eu_ai_act",
    title_de: titles.eu_ai_act,
    summary_de:
      "High-Risk-Stichprobe: Art. 9, Nachweisbündel (Art. 11 / AI-Act-Docs), Board-Report-Recency.",
    status: pillarStatus(euInd),
    indicators: euInd,
  };
  blocks.iso_42001 = {
    pillar: "iso_42001",
    title_de: titles.iso_42001,
    summary_de: "AI-Managementsystem: Scope/Framework, Rollen, Policies (reale Setup-Artefakte).",
    status: pillarStatus(isoInd),
    indicators: isoInd,
  };
  blocks.nis2 = {
    pillar: "nis2",
    title_de: titles.nis2,
    summary_de: "Grundpflichten/KPIs, Kontakte, Incident-Runbooks an High-Risk-Systemen.",
    status: pillarStatus(nisInd),
    indicators: nisInd,
  };
  blocks.dsgvo = {
    pillar: "dsgvo",
    title_de: titles.dsgvo,
    summary_de: "DSFA-Flag / Pfad für High-Risk und Basis-Evidenz aus Guided Setup.",
    status: pillarStatus(dsgInd),
    indicators: dsgInd,
  };

  return blocks;
}

function attentionItemsForTenant(t: TenantPillarSnapshot): BoardAttentionItem[] {
  const items: BoardAttentionItem[] = [];
  const seg = t.primary_segment ? SEGMENT_LABELS_DE[t.primary_segment] : null;

  const hrIds =
    t.raw.compliance_dashboard?.systems.filter((s) => s.risk_level === "high_risk").map((s) => s.ai_system_id) ??
    [];

  for (const id of hrIds) {
    const sys = t.raw.ai_systems.find((s) => s.id === id);
    const name = sys?.name ?? id;
    const updated = sys?.updated_at_utc ?? null;

    if (!String(sys?.owner_email || "").trim()) {
      items.push({
        id: `owner:${t.tenant_id}:${id}`,
        severity: "red",
        tenant_id: t.tenant_id,
        tenant_label: t.tenant_label,
        segment_tag: seg,
        readiness_class: t.readiness_class,
        subject_type: "ai_system",
        subject_id: id,
        subject_name: name,
        missing_artefact_de: "Verantwortlicher (owner_email) fehlt",
        last_change_at: updated ?? null,
        deep_links: {
          workspace_path: `/tenant/ai-systems/${id}`,
          api_path: `/api/v1/ai-systems/${id}`,
        },
      });
    }

    if (complianceStatus(t.raw.compliance_by_system[id], ART9) !== "completed") {
      items.push({
        id: `art9:${t.tenant_id}:${id}`,
        severity: "amber",
        tenant_id: t.tenant_id,
        tenant_label: t.tenant_label,
        segment_tag: seg,
        readiness_class: t.readiness_class,
        subject_type: "ai_system",
        subject_id: id,
        subject_name: name,
        missing_artefact_de: "Risikomanagement (Art. 9) nicht abgeschlossen",
        last_change_at: updated ?? null,
        deep_links: {
          workspace_path: `/tenant/eu-ai-act`,
          api_path: `/api/v1/ai-systems/${id}/compliance`,
        },
      });
    }

    if (!evidenceBundleOk(t.raw, id)) {
      items.push({
        id: `evidence:${t.tenant_id}:${id}`,
        severity: "amber",
        tenant_id: t.tenant_id,
        tenant_label: t.tenant_label,
        segment_tag: seg,
        readiness_class: t.readiness_class,
        subject_type: "ai_system",
        subject_id: id,
        subject_name: name,
        missing_artefact_de: "Konformitätsnachweis/Doku-Bündel unvollständig (Art. 11 oder AI-Act-Docs)",
        last_change_at: updated ?? null,
        deep_links: {
          workspace_path: `/tenant/ai-systems/${id}`,
          api_path: `/api/v1/ai-systems/${id}/ai-act-docs`,
        },
      });
    }
  }

  if (hrIds.length && !t.eu.board_fresh) {
    const br = t.raw.board_reports[0];
    items.push({
      id: `board:${t.tenant_id}`,
      severity: "red",
      tenant_id: t.tenant_id,
      tenant_label: t.tenant_label,
      segment_tag: seg,
      readiness_class: t.readiness_class,
      subject_type: "tenant",
      subject_id: t.tenant_id,
      subject_name: t.tenant_label ?? t.tenant_id,
      missing_artefact_de: `Aktueller Board-Report fehlt (letzte ${BOARD_REPORT_FRESH_DAYS} Tage)`,
      last_change_at: br?.created_at ?? null,
      deep_links: {
        workspace_path: "/board/ai-compliance-report",
        api_path: `/api/v1/tenants/${t.tenant_id}/board/ai-compliance-reports`,
      },
    });
  }

  return items;
}

function rollupBySegment(
  tenants: TenantPillarSnapshot[],
  overlay: GtmProductBridgePayload["segment_overlay"],
): BoardReadinessSegmentRollupRow[] {
  const buckets: GtmSegmentBucket[] = [
    "industrie_mittelstand",
    "kanzlei_wp",
    "enterprise_sap",
    "other",
  ];

  const bySeg = new Map<GtmSegmentBucket, TenantPillarSnapshot[]>();
  for (const b of buckets) bySeg.set(b, []);
  for (const t of tenants) {
    const s = t.primary_segment ?? "other";
    bySeg.get(s)?.push(t);
  }

  return buckets.map((segment) => {
    const group = bySeg.get(segment) ?? [];
    const ov = overlay.find((r) => r.segment === segment);

    const pillar_score_proxy: Record<BoardReadinessPillarKey, number | null> = {
      eu_ai_act: null,
      iso_42001: null,
      nis2: null,
      dsgvo: null,
    };
    const pillar_status: Record<BoardReadinessPillarKey, BoardReadinessTraffic> = {
      eu_ai_act: "green",
      iso_42001: "green",
      nis2: "green",
      dsgvo: "green",
    };

    for (const pk of Object.keys(pillar_score_proxy) as BoardReadinessPillarKey[]) {
      const key = pk === "eu_ai_act" ? "eu" : pk === "iso_42001" ? "iso" : pk === "nis2" ? "nis2" : "dsgvo";
      const scores: number[] = [];
      let st: BoardReadinessTraffic = "green";
      for (const tn of group) {
        const sc = tn[key].score;
        if (sc !== null && sc !== undefined) scores.push(sc);
        st = worstTraffic(st, tn[key].status);
      }
      pillar_score_proxy[pk] = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
      pillar_status[pk] = st;
    }

    return {
      segment,
      label_de: SEGMENT_LABELS_DE[segment],
      inquiries_30d: ov?.inquiries_30d ?? 0,
      qualified_30d: ov?.qualified_30d ?? 0,
      pillar_status,
      pillar_score_proxy,
      mapped_tenant_count: group.length,
    };
  });
}

function rollupByReadinessClass(tenants: TenantPillarSnapshot[]): BoardReadinessClassRollupRow[] {
  const classes: GtmReadinessClass[] = [
    "no_footprint",
    "early_pilot",
    "baseline_governance",
    "advanced_governance",
  ];

  return classes.map((readiness_class) => {
    const group = tenants.filter((t) => t.readiness_class === readiness_class);
    const pillar_score_proxy: Record<BoardReadinessPillarKey, number | null> = {
      eu_ai_act: null,
      iso_42001: null,
      nis2: null,
      dsgvo: null,
    };
    const pillar_status: Record<BoardReadinessPillarKey, BoardReadinessTraffic> = {
      eu_ai_act: "green",
      iso_42001: "green",
      nis2: "green",
      dsgvo: "green",
    };
    for (const pk of Object.keys(pillar_score_proxy) as BoardReadinessPillarKey[]) {
      const key = pk === "eu_ai_act" ? "eu" : pk === "iso_42001" ? "iso" : pk === "nis2" ? "nis2" : "dsgvo";
      const scores: number[] = [];
      let st: BoardReadinessTraffic = "green";
      for (const tn of group) {
        const sc = tn[key].score;
        if (sc !== null && sc !== undefined) scores.push(sc);
        st = worstTraffic(st, tn[key].status);
      }
      pillar_score_proxy[pk] = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
      pillar_status[pk] = st;
    }
    return {
      readiness_class,
      label_de: GTM_READINESS_LABELS_DE[readiness_class],
      tenant_count: group.length,
      pillar_status,
      pillar_score_proxy,
    };
  });
}

async function loadLeads30d(nowMs: number): Promise<LeadInboxItem[]> {
  const allRows = await readAllLeadRecordsMerged();
  const ops = await readLeadOpsState();
  const merged = mergeLeadsWithOps(allRows, ops);
  const items = attachContactRollups(merged, allRows, ops);
  const w = windowBoundsMs(30, nowMs);
  return items.filter((it) => isoInWindow(it.created_at, w.start, w.end));
}

function primarySegmentForTenant(
  tenantId: string,
  map: Awaited<ReturnType<typeof readGtmProductAccountMap>>,
  items: LeadInboxItem[],
): GtmSegmentBucket | null {
  const counts: Record<GtmSegmentBucket, number> = {
    industrie_mittelstand: 0,
    kanzlei_wp: 0,
    enterprise_sap: 0,
    other: 0,
  };
  for (const it of items) {
    const e = findGtmProductMapEntry(map, it);
    if (!e || e.tenant_id !== tenantId) continue;
    counts[segmentBucket(it.segment)] += 1;
  }
  let best: GtmSegmentBucket | null = null;
  let max = 0;
  (Object.keys(counts) as GtmSegmentBucket[]).forEach((k) => {
    if (counts[k] > max) {
      max = counts[k];
      best = k;
    }
  });
  return max > 0 ? best : null;
}

function mapEntryForTenant(
  tid: string,
  map: Awaited<ReturnType<typeof readGtmProductAccountMap>>,
): GtmProductMapEntry | undefined {
  return map.entries.find((e) => e.tenant_id === tid);
}

export type MappedTenantPillarSnapshotBundle = {
  generated_at: string;
  nowMs: number;
  map: Awaited<ReturnType<typeof readGtmProductAccountMap>>;
  tenantIds: string[];
  leads30d: LeadInboxItem[];
  snapshots: TenantPillarSnapshot[];
  backend_reachable: boolean;
  tenants_partial: number;
};

/**
 * Lädt alle gemappten Mandanten mit Pillar-Snapshots (eine API-Runde pro Mandant).
 * Wird von Board Readiness und Kanzlei-Portfolio (Wave 39) gemeinsam genutzt.
 */
export async function loadMappedTenantPillarSnapshots(now: Date = new Date()): Promise<MappedTenantPillarSnapshotBundle> {
  const nowMs = now.getTime();
  const map = await readGtmProductAccountMap();
  const tenantIds = [...new Set(map.entries.map((e) => e.tenant_id))];
  const leads30d = await loadLeads30d(nowMs);

  const snapshots: TenantPillarSnapshot[] = [];
  let backendReachable = false;
  let partial = 0;

  for (const tid of tenantIds) {
    const [raw, govSnap] = await Promise.all([
      fetchTenantBoardReadinessRaw(tid),
      fetchTenantGovernanceSnapshot(tid),
    ]);
    if (raw.fetch_ok) backendReachable = true;
    else partial += 1;
    const entry = mapEntryForTenant(tid, map);
    const primary_segment = primarySegmentForTenant(tid, map, leads30d);
    snapshots.push(buildTenantSnapshot(tid, entry, primary_segment, raw, govSnap, nowMs));
  }

  return {
    generated_at: now.toISOString(),
    nowMs,
    map,
    tenantIds,
    leads30d,
    snapshots,
    backend_reachable: backendReachable,
    tenants_partial: partial,
  };
}

export async function computeBoardReadinessPayload(now: Date = new Date()): Promise<BoardReadinessPayload> {
  const bundle = await loadMappedTenantPillarSnapshots(now);
  const { snapshots, backend_reachable: backendReachable, tenants_partial: partial, nowMs } = bundle;

  const { computeProductBridgePayload } = await import("@/lib/gtmProductBridgeAggregate");
  const product_bridge = await computeProductBridgePayload(now);

  const pillarMap = aggregatePillarsFromTenants(snapshots);
  const pillars = [
    pillarMap.eu_ai_act,
    pillarMap.iso_42001,
    pillarMap.nis2,
    pillarMap.dsgvo,
  ];

  const overallStatus = pillars.reduce((a, p) => worstTraffic(a, p.status), "green" as BoardReadinessTraffic);
  const overallLabel =
    overallStatus === "green"
      ? "Portfolio insgesamt im Zielkorridor"
      : overallStatus === "amber"
        ? "Gezielte Nachsteuerung empfohlen"
        : "Kritische Governance-Lücken – Board-Vorbereitung anstoßen";

  const gtmAttention: BoardAttentionItem[] = [];
  for (const row of product_bridge.segment_overlay) {
    if (row.qualified_30d >= 3 && row.dominant_readiness === "early_pilot") {
      gtmAttention.push({
        id: `gtm-demand:${row.segment}`,
        severity: "amber",
        tenant_id: "_portfolio",
        tenant_label: null,
        segment_tag: row.label_de,
        readiness_class: row.dominant_readiness,
        subject_type: "tenant",
        subject_id: null,
        subject_name: row.label_de,
        missing_artefact_de:
          "Hohe qualifizierte Nachfrage im Segment bei dominanter Pilot-Readiness – Produkt-Governance nachziehen.",
        last_change_at: new Date(nowMs).toISOString(),
        deep_links: {
          workspace_path: "/admin/gtm",
          api_path: "/api/admin/gtm/summary",
        },
      });
    }
  }

  const attention_items = [...gtmAttention, ...snapshots.flatMap(attentionItemsForTenant)].slice(0, 80);

  const gtm_demand_strip: BoardReadinessGtmDemandStrip = {
    window_days: 30,
    segment_rows: product_bridge.segment_overlay.map((r) => ({
      segment: r.segment,
      label_de: r.label_de,
      inquiries_30d: r.inquiries_30d,
      qualified_30d: r.qualified_30d,
      dominant_readiness: r.dominant_readiness,
    })),
  };

  return {
    generated_at: now.toISOString(),
    backend_reachable: backendReachable,
    mapped_tenant_count: bundle.tenantIds.length,
    tenants_partial: partial,
    overall: { status: overallStatus, label_de: overallLabel },
    pillars,
    segment_rollups: rollupBySegment(snapshots, product_bridge.segment_overlay),
    readiness_class_rollups: rollupByReadinessClass(snapshots),
    attention_items,
    gtm_demand_strip,
    notes_de: [
      "Indikatoren bewusst grob; Ampeln leiten aus echten API-Artefakten ab (kein Composite-Score).",
      "Scope: Mandanten aus gtm-product-account-map.json; Segment aus dominanten Leads (30 Tage).",
    ],
  };
}

export function boardReadinessBannerFromPayload(p: BoardReadinessPayload): BoardReadinessBanner {
  return {
    status: p.overall.status,
    label_de: p.overall.label_de,
    mapped_tenant_count: p.mapped_tenant_count,
    backend_reachable: p.backend_reachable,
  };
}

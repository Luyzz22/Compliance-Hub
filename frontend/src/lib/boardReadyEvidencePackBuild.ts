/**
 * Wave 51 – Board-Ready Evidence Pack aus bestehenden Advisor-DTOs (deterministisch, erklärbar).
 */

import type { AdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceTypes";
import type { AdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookTypes";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type { AdvisorSlaFindingDto, AdvisorSlaSeverity } from "@/lib/advisorSlaTypes";
import {
  CROSS_REGULATION_PILLAR_LABEL_DE,
  CROSS_REGULATION_PILLAR_ORDER,
  type CrossRegulationMatrixDto,
} from "@/lib/advisorCrossRegulationTypes";
import {
  BOARD_READY_EVIDENCE_PACK_VERSION,
  type BoardReadyEvidencePackDto,
  type BoardReadyEvidencePackMeta,
} from "@/lib/boardReadyEvidencePackTypes";
import { GTM_READINESS_CLASSES, GTM_READINESS_LABELS_DE, type GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";
import {
  buildKanzleiPortfolioFocusAreasDe,
  summarizeKanzleiMonthlyReportSection1,
} from "@/lib/kanzleiMonthlyReportBuild";

const DISCLAIMER_DE =
  "Internes Arbeitspapier für Geschäftsführung, Bereichsleitung oder board-nahe Gespräche. " +
  "Keine Rechtsberatung, keine Garantie der Vollständigkeit; Faktenlage pro Mandant kann abweichen. " +
  "Signale stammen aus ComplianceHub-Steuerungsdaten (Ampeln, KPIs, Heuristiken) – keine substanzielle Prüfung einzelner Systeme.";

function severityOrder(s: AdvisorSlaSeverity): number {
  if (s === "critical") return 0;
  if (s === "warning") return 1;
  return 2;
}

function sortedFindings(findings: AdvisorSlaFindingDto[]): AdvisorSlaFindingDto[] {
  return [...findings].sort((a, b) => {
    const d = severityOrder(a.severity) - severityOrder(b.severity);
    if (d !== 0) return d;
    return a.title_de.localeCompare(b.title_de, "de");
  });
}

function dominantReadinessClass(dist: Record<GtmReadinessClass, number>): GtmReadinessClass | null {
  let best: GtmReadinessClass | null = null;
  let max = 0;
  for (const c of GTM_READINESS_CLASSES) {
    const n = dist[c];
    if (n > max) {
      max = n;
      best = c;
    }
  }
  return max > 0 ? best : null;
}

function buildSectionA(
  payload: KanzleiPortfolioPayload,
  kpiSnapshot: AdvisorKpiPortfolioSnapshot | null,
): BoardReadyEvidencePackDto["section_a_executive_snapshot"] {
  const s1 = summarizeKanzleiMonthlyReportSection1(payload);
  const dom = dominantReadinessClass(s1.readiness_distribution);
  const domLabel = dom ? GTM_READINESS_LABELS_DE[dom] : "heterogen";
  const backend = s1.backend_reachable ? "vollständig erreichbar" : "teilweise eingeschränkt";
  let overall_posture_de = `Portfolio: **${s1.total_mandanten}** gemappte Mandanten; dominante Readiness-Einordnung: **${domLabel}**. ` +
    `Backend/API: ${backend}. Attention-Queue: **${s1.count_queue}** Mandant(en) mit erhöhter Steuerungspriorität. ` +
    `Offene Prüfpunkte gesamt: **${s1.total_open_points}** (davon hoch: **${s1.total_open_points_hoch}**).`;
  if (kpiSnapshot?.strip?.length) {
    const bits = kpiSnapshot.strip
      .slice(0, 2)
      .map((t) => `${t.label_de} ${t.value_display_de}`)
      .join("; ");
    overall_posture_de += ` Kanzlei-KPI-Stichprobe (${kpiSnapshot.window_days} Tage): ${bits}.`;
  }

  const top_risks_de: string[] = [];
  const sf = sortedFindings(payload.advisor_sla.findings);
  for (const f of sf.slice(0, 5)) {
    top_risks_de.push(`${f.title_de}: ${f.detail_de}`);
  }
  if (top_risks_de.length === 0) {
    for (const sig of payload.advisor_sla.signals) {
      if (sig.active) top_risks_de.push(`${sig.label_de}: ${sig.detail_de}`);
    }
  }
  if (top_risks_de.length === 0) {
    top_risks_de.push(
      "Keine aktiven SLA-Befunde im aktuellen Lauf – Kadenz und Queue dennoch im Blick behalten.",
    );
  }

  const major_open_items_de: string[] = [];
  if (s1.count_review_stale > 0) {
    major_open_items_de.push(`${s1.count_review_stale} Mandant(en): Kanzlei-Review überfällig oder offen.`);
  }
  if (s1.count_export_stale > 0 || s1.count_never_export > 0) {
    major_open_items_de.push(
      `Exportlage: ${s1.count_export_stale} mit überschrittener Kadenz, ${s1.count_never_export} ohne erfassten Export.`,
    );
  }
  if (s1.count_board_report_stale > 0) {
    major_open_items_de.push(`${s1.count_board_report_stale} Mandant(en): Board-/Statusbericht überfällig.`);
  }
  for (const q of payload.attention_queue.slice(0, 3)) {
    const name = q.mandant_label ?? q.tenant_id;
    major_open_items_de.push(`${name}: ${q.naechster_schritt_de}`);
  }
  if (major_open_items_de.length === 0) {
    major_open_items_de.push("Keine aggregierten Kadenz- oder Queue-Hervorhebungen über die Basisschwellen hinaus.");
  }

  return {
    overall_posture_de,
    top_risks_de: top_risks_de.slice(0, 6),
    major_open_items_de: major_open_items_de.slice(0, 6),
  };
}

function buildSectionB(cr: CrossRegulationMatrixDto): BoardReadyEvidencePackDto["section_b_cross_regulation"] {
  const highlights = CROSS_REGULATION_PILLAR_ORDER.map((pk) => {
    const c = cr.totals.per_pillar[pk];
    const lab = CROSS_REGULATION_PILLAR_LABEL_DE[pk];
    const summary_de = `Priorität: **${c.priority}**, Nacharbeit: **${c.needs_attention}**, OK: **${c.ok}**, Datenlage unklar: **${c.unknown}**.`;
    return { pillar_label_de: lab, summary_de };
  });
  const multi =
    cr.totals.mandanten_multi_pillar_stress > 0
      ? `${cr.totals.mandanten_multi_pillar_stress} Mandant(en) mit Druck auf mindestens zwei Säulen gleichzeitig – geeignet für Querschnittsgespräche („map once, comply many“).`
      : null;
  return { highlights, multi_stress_note_de: multi };
}

function buildSectionC(ag: AdvisorAiGovernancePortfolioDto): BoardReadyEvidencePackDto["section_c_ai_governance"] {
  const s = ag.summary;
  const ai_act_relevance_note_de = `Heuristisch **${s.count_likely_ai_act_relevance}** Mandant(en) mit Hinweis auf mögliche AI-Act-/Register-Relevanz; **${s.count_potential_high_risk_exposure}** mit High-Risk-Indikator im Dashboard (keine Rechtsklassifikation).`;

  const governance_gaps_de: string[] = [];
  if (s.count_weak_iso42001 > 0) {
    governance_gaps_de.push(
      `ISO 42001: Bei **${s.count_weak_iso42001}** Mandant(en) Ampel schwach oder mittel – AIMs-Artefakte und Rollen klären.`,
    );
  }
  if (s.count_weak_post_market > 0) {
    governance_gaps_de.push(
      `Überwachung/Reporting (Post-Market-Kontext): **${s.count_weak_post_market}** Mandant(en) mit Lückenhinweis bei High-Risk-Kontext.`,
    );
  }
  if (s.count_weak_human_oversight > 0) {
    governance_gaps_de.push(
      `Human Oversight: **${s.count_weak_human_oversight}** Mandant(en) mit Prüfbedarf (Owner/Verantwortung).`,
    );
  }
  if (governance_gaps_de.length === 0) {
    governance_gaps_de.push("Keine aggregierten KI-Governance-Lücken über die Standard-Schwellen hinaus gemeldet.");
  }

  const oversight_monitoring_de =
    "Monitoring und Nachweise bleiben mandantenindividuell zu belegen; dieses Pack spiegelt nur Dashboard- und Ampelstände wider.";

  return {
    ai_act_relevance_note_de,
    governance_gaps_de: governance_gaps_de.slice(0, 5),
    oversight_monitoring_de,
  };
}

function buildSectionD(eh: AdvisorEvidenceHooksPortfolioDto): BoardReadyEvidencePackDto["section_d_evidence_touchpoints"] {
  const s = eh.summary;
  const executive_summary_de = `Evidenz-Reife (Metadaten): **${s.total_hook_rows}** Hook-Zeilen im Überblick. ` +
    `**${s.mandanten_without_sap_touchpoint}** Mandant(en) ohne SAP/BTP-Touchpoint (verbunden oder geplant); **${s.mandanten_without_datev_export}** ohne DATEV-Export in der Historie.`;

  const datev_erp_note_de =
    "DATEV stützt den Kanzlei-Kanal (Belege/Steuerkontext); SAP/ERP-Hooks markieren typische Enterprise-Lücken – keine Live-Integration, keine technische Tiefe in diesem Dokument.";

  const status_overview_de = `Status der Hooks: verbunden **${s.by_status.connected}**, geplant **${s.by_status.planned}**, nicht verbunden **${s.by_status.not_connected}**, Fehler **${s.by_status.error}**. Upsell-Kandidaten (Governance + Drucksignale): **${s.mandanten_enterprise_upsell_candidates}**.`;

  return {
    executive_summary_de,
    datev_erp_note_de,
    status_overview_de,
  };
}

function buildSectionE(payload: KanzleiPortfolioPayload): BoardReadyEvidencePackDto["section_e_next_actions"] {
  const s1 = summarizeKanzleiMonthlyReportSection1(payload);
  const fromSla = payload.advisor_sla.next_steps_de;
  const fromFocus = buildKanzleiPortfolioFocusAreasDe(payload, s1);
  const pool = [...fromSla, ...fromFocus];
  const seen = new Set<string>();
  const actions_de: string[] = [];
  for (const line of pool) {
    const k = line.trim();
    if (!k || seen.has(k)) continue;
    seen.add(k);
    actions_de.push(k);
    if (actions_de.length >= 5) break;
  }
  if (actions_de.length < 3) {
    actions_de.push("Termin mit Geschäftsführung/Bereichsleitung: Top-3-Mandanten aus Attention-Queue gemeinsam priorisieren.");
  }
  return { actions_de: actions_de.slice(0, 5) };
}

function buildMeta(
  payload: KanzleiPortfolioPayload,
  kpiSnapshot: AdvisorKpiPortfolioSnapshot | null,
  generatedAt: Date,
): BoardReadyEvidencePackMeta {
  const included_signals_de = [
    "Kanzlei-Portfolio & Board-Readiness-Zeilen",
    "Cross-Regulation-Matrix (EU AI Act, ISO 42001, NIS2, DSGVO)",
    "AI-Governance-Überblick (Heuristik)",
    "SLA- und Eskalationssignale",
    "Enterprise Evidence Hooks (Metadaten)",
  ];
  if (kpiSnapshot) {
    included_signals_de.push(`Kanzlei-KPI-Snapshot (${kpiSnapshot.window_days} Tage)`);
  }
  return {
    version: BOARD_READY_EVIDENCE_PACK_VERSION,
    generated_at: generatedAt.toISOString(),
    portfolio_version: payload.version,
    portfolio_generated_at: payload.generated_at,
    included_signals_de,
    disclaimer_de: DISCLAIMER_DE,
  };
}

function buildMarkdown(dto: BoardReadyEvidencePackDto): string {
  const m = dto.meta;
  const a = dto.section_a_executive_snapshot;
  const b = dto.section_b_cross_regulation;
  const c = dto.section_c_ai_governance;
  const d = dto.section_d_evidence_touchpoints;
  const e = dto.section_e_next_actions;
  const lines: string[] = [];

  lines.push("# Board-Ready Evidence Pack");
  lines.push("");
  lines.push(`_Erzeugt: ${new Date(m.generated_at).toLocaleString("de-DE")} · Portfolio ${m.portfolio_version} · Schema ${m.version}_`);
  lines.push("");
  lines.push(`_${m.disclaimer_de}_`);
  lines.push("");
  lines.push("## A) Executive Readiness Snapshot");
  lines.push("");
  lines.push("### Gesamtlage");
  lines.push(a.overall_posture_de);
  lines.push("");
  lines.push("### Top-Risiken (operativ)");
  for (const x of a.top_risks_de) lines.push(`- ${x}`);
  lines.push("");
  lines.push("### Wesentliche offene Punkte");
  for (const x of a.major_open_items_de) lines.push(`- ${x}`);
  lines.push("");
  lines.push("## B) Cross-Regulation (Kurz)");
  lines.push("");
  for (const h of b.highlights) {
    lines.push(`- **${h.pillar_label_de}:** ${h.summary_de}`);
  }
  if (b.multi_stress_note_de) {
    lines.push("");
    lines.push(b.multi_stress_note_de);
  }
  lines.push("");
  lines.push("## C) AI-Governance (Kurz)");
  lines.push("");
  lines.push(c.ai_act_relevance_note_de);
  lines.push("");
  lines.push("### Governance-Lücken (aggregiert)");
  for (const x of c.governance_gaps_de) lines.push(`- ${x}`);
  lines.push("");
  lines.push("### Oversight / Monitoring");
  lines.push(c.oversight_monitoring_de);
  lines.push("");
  lines.push("## D) Evidence Touchpoints");
  lines.push("");
  lines.push(d.executive_summary_de);
  lines.push("");
  lines.push(d.datev_erp_note_de);
  lines.push("");
  lines.push(d.status_overview_de);
  lines.push("");
  lines.push("## E) Empfohlene Management-Schritte");
  lines.push("");
  e.actions_de.forEach((x, i) => lines.push(`${i + 1}. ${x}`));
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("### Eingeschlossene Signalquellen");
  for (const s of m.included_signals_de) lines.push(`- ${s}`);
  lines.push("");

  return lines.join("\n");
}

export type BuildBoardReadyEvidencePackInput = {
  payload: KanzleiPortfolioPayload;
  crossRegulation: CrossRegulationMatrixDto;
  aiGovernance: AdvisorAiGovernancePortfolioDto;
  evidenceHooks: AdvisorEvidenceHooksPortfolioDto;
  kpiSnapshot: AdvisorKpiPortfolioSnapshot | null;
  generatedAt?: Date;
};

export function buildBoardReadyEvidencePack(input: BuildBoardReadyEvidencePackInput): BoardReadyEvidencePackDto {
  const generatedAt = input.generatedAt ?? new Date();
  const meta = buildMeta(input.payload, input.kpiSnapshot, generatedAt);
  const dto: BoardReadyEvidencePackDto = {
    meta,
    section_a_executive_snapshot: buildSectionA(input.payload, input.kpiSnapshot),
    section_b_cross_regulation: buildSectionB(input.crossRegulation),
    section_c_ai_governance: buildSectionC(input.aiGovernance),
    section_d_evidence_touchpoints: buildSectionD(input.evidenceHooks),
    section_e_next_actions: buildSectionE(input.payload),
    markdown_de: "",
  };
  dto.markdown_de = buildMarkdown(dto);
  return dto;
}

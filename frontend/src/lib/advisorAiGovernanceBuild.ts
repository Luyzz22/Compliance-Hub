/**
 * Wave 48 – AI-Governance-Aggregation aus Snapshot-Signalen (pure, ohne server-only).
 */

import type { BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import {
  ADVISOR_AI_GOVERNANCE_VERSION,
  type AdvisorAiGovernanceCompletenessBucket,
  type AdvisorAiGovernanceMandantRow,
  type AdvisorAiGovernancePartialTri,
  type AdvisorAiGovernancePortfolioDto,
  type AdvisorAiGovernancePortfolioSummary,
  type AdvisorAiGovernanceSnapshotInput,
  type AdvisorAiGovernanceTopAttention,
  type AdvisorAiGovernanceTriState,
} from "@/lib/advisorAiGovernanceTypes";

export const ADVISOR_AI_GOVERNANCE_DISCLAIMER_DE =
  "Hinweis: Aggregat aus Board-Readiness- und Compliance-Rohdaten. Keine Rechtsberatung und keine automatische Risiko- oder Register-Qualifikation – Bewertungen verbleiben bei Mandant und Berater.";

export function trafficToCompletenessBucket(
  status: BoardReadinessTraffic,
  apiOk: boolean,
): AdvisorAiGovernanceCompletenessBucket {
  if (!apiOk) return "unknown";
  if (status === "red") return "weak";
  if (status === "amber") return "medium";
  return "strong";
}

function triDeclared(input: AdvisorAiGovernanceSnapshotInput): AdvisorAiGovernanceTriState {
  if (!input.api_fetch_ok) return "unknown";
  return input.declared_ai_system_count > 0 ? "yes" : "no";
}

function triHighRisk(input: AdvisorAiGovernanceSnapshotInput): AdvisorAiGovernanceTriState {
  if (!input.api_fetch_ok) return "unknown";
  return input.high_risk_system_count > 0 ? "yes" : "no";
}

function triRegistration(input: AdvisorAiGovernanceSnapshotInput): AdvisorAiGovernanceTriState {
  if (!input.api_fetch_ok) return "unknown";
  if (!input.has_compliance_dashboard) return "unknown";
  if (input.high_risk_system_count > 0) return "yes";
  if (input.declared_ai_system_count > 0) return "unknown";
  return "no";
}

function postMarket(input: AdvisorAiGovernanceSnapshotInput): AdvisorAiGovernancePartialTri {
  if (!input.api_fetch_ok) return "partial";
  if (input.high_risk_system_count === 0) return "partial";
  if (!input.board_report_fresh_when_hr) return "no";
  if (input.eu_ai_act_status === "green") return "yes";
  return "partial";
}

function humanOversight(input: AdvisorAiGovernanceSnapshotInput): AdvisorAiGovernancePartialTri {
  if (!input.api_fetch_ok) return "partial";
  if (input.high_risk_system_count === 0) return "partial";
  if (input.high_risk_without_owner_count === 0) return "yes";
  if (input.high_risk_without_owner_count >= input.high_risk_system_count) return "no";
  return "partial";
}

function buildNotes(row: AdvisorAiGovernanceMandantRow, input: AdvisorAiGovernanceSnapshotInput): string[] {
  const notes: string[] = [];
  if (!input.api_fetch_ok) {
    notes.push("API-Daten unvollständig – AI-Governance-Posture nicht belastbar.");
    return notes.slice(0, 3);
  }
  if (input.declared_ai_system_count === 0) {
    notes.push("Keine KI-Systeme in der Übersicht erfasst – Erklärung im Mandantengespräch klären.");
  }
  if (input.high_risk_system_count > 0) {
    notes.push(
      "Hinweis auf mögliche AI-Act-Relevanz: High-Risk-Systeme im Dashboard – Register- und Dokumentationspfade mit Mandant abstimmen.",
    );
  }
  if (row.ai_act_artifact_completeness === "weak" || row.ai_act_artifact_completeness === "medium") {
    notes.push("Fehlende oder unvollständige Governance-Artefakte (EU AI Act-Säule) – Nachweise und Lücken im Workspace prüfen.");
  }
  if (row.iso42001_governance_completeness === "weak") {
    notes.push("Fehlende ISO-42001-Governance-Artefakte (Scope, Rollen, Policies) – AIMs-Vorbereitung einplanen.");
  }
  if (row.post_market_monitoring_readiness === "no") {
    notes.push("Prüfbedarf Post-Market/Reporting: Board- oder Statusbericht im HR-Kontext nicht im Zielkorridor.");
  }
  if (row.human_oversight_readiness === "no" || row.human_oversight_readiness === "partial") {
    notes.push("Prüfbedarf Human Oversight: Verantwortliche bei High-Risk-Systemen nicht vollständig hinterlegt.");
  }
  return notes.slice(0, 4);
}

export function buildAdvisorAiGovernanceMandantRow(
  input: AdvisorAiGovernanceSnapshotInput,
): AdvisorAiGovernanceMandantRow {
  const tidEnc = encodeURIComponent(input.tenant_id);
  const ai_act_artifact_completeness = trafficToCompletenessBucket(
    input.eu_ai_act_status,
    input.api_fetch_ok,
  );
  const iso42001_governance_completeness = trafficToCompletenessBucket(
    input.iso_42001_status,
    input.api_fetch_ok,
  );

  const row: AdvisorAiGovernanceMandantRow = {
    tenant_id: input.tenant_id,
    mandant_label: input.mandant_label,
    ai_systems_declared: triDeclared(input),
    high_risk_indicator: triHighRisk(input),
    ai_act_artifact_completeness,
    iso42001_governance_completeness,
    post_market_monitoring_readiness: postMarket(input),
    human_oversight_readiness: humanOversight(input),
    registration_relevance: triRegistration(input),
    notes_de: [],
    links: {
      mandant_export_page: `/admin/advisor-mandant-export?client_id=${tidEnc}`,
      board_readiness_admin: "/admin/board-readiness",
    },
  };
  row.notes_de = buildNotes(row, input);
  return row;
}

function emptyBuckets(): Record<AdvisorAiGovernanceCompletenessBucket, number> {
  return { weak: 0, medium: 0, strong: 0, unknown: 0 };
}

function priorityScore(row: AdvisorAiGovernanceMandantRow): number {
  let s = 0;
  if (row.post_market_monitoring_readiness === "no") s += 5;
  if (row.human_oversight_readiness === "no") s += 4;
  if (row.ai_act_artifact_completeness === "weak") s += 4;
  else if (row.ai_act_artifact_completeness === "medium") s += 2;
  if (row.iso42001_governance_completeness === "weak") s += 3;
  else if (row.iso42001_governance_completeness === "medium") s += 1;
  if (row.high_risk_indicator === "yes") s += 2;
  if (row.registration_relevance === "yes" && row.ai_act_artifact_completeness !== "strong") s += 1;
  return s;
}

function topHint(row: AdvisorAiGovernanceMandantRow): string {
  if (row.post_market_monitoring_readiness === "no") return "Post-Market/Reporting im HR-Kontext nachziehen.";
  if (row.human_oversight_readiness === "no") return "Human Oversight: Verantwortliche bei High-Risk-Systemen ergänzen.";
  if (row.ai_act_artifact_completeness === "weak") return "EU AI Act: Artefakte und Nachweise priorisieren.";
  if (row.iso42001_governance_completeness === "weak") return "ISO 42001: Governance-Grundlagen (Scope/Rollen/Policies) schließen.";
  if (row.high_risk_indicator === "yes") return "High-Risk-Systeme: Register- und Dokumentationspfad mit Mandant klären.";
  return "AI-Governance-Steuerung im Einzelfall vertiefen.";
}

export function summarizeAdvisorAiGovernancePortfolio(
  mandanten: AdvisorAiGovernanceMandantRow[],
  tenantsPartial: number,
): AdvisorAiGovernancePortfolioSummary {
  const bucket_ai_act = emptyBuckets();
  const bucket_iso42001 = emptyBuckets();
  let count_likely_ai_act_relevance = 0;
  let count_potential_high_risk_exposure = 0;
  let count_weak_iso42001 = 0;
  let count_weak_post_market = 0;
  let count_weak_human_oversight = 0;

  for (const m of mandanten) {
    bucket_ai_act[m.ai_act_artifact_completeness] += 1;
    bucket_iso42001[m.iso42001_governance_completeness] += 1;
    if (m.registration_relevance === "yes" || m.ai_act_artifact_completeness === "weak") {
      count_likely_ai_act_relevance += 1;
    }
    if (m.high_risk_indicator === "yes") count_potential_high_risk_exposure += 1;
    if (m.iso42001_governance_completeness === "weak" || m.iso42001_governance_completeness === "medium") {
      count_weak_iso42001 += 1;
    }
    if (m.post_market_monitoring_readiness === "no") count_weak_post_market += 1;
    if (m.human_oversight_readiness === "no") count_weak_human_oversight += 1;
  }

  return {
    total_mandanten: mandanten.length,
    tenants_partial_api: tenantsPartial,
    count_likely_ai_act_relevance,
    count_potential_high_risk_exposure,
    count_weak_iso42001,
    count_weak_post_market,
    count_weak_human_oversight,
    bucket_ai_act,
    bucket_iso42001,
  };
}

export function buildAdvisorAiGovernanceTopAttention(
  mandanten: AdvisorAiGovernanceMandantRow[],
  maxN: number,
): AdvisorAiGovernanceTopAttention[] {
  const ranked = [...mandanten].sort((a, b) => {
    const d = priorityScore(b) - priorityScore(a);
    if (d !== 0) return d;
    return (a.mandant_label ?? a.tenant_id).localeCompare(b.mandant_label ?? b.tenant_id, "de");
  });
  const n = Math.min(12, Math.max(3, maxN));
  return ranked.slice(0, n).map((m) => ({
    tenant_id: m.tenant_id,
    mandant_label: m.mandant_label,
    priority_hint_de: topHint(m),
    links: m.links,
  }));
}

export function advisorAiGovernanceMarkdownDe(dto: AdvisorAiGovernancePortfolioDto): string {
  const s = dto.summary;
  const lines: string[] = [];
  lines.push(`# AI-Governance Portfolio (Advisor)`);
  lines.push(
    `_Erzeugt: ${new Date(dto.generated_at).toLocaleString("de-DE")} · Portfolio-Stand: ${new Date(dto.portfolio_generated_at).toLocaleString("de-DE")} · Schema ${dto.version}_`,
  );
  lines.push("");
  lines.push(`_${dto.disclaimer_de}_`);
  lines.push("");
  lines.push(`## Überblick`);
  lines.push(`- Mandanten: **${s.total_mandanten}** (API teilweise: **${s.tenants_partial_api}**)`);
  lines.push(`- Hinweis AI-Act-/Register-Thematik (Heuristik): **${s.count_likely_ai_act_relevance}**`);
  lines.push(`- High-Risk-Systeme im Dashboard: **${s.count_potential_high_risk_exposure}** Mandanten`);
  lines.push(`- Schwache ISO-42001-Säule: **${s.count_weak_iso42001}**`);
  lines.push(`- Post-Market/Reporting-Lücke (HR-Kontext): **${s.count_weak_post_market}**`);
  lines.push(`- Prüfbedarf Human Oversight: **${s.count_weak_human_oversight}**`);
  lines.push("");
  lines.push(`## EU AI Act – Verteilung (Ampel → Bucket)`);
  lines.push(
    `- schwach: **${s.bucket_ai_act.weak}** · mittel: **${s.bucket_ai_act.medium}** · stark: **${s.bucket_ai_act.strong}** · unbekannt: **${s.bucket_ai_act.unknown}**`,
  );
  lines.push(`## ISO 42001 – Verteilung`);
  lines.push(
    `- schwach: **${s.bucket_iso42001.weak}** · mittel: **${s.bucket_iso42001.medium}** · stark: **${s.bucket_iso42001.strong}** · unbekannt: **${s.bucket_iso42001.unknown}**`,
  );
  lines.push("");
  lines.push(`## Top Mandanten (Advisor-Fokus)`);
  for (const t of dto.top_attention) {
    const name = t.mandant_label ?? t.tenant_id;
    lines.push(`- **${name}** (\`${t.tenant_id}\`): ${t.priority_hint_de}`);
  }
  return lines.join("\n");
}

/** Leerer Überblick für Tests oder Fallback, wenn keine Snapshots vorliegen. */
export function stubAdvisorAiGovernancePortfolioDto(portfolioGeneratedAt: string): AdvisorAiGovernancePortfolioDto {
  return buildAdvisorAiGovernancePortfolioDto([], 0, portfolioGeneratedAt);
}

export function buildAdvisorAiGovernancePortfolioDto(
  inputs: AdvisorAiGovernanceSnapshotInput[],
  tenantsPartial: number,
  portfolioGeneratedAt: string,
): AdvisorAiGovernancePortfolioDto {
  const mandanten = inputs.map(buildAdvisorAiGovernanceMandantRow);
  const summary = summarizeAdvisorAiGovernancePortfolio(mandanten, tenantsPartial);
  const top_attention = buildAdvisorAiGovernanceTopAttention(mandanten, 8);
  const generated_at = new Date().toISOString();
  const base: Omit<AdvisorAiGovernancePortfolioDto, "markdown_de"> = {
    version: ADVISOR_AI_GOVERNANCE_VERSION,
    generated_at,
    portfolio_generated_at: portfolioGeneratedAt,
    disclaimer_de: ADVISOR_AI_GOVERNANCE_DISCLAIMER_DE,
    summary,
    mandanten,
    top_attention,
  };
  const markdown_de = advisorAiGovernanceMarkdownDe({ ...base, markdown_de: "" });
  return { ...base, markdown_de };
}

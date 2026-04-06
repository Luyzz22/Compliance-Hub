/**
 * Wave 49 – Matrix aus Kanzlei-Portfolio-Zeilen (Board-Säulen + erklärbare Lücken-Heuristik).
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import {
  CROSS_REGULATION_PILLAR_LABEL_DE,
  CROSS_REGULATION_PILLAR_ORDER,
  ADVISOR_CROSS_REGULATION_VERSION,
  type CrossRegulationBucket,
  type CrossRegulationMandantRow,
  type CrossRegulationMatrixDto,
  type CrossRegulationPillarBucketCounts,
  type CrossRegulationPortfolioTotals,
  type CrossRegulationTopCase,
} from "@/lib/advisorCrossRegulationTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";

export const ADVISOR_CROSS_REGULATION_DISCLAIMER_DE =
  "Hinweis: Matrix aus Board-Readiness-Ampeln und offenen Prüfpunkten (Kanzlei-Semantik). Keine Rechtsbewertung und keine vollständige Normenabdeckung – Steuerungshilfe für Berater, besonders Mittelstand und WP-Kanzleien. NIS2- und DSGVO-Signale können auch ohne hohe EU-AI-Act-Relevanz relevant sein.";

const TOP_GAP_CODE_TO_PILLAR: Record<string, BoardReadinessPillarKey> = {
  EU_AI_Act: "eu_ai_act",
  ISO_42001: "iso_42001",
  NIS2: "nis2",
  DSGVO: "dsgvo",
};

const BUCKET_RANK: Record<CrossRegulationBucket, number> = {
  unknown: 0,
  ok: 1,
  needs_attention: 2,
  priority: 3,
};

function maxBucket(a: CrossRegulationBucket, b: CrossRegulationBucket): CrossRegulationBucket {
  return BUCKET_RANK[a] >= BUCKET_RANK[b] ? a : b;
}

export function trafficToCrossRegulationBucket(
  traffic: BoardReadinessTraffic,
  apiOk: boolean,
): CrossRegulationBucket {
  if (!apiOk) return "unknown";
  if (traffic === "red") return "priority";
  if (traffic === "amber") return "needs_attention";
  return "ok";
}

function gapPressureOnPillar(row: KanzleiPortfolioRow, pillar: BoardReadinessPillarKey, manyOpenThr: number): boolean {
  const mapped = TOP_GAP_CODE_TO_PILLAR[row.top_gap_pillar_code];
  if (mapped !== pillar) return false;
  if (row.open_points_count <= 0) return false;
  if (row.open_points_hoch > 0) return true;
  return row.open_points_count >= manyOpenThr;
}

function buildMandantRow(row: KanzleiPortfolioRow, manyOpenThr: number): CrossRegulationMandantRow {
  const pillars = {} as Record<BoardReadinessPillarKey, CrossRegulationBucket>;
  for (const pk of CROSS_REGULATION_PILLAR_ORDER) {
    let b = trafficToCrossRegulationBucket(row.pillar_traffic[pk], row.api_fetch_ok);
    if (row.api_fetch_ok && gapPressureOnPillar(row, pk, manyOpenThr)) {
      b = maxBucket(b, "needs_attention");
    }
    pillars[pk] = b;
  }

  let priority_pillar_count = 0;
  let active_pillar_pressure_count = 0;
  for (const pk of CROSS_REGULATION_PILLAR_ORDER) {
    const x = pillars[pk];
    if (x === "priority") {
      priority_pillar_count += 1;
      active_pillar_pressure_count += 1;
    } else if (x === "needs_attention") {
      active_pillar_pressure_count += 1;
    }
  }

  const notes_de: string[] = [];
  if (!row.api_fetch_ok) {
    notes_de.push("API teilweise nicht lesbar – Säulen nicht belastbar.");
  } else {
    if (priority_pillar_count >= 2) {
      notes_de.push("Mehrere Säulen mit hohem Nachholbedarf – gemeinsame Vorhaben (Evidence, Rollen, Lieferkette) können Synergien nutzen (Map once, comply many).");
    }
    if (pillars.nis2 === "priority" || pillars.nis2 === "needs_attention") {
      notes_de.push("NIS2 / KRITIS-Relevanz prüfen – auch bei geringer KI-Nutzung.");
    }
    if (pillars.dsgvo === "priority" || pillars.dsgvo === "needs_attention") {
      notes_de.push("DSGVO / BDSG- und Verarbeitungsstammdaten im Blick behalten.");
    }
    if (row.gaps_heavy_without_recent_export) {
      notes_de.push("Viele offene Punkte ohne frischen Export – Aktenstand für Querschnittsreview ziehen.");
    }
  }

  return {
    tenant_id: row.tenant_id,
    mandant_label: row.mandant_label,
    pillars,
    active_pillar_pressure_count,
    priority_pillar_count,
    notes_de: notes_de.slice(0, 4),
    links: { ...row.links },
  };
}

function emptyPillarCounts(): CrossRegulationPillarBucketCounts {
  return { ok: 0, needs_attention: 0, priority: 0, unknown: 0 };
}

function stressScore(m: CrossRegulationMandantRow): number {
  let s = 0;
  for (const pk of CROSS_REGULATION_PILLAR_ORDER) {
    const x = m.pillars[pk];
    if (x === "priority") s += 4;
    else if (x === "needs_attention") s += 2;
    else if (x === "unknown") s += 1;
  }
  return s;
}

function topHint(m: CrossRegulationMandantRow): string {
  if (m.priority_pillar_count >= 2) {
    return "Mehrere Säulen prioritär – gemeinsame Governance-Arbeit einplanen.";
  }
  if (m.pillars.eu_ai_act === "priority") return "EU AI Act: Dokumentation und Register-Pfade priorisieren.";
  if (m.pillars.iso_42001 === "priority") return "ISO 42001: AIMs-Grundlagen und Rollen schließen.";
  if (m.pillars.nis2 === "priority") return "NIS2 / KRITIS: Melde- und Lieferkettenpfade schärfen.";
  if (m.pillars.dsgvo === "priority") return "DSGVO / BDSG: Verarbeitung und Nachweise klären.";
  if (m.active_pillar_pressure_count >= 2) return "Mehrere Säulen beobachten – Querschnittsgespräch.";
  return "Säulenlage im Einzelfall vertiefen.";
}

export function summarizeCrossRegulationTotals(mandanten: CrossRegulationMandantRow[]): CrossRegulationPortfolioTotals {
  const per_pillar = {
    eu_ai_act: emptyPillarCounts(),
    iso_42001: emptyPillarCounts(),
    nis2: emptyPillarCounts(),
    dsgvo: emptyPillarCounts(),
  } as Record<BoardReadinessPillarKey, CrossRegulationPillarBucketCounts>;

  for (const m of mandanten) {
    for (const pk of CROSS_REGULATION_PILLAR_ORDER) {
      per_pillar[pk][m.pillars[pk]] += 1;
    }
  }

  let mandanten_multi_pillar_priority = 0;
  let mandanten_multi_pillar_stress = 0;
  for (const m of mandanten) {
    if (m.priority_pillar_count >= 2) mandanten_multi_pillar_priority += 1;
    if (m.active_pillar_pressure_count >= 2) mandanten_multi_pillar_stress += 1;
  }

  return { per_pillar, mandanten_multi_pillar_priority, mandanten_multi_pillar_stress };
}

export function buildCrossRegulationTopCases(
  mandanten: CrossRegulationMandantRow[],
  maxN: number,
): CrossRegulationTopCase[] {
  const n = Math.min(15, Math.max(3, maxN));
  const sorted = [...mandanten].sort((a, b) => {
    const ds = stressScore(b) - stressScore(a);
    if (ds !== 0) return ds;
    if (b.priority_pillar_count !== a.priority_pillar_count) {
      return b.priority_pillar_count - a.priority_pillar_count;
    }
    return (a.mandant_label ?? a.tenant_id).localeCompare(b.mandant_label ?? b.tenant_id, "de");
  });
  return sorted.slice(0, n).map((m) => ({
    tenant_id: m.tenant_id,
    mandant_label: m.mandant_label,
    hint_de: topHint(m),
    links: m.links,
  }));
}

export function crossRegulationMatrixMarkdownDe(dto: CrossRegulationMatrixDto): string {
  const lines: string[] = [];
  lines.push("# Cross-Regulation Matrix (Advisor)");
  lines.push(
    `_Erzeugt: ${new Date(dto.generated_at).toLocaleString("de-DE")} · Portfolio: ${new Date(dto.portfolio_generated_at).toLocaleString("de-DE")} · ${dto.version}_`,
  );
  lines.push("");
  lines.push(`_${dto.disclaimer_de}_`);
  lines.push("");
  lines.push("## Portfolio-Kennzahlen");
  lines.push(
    `- Mandanten mit **≥2** prioritären Säulen: **${dto.totals.mandanten_multi_pillar_priority}**`,
  );
  lines.push(
    `- Mandanten mit **≥2** Säulen unter Druck (priority oder Nacharbeit): **${dto.totals.mandanten_multi_pillar_stress}**`,
  );
  lines.push("");
  for (const pk of CROSS_REGULATION_PILLAR_ORDER) {
    const c = dto.totals.per_pillar[pk];
    const lab = CROSS_REGULATION_PILLAR_LABEL_DE[pk];
    lines.push(
      `- **${lab}:** OK ${c.ok} · Nacharbeit ${c.needs_attention} · Priorität ${c.priority} · unbekannt ${c.unknown}`,
    );
  }
  lines.push("");
  lines.push("## Top Fälle (Querschnitt)");
  for (const t of dto.top_cases) {
    const name = t.mandant_label ?? t.tenant_id;
    lines.push(`- **${name}** (\`${t.tenant_id}\`): ${t.hint_de}`);
  }
  return lines.join("\n");
}

export function buildCrossRegulationMatrixFromPayload(payload: KanzleiPortfolioPayload): CrossRegulationMatrixDto {
  const thr = payload.constants.many_open_points_threshold;
  const mandanten = payload.rows.map((r) => buildMandantRow(r, thr));
  const totals = summarizeCrossRegulationTotals(mandanten);
  const top_cases = buildCrossRegulationTopCases(mandanten, 8);
  const generated_at = new Date().toISOString();
  const base: Omit<CrossRegulationMatrixDto, "markdown_de"> = {
    version: ADVISOR_CROSS_REGULATION_VERSION,
    generated_at,
    portfolio_generated_at: payload.generated_at,
    disclaimer_de: ADVISOR_CROSS_REGULATION_DISCLAIMER_DE,
    totals,
    mandanten,
    top_cases,
  };
  const markdown_de = crossRegulationMatrixMarkdownDe({ ...base, markdown_de: "" });
  return { ...base, markdown_de };
}

export function stubCrossRegulationMatrixDto(portfolioGeneratedAt: string): CrossRegulationMatrixDto {
  const emptyMandanten: CrossRegulationMandantRow[] = [];
  const totals = summarizeCrossRegulationTotals(emptyMandanten);
  const generated_at = new Date().toISOString();
  const base: Omit<CrossRegulationMatrixDto, "markdown_de"> = {
    version: ADVISOR_CROSS_REGULATION_VERSION,
    generated_at,
    portfolio_generated_at: portfolioGeneratedAt,
    disclaimer_de: ADVISOR_CROSS_REGULATION_DISCLAIMER_DE,
    totals,
    mandanten: [],
    top_cases: [],
  };
  return { ...base, markdown_de: crossRegulationMatrixMarkdownDe({ ...base, markdown_de: "" }) };
}

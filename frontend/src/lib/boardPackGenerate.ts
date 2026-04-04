import type {
  BoardAttentionItem,
  BoardReadinessPayload,
  BoardReadinessPillarKey,
  BoardReadinessTraffic,
} from "@/lib/boardReadinessTypes";
import type { BoardReadinessBriefingBaselineFile } from "@/lib/boardReadinessBriefingTypes";
import {
  briefingRefIdForAttentionItem,
  computeDeltaBulletsDe,
} from "@/lib/boardReadinessBriefingGenerate";
import type {
  BoardPackActionRow,
  BoardPackAttentionRow,
  BoardPackExecutiveMemo,
  BoardPackHorizon,
  BoardPackMetadata,
  BoardPackPayload,
  BoardPackPillarKey,
} from "@/lib/boardPackTypes";
import { BOARD_PACK_HORIZON_LABEL_DE, BOARD_PACK_VERSION } from "@/lib/boardPackTypes";

const PILLAR_TITLES: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU AI Act",
  iso_42001: "ISO 42001",
  nis2: "NIS2 / KRITIS",
  dsgvo: "DSGVO / Aufzeichnungen",
};

function trafficWort(s: BoardReadinessTraffic): string {
  if (s === "green") return "Grün";
  if (s === "amber") return "Amber";
  return "Rot";
}

/** Transparente Priorisierung (niedriger Score = höhere Priorität). */
export function attentionPriorityScore(it: BoardAttentionItem): number {
  const sev = it.severity === "red" ? 0 : it.severity === "amber" ? 100 : 200;
  const m = it.missing_artefact_de.toLowerCase();
  let kind = 50;
  if (m.includes("verantwortlich") || m.includes("owner_email") || m.includes("owner")) kind = 0;
  else if (m.includes("board-report") || m.includes("board report")) kind = 10;
  else if (m.includes("art. 9") || m.includes("risikomanagement")) kind = 20;
  else if (m.includes("nachweis") || m.includes("doku") || m.includes("konformität")) kind = 30;
  else if (m.includes("nachfrage") || m.includes("governance nachziehen") || m.includes("pilot")) kind = 40;
  return sev + kind;
}

export const BOARD_PACK_PRIORITIZATION_RULES_DE: string[] = [
  "Zuerst Ampel Rot, dann Amber (Green kommt im Pack nicht vor).",
  "Innerhalb gleicher Ampel: fehlender Verantwortlicher (Owner) vor veraltetem Board-Report, vor Art. 9-Lücken, vor Nachweis/Doku, vor GTM-Nachfrage-vs.-Readiness-Hinweisen.",
  "Keine KI- oder Rechtsbewertung – nur regelbasierte Sortierung über Dashboard-Texte und Severity.",
];

export function sortAttentionForBoardPack(items: BoardAttentionItem[]): BoardAttentionItem[] {
  return [...items].sort((a, b) => {
    const d = attentionPriorityScore(a) - attentionPriorityScore(b);
    if (d !== 0) return d;
    return a.id.localeCompare(b.id);
  });
}

export function inferPillarFromAttention(it: BoardAttentionItem): BoardPackPillarKey {
  const m = it.missing_artefact_de.toLowerCase();
  if (m.includes("iso") || m.includes("42001") || m.includes("policy")) return "iso_42001";
  if (m.includes("nis2") || m.includes("incident") || m.includes("kpi")) return "nis2";
  if (m.includes("dsgvo") || m.includes("dsfa") || m.includes("dpia") || m.includes("aufzeichnung"))
    return "dsgvo";
  if (it.tenant_id === "_portfolio" || m.includes("nachfrage") || m.includes("segment")) return "portfolio";
  return "eu_ai_act";
}

function horizonForAttention(it: BoardAttentionItem): BoardPackHorizon {
  if (it.severity === "red") {
    const m = it.missing_artefact_de.toLowerCase();
    if (m.includes("owner") || m.includes("verantwortlich")) return "now";
    if (m.includes("board")) return "now";
    return "this_quarter";
  }
  if (it.tenant_id === "_portfolio") return "this_quarter";
  return "this_quarter";
}

const DEFAULT_OWNER = "Unbekannt – CCO/CISO zuweisen";

function ownerHintFromAttention(it: BoardAttentionItem): string {
  if (it.missing_artefact_de.toLowerCase().includes("verantwortlich")) return DEFAULT_OWNER;
  return DEFAULT_OWNER;
}

function actionTextFromAttention(it: BoardAttentionItem, ref: string): string {
  const m = it.missing_artefact_de;
  const tenant = it.tenant_label?.trim() || it.tenant_id;
  if (m.toLowerCase().includes("verantwortlich") || m.toLowerCase().includes("owner")) {
    return `Verantwortlichen im KI-Register setzen (${tenant}; ${ref}).`;
  }
  if (m.toLowerCase().includes("board-report") || m.toLowerCase().includes("board report")) {
    return `Board-Report aktualisieren (${tenant}; ${ref}).`;
  }
  if (m.toLowerCase().includes("art. 9")) {
    return `Risikomanagement Art. 9 abschließen (${tenant}; ${ref}).`;
  }
  if (m.toLowerCase().includes("nachweis") || m.toLowerCase().includes("doku")) {
    return `Konformitätsnachweis / Dokumentation schließen (${tenant}; ${ref}).`;
  }
  if (it.tenant_id === "_portfolio") {
    return `GTM-fokussiert Governance-Baseline nachziehen (${ref}).`;
  }
  return `Lücke schließen: ${m} (${tenant}; ${ref}).`;
}

let actionIdSeq = 0;
function nextActionId(): string {
  actionIdSeq += 1;
  return `ACT-${String(actionIdSeq).padStart(3, "0")}`;
}

export function buildActionRegister(
  prioritized: BoardAttentionItem[],
  payload: BoardReadinessPayload,
  maxRows: number,
): BoardPackActionRow[] {
  actionIdSeq = 0;
  const seen = new Set<string>();
  const rows: BoardPackActionRow[] = [];

  for (const it of prioritized) {
    if (rows.length >= maxRows) break;
    const ref = briefingRefIdForAttentionItem(it);
    const pillar = inferPillarFromAttention(it);
    const action_de = actionTextFromAttention(it, ref);
    const key = `${pillar}:${action_de.slice(0, 80)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({
      id: nextActionId(),
      priority_rank: rows.length + 1,
      action_de,
      pillar,
      owner_de: ownerHintFromAttention(it),
      horizon: horizonForAttention(it),
      reference_ids: [ref],
      source_attention_id: it.id,
    });
  }

  for (const p of payload.pillars) {
    if (rows.length >= maxRows) break;
    if (p.status !== "red") continue;
    const key = `pillar-sweep:${p.pillar}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({
      id: nextActionId(),
      priority_rank: rows.length + 1,
      action_de: `Portfolio-Säule „${PILLAR_TITLES[p.pillar]}“ entzerren (Review gemappter Mandanten, Indikatoren im Dashboard).`,
      pillar: p.pillar,
      owner_de: DEFAULT_OWNER,
      horizon: "this_quarter",
      reference_ids: [`PILLAR-${p.pillar}`],
    });
  }

  return rows;
}

function priorityRuleLabel(score: number, it: BoardAttentionItem): string {
  const base =
    it.severity === "red" ? "Rot" : it.severity === "amber" ? "Amber" : "Grün";
  const m = it.missing_artefact_de.toLowerCase();
  if (m.includes("verantwortlich") || m.includes("owner")) return `${base} · Owner zuerst`;
  if (m.includes("board")) return `${base} · Board-Report`;
  if (m.includes("art. 9")) return `${base} · Art. 9`;
  if (m.includes("nachweis") || m.includes("doku")) return `${base} · Nachweis/Doku`;
  if (it.tenant_id === "_portfolio") return `${base} · GTM/Portfolio`;
  return `${base} · Sonstige Lücke`;
}

function buildAttentionRows(sorted: BoardAttentionItem[], limit: number): BoardPackAttentionRow[] {
  const filtered = sorted.filter((it) => it.severity !== "green");
  return filtered.slice(0, limit).map((it, i) => ({
    priority_rank: i + 1,
    priority_rule_de: priorityRuleLabel(attentionPriorityScore(it), it),
    severity: it.severity,
    summary_de: `${it.missing_artefact_de} · ${it.tenant_label?.trim() || it.tenant_id}${
      it.subject_name ? ` · „${it.subject_name}“` : ""
    }`,
    reference_id: briefingRefIdForAttentionItem(it),
    tenant_label_de: it.tenant_label?.trim() || it.tenant_id,
    pillar_hint: inferPillarFromAttention(it),
  }));
}

function buildKeyRisks(payload: BoardReadinessPayload, topAttention: BoardAttentionItem[]): string[] {
  const out: string[] = [];
  for (const p of payload.pillars) {
    if (p.status === "red") {
      out.push(
        `Säule ${PILLAR_TITLES[p.pillar]} auf Rot – Details siehe Indikatoren im Board-Readiness-Dashboard.`,
      );
    }
  }
  for (const it of topAttention.filter((x) => x.severity === "red").slice(0, 5)) {
    const ref = briefingRefIdForAttentionItem(it);
    out.push(`${ref}: ${it.missing_artefact_de} (${it.tenant_label?.trim() || it.tenant_id}).`);
  }
  if (!out.length) {
    out.push(
      "Keine roten Ampeln auf Portfolio-Ebene und keine roten Attention-Items im aktuellen Schnappschuss (trotzdem Detailprüfung empfohlen).",
    );
  }
  return out.slice(0, 8);
}

function buildPillarHeadlines(payload: BoardReadinessPayload): string[] {
  return payload.pillars.map(
    (p) =>
      `${PILLAR_TITLES[p.pillar]}: ${trafficWort(p.status)} – ${p.summary_de.split(".")[0] ?? p.summary_de}.`,
  );
}

export function buildBoardPackMarkdownDe(payload: BoardPackPayload): string {
  const m = payload.meta;
  const lines: string[] = [
    `# Quarterly Board Pack – Board Readiness`,
    "",
    `_Erzeugt: ${m.generated_at} · Quelle Dashboard: ${m.source_board_readiness_generated_at}_`,
    "",
    "## Metadaten",
    "",
    `- ${m.scope_de}`,
    `- Gemappte Mandanten: ${m.mapped_tenant_count}`,
    `- Backend erreichbar: ${m.backend_reachable ? "ja" : "teilweise eingeschränkt"}`,
    m.baseline_saved_at
      ? `- Baseline gespeichert: ${m.baseline_saved_at} (Dashboard-Stand ${m.baseline_board_readiness_generated_at ?? "—"})`
      : "- Keine Baseline-Datei (Delta-Abschnitt kann leer sein).",
    "",
    "## Teil A – Executive Memo",
    "",
    "### Ampel je Säule",
    "",
    ...payload.memo.pillar_headlines_de.map((x) => `- ${x}`),
    "",
    "### Änderungen seit Baseline",
    "",
    ...(payload.memo.changes_since_baseline_de.length
      ? payload.memo.changes_since_baseline_de.map((x) => `- ${x}`)
      : ["- (Keine Baseline oder keine Ampel-Änderung erkannt.)"]),
    "",
    "### Wesentliche Risiken / Aufmerksamkeit",
    "",
    ...payload.memo.key_risks_and_concerns_de.map((x) => `- ${x}`),
    "",
    "## Teil B – Attention Items (priorisiert)",
    "",
    "| Rang | Regel | Ampel | Referenz | Kurztext |",
    "| --- | --- | --- | --- | --- |",
    ...payload.attention.map(
      (r) =>
        `| ${r.priority_rank} | ${r.priority_rule_de.replace(/\|/g, "/")} | ${r.severity} | \`${r.reference_id}\` | ${r.summary_de.replace(/\|/g, "/")} |`,
    ),
    "",
    "## Teil C – Aktionsregister",
    "",
    "| ID | Prio | Aktion | Säule | Owner | Horizont | Referenzen |",
    "| --- | --- | --- | --- | --- | --- | --- |",
    ...payload.actions.map((a) => {
      const refs = a.reference_ids.map((x) => `\`${x}\``).join(", ");
      const pillar =
        a.pillar === "portfolio" ? "Portfolio/GTM" : PILLAR_TITLES[a.pillar as BoardReadinessPillarKey];
      return `| ${a.id} | ${a.priority_rank} | ${a.action_de.replace(/\|/g, "/")} | ${pillar} | ${a.owner_de.replace(/\|/g, "/")} | ${BOARD_PACK_HORIZON_LABEL_DE[a.horizon]} | ${refs} |`;
    }),
    "",
    "## Priorisierungsregeln (transparent)",
    "",
    ...m.prioritization_rules_de.map((x) => `- ${x}`),
    "",
    "---",
    "",
    "_Hinweis: Entwurf zur manuellen Freigabe vor Versand an Board/Advisory; keine Rechtsberatung._",
    "",
  ];
  return lines.join("\n");
}

const DEFAULT_ATTENTION_LIMIT = 12;
const DEFAULT_ACTION_LIMIT = 18;

export function generateQuarterlyBoardPack(
  payload: BoardReadinessPayload,
  baseline: BoardReadinessBriefingBaselineFile | null,
): BoardPackPayload {
  const sorted = sortAttentionForBoardPack(payload.attention_items);
  const attention = buildAttentionRows(sorted, DEFAULT_ATTENTION_LIMIT);
  const actions = buildActionRegister(sorted, payload, DEFAULT_ACTION_LIMIT);

  const changes = computeDeltaBulletsDe(payload, baseline);

  const memo: BoardPackExecutiveMemo = {
    title_de: `Board Readiness – Quartals-Pack (${new Date(payload.generated_at).toLocaleDateString("de-DE")})`,
    pillar_headlines_de: buildPillarHeadlines(payload),
    changes_since_baseline_de: changes,
    key_risks_and_concerns_de: buildKeyRisks(payload, sorted),
  };

  const generated_at = new Date().toISOString();

  const meta: BoardPackMetadata = {
    generated_at,
    source_board_readiness_generated_at: payload.generated_at,
    baseline_saved_at: baseline?.saved_at ?? null,
    baseline_board_readiness_generated_at: baseline?.source_board_readiness_generated_at ?? null,
    scope_de:
      "Interne Aggregation über gemappte Mandanten (GTM Product Map) und Live-API-Signale; kein Mandanten-Report im Rechtssinne.",
    mapped_tenant_count: payload.mapped_tenant_count,
    backend_reachable: payload.backend_reachable,
    attention_rows_count: attention.length,
    action_rows_count: actions.length,
    prioritization_rules_de: BOARD_PACK_PRIORITIZATION_RULES_DE,
  };

  const pack: BoardPackPayload = {
    version: BOARD_PACK_VERSION,
    memo,
    attention,
    actions,
    markdown_de: "",
    meta,
  };
  pack.markdown_de = buildBoardPackMarkdownDe(pack);
  return pack;
}

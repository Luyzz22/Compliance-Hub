/**
 * Wave 41 – Attention Queue: Priorisierung, „Warum jetzt?“, regelbasierte Nächster-Schritt-Hinweise.
 * Kein Workflow-Engine; nur Ableitung aus bestehenden Portfolio-Zeilen.
 */

import type { BoardReadinessPillarKey } from "@/lib/boardReadinessTypes";
import type { KanzleiAttentionQueueItem, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";

const PILLAR_KEYS: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

const CODE_TO_DE: Record<string, string> = {
  EU_AI_Act: "EU AI Act",
  ISO_42001: "ISO 42001",
  NIS2: "NIS2",
  DSGVO: "DSGVO",
};

/** Mandanten mit messbarer Last erscheinen in der Queue (kein Task-System). */
export function rowQualifiesForAttentionQueue(row: KanzleiPortfolioRow, manyOpenThreshold: number): boolean {
  if (row.attention_score < 1) return false;
  if (!row.api_fetch_ok) return true;
  if (row.review_stale || row.any_export_stale || row.board_report_stale) return true;
  if (row.gaps_heavy_without_recent_export) return true;
  if (row.open_points_count >= manyOpenThreshold) return true;
  if (row.open_points_hoch >= 1) return true;
  if (PILLAR_KEYS.some((k) => row.pillar_traffic[k] === "red")) return true;
  return row.attention_score >= 22;
}

function firstRedPillarLabel(row: KanzleiPortfolioRow): string | null {
  for (const k of PILLAR_KEYS) {
    if (row.pillar_traffic[k] === "red") {
      const code = k === "eu_ai_act" ? "EU_AI_Act" : k === "iso_42001" ? "ISO_42001" : k === "nis2" ? "NIS2" : "DSGVO";
      return CODE_TO_DE[code] ?? row.top_gap_pillar_label_de;
    }
  }
  return null;
}

function amberPillarCount(row: KanzleiPortfolioRow): number {
  return PILLAR_KEYS.filter((k) => row.pillar_traffic[k] === "amber").length;
}

/** Kurzbegründungen für die Queue (max. vier, priorisiert). */
export function warumJetztForRow(row: KanzleiPortfolioRow, manyOpenThreshold: number): string[] {
  const out: string[] = [];

  if (!row.api_fetch_ok) {
    out.push("API-Daten für diesen Mandanten sind unvollständig oder nicht lesbar.");
  }
  if (row.review_stale) {
    out.push("Formelles Kanzlei-Review ist fällig oder noch nicht erfasst.");
  }
  if (row.never_any_export) {
    out.push("Es liegt noch kein gespeicherter Readiness- oder DATEV-Export vor.");
  } else if (row.any_export_stale) {
    out.push("Export-Kadenz überschritten (Readiness/DATEV zu alt oder Historie fehlerhaft).");
  }
  if (row.board_report_stale) {
    out.push("Mandanten-Board- oder Statusbericht ist überfällig.");
  }
  if (row.gaps_heavy_without_recent_export) {
    out.push("Viele offene Prüfpunkte ohne frischen Export für die Kanzlei-Dokumentation.");
  }
  if (row.open_points_count >= manyOpenThreshold) {
    out.push(`Hohe Anzahl offener Prüfpunkte (${row.open_points_count}, Schwelle ${manyOpenThreshold}).`);
  } else if (row.open_points_hoch >= 1) {
    out.push(`${row.open_points_hoch} offene Punkt(e) mit hoher Dringlichkeit.`);
  }

  const redLabel = firstRedPillarLabel(row);
  if (redLabel) {
    out.push(`Kritische Ampel (${redLabel}); Handlungsbedarf in dieser Säule.`);
  } else if (amberPillarCount(row) >= 2) {
    out.push("Mehrere Säulen auf Beobachten – Gesamtbild im Mandantengespräch klären.");
  }

  if (row.readiness_class === "early_pilot" && out.length < 4) {
    out.push("Pilot-Readiness: Governance-Baseline ist noch dünn.");
  }

  if (out.length === 0 && row.attention_score >= 22) {
    out.push("Kumulierte Risiko-Signale (Attention-Score) – Details in der Portfolio-Zeile prüfen.");
  }

  return out.slice(0, 4);
}

/**
 * Einfache Prioritätskette: blockierendes zuerst, dann Kadenz, dann inhaltliche Lücken.
 */
export function naechsterSchrittForRow(row: KanzleiPortfolioRow, manyOpenThreshold: number): string {
  if (!row.api_fetch_ok) {
    return "Technischen Zugriff prüfen (API/Backend), danach Cockpit erneut laden.";
  }
  if (row.gaps_heavy_without_recent_export) {
    return "Zuerst Readiness-Export oder DATEV-ZIP neu erzeugen, dann offene Prüfpunkte mit Mandant durchgehen.";
  }
  if (row.never_any_export) {
    return "Ersten Mandanten-Readiness-Export oder DATEV-Bundle erzeugen und in der Historie verankern.";
  }
  if (row.any_export_stale) {
    return "Export-Kadenz auffrischen: Readiness-Export oder DATEV-ZIP neu erzeugen.";
  }
  if (row.board_report_stale) {
    return "Board-/Statusbericht im Mandanten aktualisieren (Readiness-Daten erneut beziehen).";
  }
  if (row.review_stale) {
    return "Kanzlei-Review durchführen und in der Historie speichern (optional mit kurzer Notiz).";
  }
  if (row.open_points_hoch >= 1 && row.top_gap_pillar_label_de) {
    return `Dringliche offene Punkte zur Säule „${row.top_gap_pillar_label_de}“ mit Mandant besprechen.`;
  }
  if (row.open_points_count >= manyOpenThreshold && row.top_gap_pillar_label_de) {
    return `Offene ${row.top_gap_pillar_label_de}-Prüfpunkte priorisieren und Termin mit Mandant setzen.`;
  }
  const red = firstRedPillarLabel(row);
  if (red) {
    return `Säule „${red}“ vertiefen: Maßnahmen und Nachweise mit Mandant abstimmen.`;
  }
  if (row.readiness_class === "early_pilot") {
    return "Governance-Baseline mit Mandant schärfen (Rollen, Nachweise, Pilot-Meilensteine).";
  }
  return "Portfolio-Zeile und Signale kurz prüfen; nächste Maßnahme dokumentieren.";
}

export function buildAttentionQueue(
  rows: KanzleiPortfolioRow[],
  manyOpenThreshold: number,
): KanzleiAttentionQueueItem[] {
  const picked = rows
    .filter((r) => rowQualifiesForAttentionQueue(r, manyOpenThreshold))
    .sort((a, b) => {
      if (b.attention_score !== a.attention_score) return b.attention_score - a.attention_score;
      if (b.open_points_count !== a.open_points_count) return b.open_points_count - a.open_points_count;
      return (a.mandant_label ?? a.tenant_id).localeCompare(b.mandant_label ?? b.tenant_id, "de");
    });
  return picked.map((row) => ({
    tenant_id: row.tenant_id,
    mandant_label: row.mandant_label,
    attention_score: row.attention_score,
    warum_jetzt_de: warumJetztForRow(row, manyOpenThreshold),
    naechster_schritt_de: naechsterSchrittForRow(row, manyOpenThreshold),
    links: row.links,
  }));
}

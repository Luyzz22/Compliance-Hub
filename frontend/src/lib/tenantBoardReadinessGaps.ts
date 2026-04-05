/**
 * Shared gap / open-point logic for Board Readiness and Mandant advisor exports.
 * Pure helpers (no server-only) so tests can import without Next server graph issues.
 */

import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";
import { BOARD_REPORT_FRESH_DAYS } from "@/lib/boardReadinessThresholds";
import { isoInWindow, windowBoundsMs } from "@/lib/gtmDashboardTime";

export const EU_AI_ACT_ART9 = "art9_risk_management";
export const EU_AI_ACT_ART11 = "art11_technical_documentation";

export function complianceGapStatus(
  rows: { requirement_id: string; status: string }[] | undefined,
  reqId: string,
): string | undefined {
  return rows?.find((r) => r.requirement_id === reqId)?.status;
}

export function countSavedAiActDocSections(raw: TenantBoardReadinessRaw, sysId: string): number {
  const items = raw.ai_act_doc_items_by_system[sysId] ?? [];
  return items.filter((it) => it.status === "saved").length;
}

/** Art. 11 abgeschlossen oder ausreichend gespeicherte AI-Act-Doku-Sektionen. */
export function evidenceBundleComplete(raw: TenantBoardReadinessRaw, sysId: string): boolean {
  const st = complianceGapStatus(raw.compliance_by_system[sysId], EU_AI_ACT_ART11);
  if (st === "completed") return true;
  return countSavedAiActDocSections(raw, sysId) >= 2;
}

export function boardComplianceReportFresh(raw: TenantBoardReadinessRaw, nowMs: number): boolean {
  const latest = raw.board_reports[0];
  if (!latest?.created_at) return false;
  const w = windowBoundsMs(BOARD_REPORT_FRESH_DAYS, nowMs);
  return isoInWindow(latest.created_at, w.start, w.end);
}

/** Ein offener Prüfpunkt für Mandanten- / Advisor-Export (Kanzlei-Semantik). */
export type MandantOffenerPunkt = {
  id: string;
  dringlichkeit: "hoch" | "mittel";
  pruefpunkt_de: string;
  ki_system_id?: string;
  ki_system_name?: string;
  referenz_id: string;
  workspace_path?: string;
  api_pfad?: string;
  letzte_aenderung_iso?: string | null;
};

/** Säulen-Code für offene Punkte (Kanzlei-Export / Portfolio). */
export function pillarCodeForOpenPoint(p: MandantOffenerPunkt): string {
  if (p.id.startsWith("board:")) return "EU_AI_Act";
  const t = p.pruefpunkt_de.toLowerCase();
  if (t.includes("nis2")) return "NIS2";
  if (t.includes("dsgvo") || t.includes("datenschutz")) return "DSGVO";
  if (t.includes("iso")) return "ISO_42001";
  return "EU_AI_Act";
}

function refKi(sysId: string): string {
  return `HR-AI-${sysId}`;
}

function refMandant(tenantId: string): string {
  return `TENANT-${tenantId}`;
}

/**
 * Offene Punkte für einen Mandanten aus Roh-API-Daten (High-Risk-Fokus + Board-Report).
 * Wiederverwendbare Logik neben Board-Readiness-Aggregation.
 */
export function computeMandantOffenePunkte(
  tenantId: string,
  raw: TenantBoardReadinessRaw,
  nowMs: number,
): MandantOffenerPunkt[] {
  const out: MandantOffenerPunkt[] = [];
  const hrIds =
    raw.compliance_dashboard?.systems.filter((s) => s.risk_level === "high_risk").map((s) => s.ai_system_id) ??
    [];

  for (const id of hrIds) {
    const sys = raw.ai_systems.find((s) => s.id === id);
    const name = sys?.name ?? id;
    const updated = sys?.updated_at_utc ?? null;

    if (!String(sys?.owner_email || "").trim()) {
      out.push({
        id: `owner:${tenantId}:${id}`,
        dringlichkeit: "hoch",
        pruefpunkt_de: `Verantwortliche/r für KI-Anwendung nicht hinterlegt (fachliche Zuordnung für Prüfung).`,
        ki_system_id: id,
        ki_system_name: name,
        referenz_id: refKi(id),
        workspace_path: `/tenant/ai-systems/${id}`,
        api_pfad: `/api/v1/ai-systems/${id}`,
        letzte_aenderung_iso: updated ?? null,
      });
    }

    if (complianceGapStatus(raw.compliance_by_system[id], EU_AI_ACT_ART9) !== "completed") {
      out.push({
        id: `art9:${tenantId}:${id}`,
        dringlichkeit: "mittel",
        pruefpunkt_de: `Risikomanagement (EU AI Act Art. 9) für Hochrisiko-KI nicht als abgeschlossen geführt.`,
        ki_system_id: id,
        ki_system_name: name,
        referenz_id: refKi(id),
        workspace_path: `/tenant/eu-ai-act`,
        api_pfad: `/api/v1/ai-systems/${id}/compliance`,
        letzte_aenderung_iso: updated ?? null,
      });
    }

    if (!evidenceBundleComplete(raw, id)) {
      out.push({
        id: `evidence:${tenantId}:${id}`,
        dringlichkeit: "mittel",
        pruefpunkt_de: `Nachweis-/Dokumentationspaket unvollständig (technische Dokumentation / AI-Act-Bausteine).`,
        ki_system_id: id,
        ki_system_name: name,
        referenz_id: refKi(id),
        workspace_path: `/tenant/ai-systems/${id}`,
        api_pfad: `/api/v1/ai-systems/${id}/ai-act-docs`,
        letzte_aenderung_iso: updated ?? null,
      });
    }
  }

  if (hrIds.length && !boardComplianceReportFresh(raw, nowMs)) {
    const br = raw.board_reports[0];
    out.push({
      id: `board:${tenantId}`,
      dringlichkeit: "hoch",
      pruefpunkt_de: `Bericht für Mandantenführung / Board nicht im empfohlenen Zeitraum (${BOARD_REPORT_FRESH_DAYS} Tage) aktualisiert.`,
      referenz_id: refMandant(tenantId),
      workspace_path: "/board/ai-compliance-report",
      api_pfad: `/api/v1/tenants/${tenantId}/board/ai-compliance-reports`,
      letzte_aenderung_iso: br?.created_at ?? null,
    });
  }

  return out;
}

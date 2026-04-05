/**
 * DATEV-adjacent Kanzlei-Arbeitspaket (Wave 38): stable filenames + semicolon CSV for Excel (DE).
 * Reuses Mandanten-Readiness narrative and the same open-point rules as tenantBoardReadinessGaps.
 */

import JSZip from "jszip";

import {
  boardComplianceReportFresh,
  pillarCodeForOpenPoint,
  type MandantOffenerPunkt,
} from "@/lib/tenantBoardReadinessGaps";
import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";

export const DATEV_KANZLEI_BUNDLE_VERSION = "wave38-v1";

const CSV_SEP = ";";

/** UTF-8 BOM so Excel (DE) opens UTF-8 correctly. */
export const EXCEL_UTF8_BOM = "\uFEFF";

export { pillarCodeForOpenPoint };

export function objectTypeForOpenPoint(p: MandantOffenerPunkt): string {
  if (p.id.startsWith("owner:")) return "AI_System";
  if (p.id.startsWith("art9:")) return "Obligation";
  if (p.id.startsWith("evidence:")) return "Evidence_Bundle";
  if (p.id.startsWith("board:")) return "Board_Report";
  return "Other";
}

export function fristHinweisDe(p: MandantOffenerPunkt): string {
  if (p.dringlichkeit === "hoch") return "Kurzfristig (ca. 14 Tage)";
  return "Dieses Geschäftsjahr / Quartal";
}

function verantwortlicheForPunkt(p: MandantOffenerPunkt, raw: TenantBoardReadinessRaw): string {
  if (p.ki_system_id) {
    const sys = raw.ai_systems.find((s) => s.id === p.ki_system_id);
    const em = String(sys?.owner_email ?? "").trim();
    if (em) return em;
  }
  return "offen / zuweisen";
}

/** Escape one CSV field; delimiter is semicolon (Excel DE). */
export function csvCellSemicolon(value: string): string {
  const v = value.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const needsQuote = /[";\n]/.test(v);
  const escaped = v.replace(/"/g, '""');
  return needsQuote ? `"${escaped}"` : escaped;
}

export function csvLineSemicolon(fields: string[]): string {
  return fields.map(csvCellSemicolon).join(CSV_SEP);
}

const OFFENE_PUNKTE_HEADER = [
  "mandant_id",
  "pillar",
  "object_type",
  "object_reference",
  "issue_summary",
  "priority",
  "owner",
  "due_hint",
  "last_update",
] as const;

const NACHWEIS_HEADER = [
  "reference_id",
  "type",
  "related_system_or_tenant",
  "status",
  "date_freshness",
  "note_de",
] as const;

export function buildOffenePunkteCsv(
  mandantId: string,
  raw: TenantBoardReadinessRaw,
  punkte: MandantOffenerPunkt[],
): string {
  const lines: string[] = [csvLineSemicolon([...OFFENE_PUNKTE_HEADER])];
  for (const p of punkte) {
    lines.push(
      csvLineSemicolon([
        mandantId,
        pillarCodeForOpenPoint(p),
        objectTypeForOpenPoint(p),
        p.referenz_id,
        p.pruefpunkt_de,
        p.dringlichkeit,
        verantwortlicheForPunkt(p, raw),
        fristHinweisDe(p),
        p.letzte_aenderung_iso ?? "",
      ]),
    );
  }
  return EXCEL_UTF8_BOM + lines.join("\n") + "\n";
}

export type NachweisReferenzRow = {
  reference_id: string;
  type: string;
  related_system_or_tenant: string;
  status: string;
  date_freshness: string;
  note_de: string;
};

export function buildNachweisReferenzenRows(
  mandantId: string,
  raw: TenantBoardReadinessRaw,
  nowMs: number,
): NachweisReferenzRow[] {
  const rows: NachweisReferenzRow[] = [];
  const br = raw.board_reports[0];
  if (br) {
    const fresh = boardComplianceReportFresh(raw, nowMs);
    rows.push({
      reference_id: `BOARD-${br.id}`,
      type: "board_report",
      related_system_or_tenant: mandantId,
      status: fresh ? "aktuell" : "aktualisierung_empfohlen",
      date_freshness: br.created_at,
      note_de: br.title,
    });
  }

  const eu = raw.eu_ai_act_readiness;
  if (eu) {
    const pct =
      eu.overall_readiness !== undefined
        ? `${Math.round(Number(eu.overall_readiness) * 1000) / 10}%`
        : "n/a";
    const inc = eu.high_risk_systems_essential_incomplete ?? 0;
    rows.push({
      reference_id: `EU-AI-ACT-READINESS-${mandantId}`,
      type: "risk_readiness_aggregate",
      related_system_or_tenant: mandantId,
      status: inc === 0 ? "hr_pflichtnachweise_vollstaendig" : `hr_offen_${inc}`,
      date_freshness: new Date(nowMs).toISOString().slice(0, 10),
      note_de: `EU AI Act Readiness (rechnerisch) ${pct}`,
    });
  }

  const hr = raw.compliance_dashboard?.systems.filter((s) => s.risk_level === "high_risk") ?? [];
  for (const s of hr.slice(0, 50)) {
    const sys = raw.ai_systems.find((a) => a.id === s.ai_system_id);
    rows.push({
      reference_id: `HR-AI-${s.ai_system_id}`,
      type: "ai_system",
      related_system_or_tenant: s.ai_system_id,
      status:
        s.readiness_score !== undefined ? `readiness_score_${s.readiness_score}` : "high_risk",
      date_freshness: sys?.updated_at_utc ?? "",
      note_de: s.ai_system_name || s.ai_system_id,
    });
  }

  const nis2 = raw.ai_compliance_overview?.nis2_kritis_kpi_mean_percent;
  if (nis2 != null) {
    rows.push({
      reference_id: `NIS2-KPI-${mandantId}`,
      type: "nis2_kpi_snapshot",
      related_system_or_tenant: mandantId,
      status: "snapshot",
      date_freshness: new Date(nowMs).toISOString().slice(0, 10),
      note_de: `NIS2 KRITIS KPI Mittelwert ${nis2}% (Dashboard)`,
    });
  }

  return rows;
}

export function buildNachweisReferenzenCsv(
  mandantId: string,
  raw: TenantBoardReadinessRaw,
  nowMs: number,
): string {
  const rows = buildNachweisReferenzenRows(mandantId, raw, nowMs);
  const lines: string[] = [csvLineSemicolon([...NACHWEIS_HEADER])];
  for (const r of rows) {
    lines.push(
      csvLineSemicolon([
        r.reference_id,
        r.type,
        r.related_system_or_tenant,
        r.status,
        r.date_freshness,
        r.note_de,
      ]),
    );
  }
  return EXCEL_UTF8_BOM + lines.join("\n") + "\n";
}

export function buildDatevKanzleiMetadataJson(input: {
  mandantId: string;
  generatedAtIso: string;
  exportPayloadVersion: string;
  apiFetchOk: boolean;
}): string {
  const meta = {
    bundle_version: DATEV_KANZLEI_BUNDLE_VERSION,
    mandant_id: input.mandantId,
    generated_at: input.generatedAtIso,
    source: "compliancehub_internal_advisor",
    mandanten_readiness_export_version: input.exportPayloadVersion,
    api_fetch_ok: input.apiFetchOk,
    files: [
      "01-mandantenstatus.md",
      "02-offene-punkte.csv",
      "03-nachweis-referenzen.csv",
      "04-metadata.json",
    ],
    hinweis_de:
      "Arbeitspaket für Kanzlei/DMS; keine automatische DATEV-Schnittstelle. Spaltentrenner Semikolon (Excel DE).",
  };
  return `${JSON.stringify(meta, null, 2)}\n`;
}

export type DatevKanzleiBundleFiles = {
  "01-mandantenstatus.md": string;
  "02-offene-punkte.csv": string;
  "03-nachweis-referenzen.csv": string;
  "04-metadata.json": string;
};

export function buildDatevKanzleiBundleFiles(input: {
  mandantReadinessMarkdownDe: string;
  mandantId: string;
  raw: TenantBoardReadinessRaw;
  punkte: MandantOffenerPunkt[];
  nowMs: number;
  exportPayloadVersion: string;
  generatedAtIso: string;
}): DatevKanzleiBundleFiles {
  const md = input.mandantReadinessMarkdownDe;
  const csvOpen = buildOffenePunkteCsv(input.mandantId, input.raw, input.punkte);
  const csvNach = buildNachweisReferenzenCsv(input.mandantId, input.raw, input.nowMs);
  const meta = buildDatevKanzleiMetadataJson({
    mandantId: input.mandantId,
    generatedAtIso: input.generatedAtIso,
    exportPayloadVersion: input.exportPayloadVersion,
    apiFetchOk: input.raw.fetch_ok,
  });
  return {
    "01-mandantenstatus.md": md,
    "02-offene-punkte.csv": csvOpen,
    "03-nachweis-referenzen.csv": csvNach,
    "04-metadata.json": meta,
  };
}

export async function zipDatevKanzleiBundle(files: DatevKanzleiBundleFiles): Promise<Buffer> {
  const zip = new JSZip();
  zip.file("01-mandantenstatus.md", files["01-mandantenstatus.md"]);
  zip.file("02-offene-punkte.csv", files["02-offene-punkte.csv"]);
  zip.file("03-nachweis-referenzen.csv", files["03-nachweis-referenzen.csv"]);
  zip.file("04-metadata.json", files["04-metadata.json"]);
  const buf = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  return buf;
}

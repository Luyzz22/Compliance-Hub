"use client";

import React, { useState } from "react";

import { getBoardKpiExportUrl } from "@/lib/api";

const TIP_JSON =
  "Strukturierter Export: alle KI-Systeme des Tenants mit NIS2-/KRITIS-KPI-Werten " +
  "(Incident-Reife, Supplier-Risk, OT/IT-Segmentierung), Szenario-Profil-ID, " +
  "Risk-Level, AI-Act-Kategorie sowie Envelope-Felder (regulatory_scope, generated_by) " +
  "für DMS- und Integrationspfade.";

const TIP_CSV =
  "Tabellarischer Export derselben Systemzeilen wie JSON – ideal für Excel, " +
  "WP-Arbeitsmappen, DATEV-/DMS-Importe und manuelle Prüfung durch Kanzleien.";

export function BoardKpiAdvisorExport() {
  const [format, setFormat] = useState<"json" | "csv">("json");

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
        <label className="text-xs font-semibold text-slate-700">
          Export für WP / DMS / DATEV
          <select
            className="ml-2 mt-1 block rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-normal text-slate-800 sm:mt-0 sm:inline-block"
            value={format}
            onChange={(e) => setFormat(e.target.value as "json" | "csv")}
            aria-label="Exportformat für Berater und Archivierung"
          >
            <option value="json" title={TIP_JSON}>
              JSON (API / DMS-Pipeline)
            </option>
            <option value="csv" title={TIP_CSV}>
              CSV (Excel / WP / DATEV-Import)
            </option>
          </select>
        </label>
        <span className="text-xs text-slate-600" title={format === "json" ? TIP_JSON : TIP_CSV}>
          {format === "json" ? TIP_JSON : TIP_CSV}
        </span>
        <a
          href={getBoardKpiExportUrl(format)}
          download
          className="inline-flex shrink-0 items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 underline-offset-2 hover:bg-slate-100 hover:underline"
        >
          Datei herunterladen
        </a>
      </div>
    </div>
  );
}

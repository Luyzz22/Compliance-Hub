"use client";

import { useState } from "react";

type VVTEntry = {
  processing_activity: string;
  data_categories: string[];
  purpose: string;
  legal_basis: string;
  recipients: string[];
  retention_period: string;
  technical_measures: string[];
};

const SAMPLE_VVT: VVTEntry[] = [
  {
    processing_activity: "login_success",
    data_categories: ["session"],
    purpose: "Compliance-Verarbeitung: login_success",
    legal_basis: "Art. 6 Abs. 1 lit. c/f DSGVO",
    recipients: ["Compliance-Hub System", "Tenant-Administratoren"],
    retention_period: "10 Jahre (GoBD / AO)",
    technical_measures: ["SHA-256 Hashketten-Integrität", "Append-only Speicherung", "Row-Level-Security", "TLS 1.3 Verschlüsselung"],
  },
  {
    processing_activity: "role_change",
    data_categories: ["user_role"],
    purpose: "Compliance-Verarbeitung: role_change",
    legal_basis: "Art. 6 Abs. 1 lit. c/f DSGVO",
    recipients: ["Compliance-Hub System", "Tenant-Administratoren"],
    retention_period: "10 Jahre (GoBD / AO)",
    technical_measures: ["SHA-256 Hashketten-Integrität", "Append-only Speicherung", "Row-Level-Security", "TLS 1.3 Verschlüsselung"],
  },
  {
    processing_activity: "update_ai_system",
    data_categories: ["ai_system"],
    purpose: "Compliance-Verarbeitung: update_ai_system",
    legal_basis: "Art. 6 Abs. 1 lit. c/f DSGVO",
    recipients: ["Compliance-Hub System", "Tenant-Administratoren"],
    retention_period: "10 Jahre (GoBD / AO)",
    technical_measures: ["SHA-256 Hashketten-Integrität", "Append-only Speicherung", "Row-Level-Security", "TLS 1.3 Verschlüsselung"],
  },
];

export function VVTExportClient() {
  const [exportFormat, setExportFormat] = useState<"json" | "pdf">("json");

  return (
    <div className="min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <nav className="mb-2 flex items-center gap-1 text-xs">
            <a href="/admin/audit-log" className="text-xs font-medium text-slate-500 hover:text-cyan-700 transition">
              Audit-Log
            </a>
            <span className="text-xs text-slate-300 select-none">/</span>
            <span className="text-xs font-semibold text-slate-800">VVT-Export</span>
          </nav>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            DSGVO Art. 30 · Verarbeitungsverzeichnis
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2rem] sm:leading-tight">
            Verarbeitungsverzeichnis (VVT)
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
            Automatisch generiertes Verzeichnis aller Verarbeitungstätigkeiten gemäß Art. 30 DSGVO,
            abgeleitet aus dem Audit-Trail.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setExportFormat("json")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              exportFormat === "json" ? "bg-cyan-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            JSON
          </button>
          <button
            onClick={() => setExportFormat("pdf")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              exportFormat === "pdf" ? "bg-cyan-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            PDF
          </button>
          <button className="inline-flex items-center justify-center rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-700">
            📥 {exportFormat.toUpperCase()} herunterladen
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Verarbeitungen</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{SAMPLE_VVT.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Rechtsgrundlage</p>
          <p className="mt-1 text-sm font-medium text-slate-800">Art. 6 Abs. 1 lit. c/f DSGVO</p>
        </div>
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Aufbewahrung</p>
          <p className="mt-1 text-sm font-medium text-slate-800">10 Jahre (GoBD / AO)</p>
        </div>
      </div>

      {/* VVT Entries */}
      <div className="space-y-4">
        {SAMPLE_VVT.map((entry, idx) => (
          <div key={idx} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-900">{entry.processing_activity}</h3>
                <p className="mt-1 text-sm text-slate-600">{entry.purpose}</p>
              </div>
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset bg-cyan-100 text-cyan-900 ring-cyan-200/70">
                Art. 30 DSGVO
              </span>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Datenkategorien</p>
                <p className="mt-0.5 text-sm text-slate-700">{entry.data_categories.join(", ")}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Rechtsgrundlage</p>
                <p className="mt-0.5 text-sm text-slate-700">{entry.legal_basis}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Empfänger</p>
                <p className="mt-0.5 text-sm text-slate-700">{entry.recipients.join(", ")}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Aufbewahrungsfrist</p>
                <p className="mt-0.5 text-sm text-slate-700">{entry.retention_period}</p>
              </div>
              <div className="sm:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Technische Maßnahmen</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {entry.technical_measures.map((m, mi) => (
                    <span key={mi} className="inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset bg-slate-100 text-slate-700 ring-slate-200/70">
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

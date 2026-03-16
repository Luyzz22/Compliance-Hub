"use client";

import React, { useState } from "react";
import {
  createBoardReportExportJob,
  type BoardReportExportJob,
  type BoardReportTargetSystem,
} from "@/lib/api";

const TARGET_LABELS: Record<BoardReportTargetSystem, string> = {
  generic_webhook: "Generischer Webhook",
  sap_btp: "SAP BTP",
  sharepoint: "SharePoint",
  sap_btp_http: "SAP BTP HTTP",
  dms_generic: "DMS (generisch – vorbereitet)",
  datev_dms_prepared: "Steuerkanzlei / DATEV-DMS (vorbereitet)",
};

export function BoardReportExportForm() {
  const [targetSystem, setTargetSystem] =
    useState<BoardReportTargetSystem>("generic_webhook");
  const [callbackUrl, setCallbackUrl] = useState("");
  const [metadata, setMetadata] = useState({
    mandant_nr: "",
    mandant_name: "",
    aktenzeichen: "",
    berichtszeitraum_von: "",
    berichtszeitraum_bis: "",
  });
  const [loading, setLoading] = useState(false);
  const [lastJob, setLastJob] = useState<BoardReportExportJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const needsCallback =
    targetSystem === "generic_webhook" ||
    targetSystem === "sap_btp_http" ||
    targetSystem === "datev_dms_prepared";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLastJob(null);

    if (needsCallback && !callbackUrl.trim()) {
      const messages: Record<string, string> = {
        generic_webhook: "Bei „Generischer Webhook“ ist eine Callback-URL erforderlich.",
        sap_btp_http: "Bei „SAP BTP HTTP“ ist eine Callback-URL erforderlich.",
        datev_dms_prepared:
          "Bei „Steuerkanzlei / DATEV-DMS“ ist eine Callback-URL erforderlich.",
      };
      setError(messages[targetSystem] ?? "Callback-URL erforderlich.");
      return;
    }

    const meta =
      targetSystem === "datev_dms_prepared"
        ? Object.fromEntries(
            Object.entries(metadata).filter(([, v]) => v.trim() !== "")
          )
        : undefined;

    setLoading(true);
    try {
      const job = await createBoardReportExportJob({
        target_system: targetSystem,
        callback_url: needsCallback ? callbackUrl.trim() || null : null,
        metadata: meta && Object.keys(meta).length > 0 ? meta : undefined,
      });
      setLastJob(job);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Export fehlgeschlagen. Bitte erneut versuchen."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      aria-label="Externer Export"
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
        Externer Export
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Vorbereitung für PDF-/DMS-/SAP-BTP-Integration: Board-Report (JSON +
        Markdown) an ein externes System senden (z. B. Webhook für
        Weiterverarbeitung oder Archiv).
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="board-export-target"
            className="block text-xs font-medium text-slate-700"
          >
            Zielsystem
          </label>
          <select
            id="board-export-target"
            value={targetSystem}
            onChange={(e) =>
              setTargetSystem(e.target.value as BoardReportTargetSystem)
            }
            className="mt-1 block w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            <option value="generic_webhook">
              {TARGET_LABELS.generic_webhook}
            </option>
            <option value="sap_btp_http">{TARGET_LABELS.sap_btp_http}</option>
            <option value="dms_generic">{TARGET_LABELS.dms_generic}</option>
            <option value="datev_dms_prepared">
              {TARGET_LABELS.datev_dms_prepared}
            </option>
          </select>
          {targetSystem === "sap_btp_http" && (
            <p className="mt-1 text-xs text-slate-500">
              Für Anbindung an SAP Cloud Integration / BTP HTTP-Inbound-Flows.
            </p>
          )}
          {targetSystem === "dms_generic" && (
            <p className="mt-1 text-xs text-slate-500">
              DMS-/Archiv-Anbindung vorbereitet; Integration folgt.
            </p>
          )}
          {targetSystem === "datev_dms_prepared" && (
            <p className="mt-1 text-xs text-slate-500">
              Optimiert für Weiterleitung an DATEV-/Kanzlei-DMS (Mandanten-Akte,
              Prüfungsdokumentation, EU-AI-Act-/NIS2-Nachweise).
            </p>
          )}
        </div>

        {needsCallback && (
          <div>
            <label
              htmlFor="board-export-callback-url"
              className="block text-xs font-medium text-slate-700"
            >
              Callback-URL <span className="text-red-600">*</span>
            </label>
            <input
              id="board-export-callback-url"
              type="url"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
              placeholder="https://..."
              className="mt-1 block w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              required={needsCallback}
            />
          </div>
        )}

        {targetSystem === "datev_dms_prepared" && (
          <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50/50 p-3">
            <p className="text-xs font-medium text-slate-600">
              Optionale Metadaten (Mandant, Aktenzeichen, Zeitraum)
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                type="text"
                value={metadata.mandant_nr}
                onChange={(e) =>
                  setMetadata((m) => ({ ...m, mandant_nr: e.target.value }))
                }
                placeholder="Mandantennummer"
                className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              />
              <input
                type="text"
                value={metadata.mandant_name}
                onChange={(e) =>
                  setMetadata((m) => ({ ...m, mandant_name: e.target.value }))
                }
                placeholder="Mandantenname"
                className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              />
              <input
                type="text"
                value={metadata.aktenzeichen}
                onChange={(e) =>
                  setMetadata((m) => ({ ...m, aktenzeichen: e.target.value }))
                }
                placeholder="Aktenzeichen"
                className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              />
              <input
                type="text"
                value={metadata.berichtszeitraum_von}
                onChange={(e) =>
                  setMetadata((m) => ({
                    ...m,
                    berichtszeitraum_von: e.target.value,
                  }))
                }
                placeholder="Zeitraum von (z. B. 2025-01-01)"
                className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              />
              <input
                type="text"
                value={metadata.berichtszeitraum_bis}
                onChange={(e) =>
                  setMetadata((m) => ({
                    ...m,
                    berichtszeitraum_bis: e.target.value,
                  }))
                }
                placeholder="Zeitraum bis (z. B. 2026-01-01)"
                className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              />
            </div>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
          >
            {error}
          </div>
        )}

        {lastJob && (
          <div
            className={`rounded-lg border px-3 py-2 text-sm ${
              lastJob.status === "failed"
                ? "border-red-200 bg-red-50 text-red-800"
                : lastJob.status === "not_implemented"
                  ? "border-amber-200 bg-amber-50 text-amber-800"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800"
            }`}
          >
            <p className="font-medium">
              {lastJob.status === "sent"
                ? "Export erfolgreich gesendet."
                : lastJob.status === "not_implemented"
                  ? "Zielsystem noch nicht implementiert."
                  : "Export fehlgeschlagen."}
            </p>
            <p className="mt-1 text-xs">
              Job-ID: {lastJob.id} · Status: {lastJob.status}
              {lastJob.error_message && ` · ${lastJob.error_message}`}
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {loading
            ? "Wird gesendet…"
            : "Board-Report an externes System senden"}
        </button>
      </form>
    </section>
  );
}

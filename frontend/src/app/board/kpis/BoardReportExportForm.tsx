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
};

export function BoardReportExportForm() {
  const [targetSystem, setTargetSystem] =
    useState<BoardReportTargetSystem>("generic_webhook");
  const [callbackUrl, setCallbackUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastJob, setLastJob] = useState<BoardReportExportJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLastJob(null);

    if (targetSystem === "generic_webhook" && !callbackUrl.trim()) {
      setError("Bei „Generischer Webhook“ ist eine Callback-URL erforderlich.");
      return;
    }

    setLoading(true);
    try {
      const job = await createBoardReportExportJob({
        target_system: targetSystem,
        callback_url:
          targetSystem === "generic_webhook" ? callbackUrl.trim() || null : null,
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
          </select>
        </div>

        {targetSystem === "generic_webhook" && (
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
              required={targetSystem === "generic_webhook"}
            />
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
                : "border-emerald-200 bg-emerald-50 text-emerald-800"
            }`}
          >
            <p className="font-medium">
              {lastJob.status === "sent"
                ? "Export erfolgreich gesendet."
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

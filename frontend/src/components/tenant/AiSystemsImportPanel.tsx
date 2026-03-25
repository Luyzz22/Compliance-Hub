"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import {
  importAiSystemsFile,
  type AIImportResult,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY } from "@/lib/boardLayout";

const EXPECTED_HEADERS =
  "id, name, description, business_unit, risk_level, ai_act_category, owner_email, criticality, data_sensitivity, has_incident_runbook, has_supplier_risk_register, has_backup_runbook, gdpr_dpia_required";

type PanelProps = {
  /** Demo read-only: Import deaktivieren. */
  mutationsBlocked?: boolean;
  blockedHint?: string;
};

export function AiSystemsImportPanel(props: PanelProps = {}) {
  const { mutationsBlocked = false, blockedHint } = props;
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AIImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function close() {
    setOpen(false);
    setResult(null);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function submit() {
    const file = inputRef.current?.files?.[0];
    if (!file) {
      setError("Bitte eine CSV- oder Excel-Datei (.xlsx) auswählen.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await importAiSystemsFile(file);
      setResult(r);
      if (r.imported_count > 0) {
        router.refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className={`${CH_BTN_SECONDARY} shrink-0 text-xs disabled:cursor-not-allowed disabled:opacity-50`}
        onClick={() => {
          if (!mutationsBlocked) setOpen(true);
        }}
        disabled={mutationsBlocked}
        title={
          mutationsBlocked
            ? blockedHint || "Im Demo-Mandanten (read-only) nicht verfügbar"
            : undefined
        }
        data-testid="ai-systems-import-trigger"
      >
        AI-Systeme importieren (CSV/Excel)
      </button>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          close();
        }
      }}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-import-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="ai-import-title"
          className="text-lg font-semibold text-slate-900"
        >
          AI-Systeme importieren
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Erste Zeile = Spaltenüberschriften. Unterstützt CSV (UTF-8) und Excel{" "}
          <span className="whitespace-nowrap">(.xlsx)</span>.
        </p>
        <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 font-mono text-[11px] leading-relaxed text-slate-700">
          {EXPECTED_HEADERS}
        </p>
        <p className="mt-2 text-xs text-slate-500">
          <Link
            href="/ai-systems-template.csv"
            className="font-semibold text-cyan-700 underline decoration-cyan-600/30 hover:text-cyan-900"
            download
          >
            Muster-CSV herunterladen
          </Link>
        </p>

        <div className="mt-4">
          <label className="block text-xs font-medium text-slate-600" htmlFor="ai-import-file">
            Datei
          </label>
          <input
            id="ai-import-file"
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="mt-1 block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-cyan-900 hover:file:bg-cyan-100"
          />
        </div>

        {error ? (
          <p
            className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        {result ? (
          <div className="mt-4 space-y-3 text-sm">
            <p className="font-medium text-slate-800">
              Verarbeitet: {result.total_rows} Zeilen · importiert:{" "}
              <span className="tabular-nums text-emerald-700">
                {result.imported_count}
              </span>{" "}
              · fehlgeschlagen:{" "}
              <span className="tabular-nums text-rose-700">
                {result.failed_count}
              </span>
            </p>
            {result.errors.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Fehler pro Zeile
                </p>
                <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs">
                  {result.errors.map((err, i) => (
                    <li key={`${err.row_number}-${i}`} className="text-slate-800">
                      <span className="font-mono font-semibold text-slate-600">
                        Zeile {err.row_number}
                      </span>
                      : {err.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-emerald-800">Import ohne Zeilenfehler abgeschlossen.</p>
            )}
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
          <button type="button" className={CH_BTN_SECONDARY} onClick={close}>
            Schließen
          </button>
          <button
            type="button"
            className={`${CH_BTN_PRIMARY} min-w-[11rem]`}
            onClick={() => void submit()}
            disabled={busy}
          >
            {busy ? "Wird importiert…" : "Datei prüfen und importieren"}
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { fetchBoardReports, generateBoardReport, type BoardReportListItemDto } from "@/lib/boardReportingApi";
import { CH_BTN_PRIMARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

interface Props {
  tenantId: string;
}

function currentMonthlyBounds() {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0, 23, 59, 59));
  const periodKey = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
  return { start, end, periodKey };
}

export function BoardReportsHubClient({ tenantId }: Props) {
  const [rows, setRows] = useState<BoardReportListItemDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setError(null);
    try {
      setRows(await fetchBoardReports(tenantId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
    }
  }, [tenantId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onGenerateMonthly() {
    setBusy(true);
    setError(null);
    try {
      const b = currentMonthlyBounds();
      const report = await generateBoardReport(tenantId, {
        period_key: b.periodKey,
        period_type: "monthly",
        period_start: b.start.toISOString(),
        period_end: b.end.toISOString(),
      });
      window.location.href = `/tenant/governance/board-reports/${report.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generierung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Governance</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">Board Reporting &amp; Management Pack</h1>
          <p className="mt-2 text-sm text-slate-600">
            Kompakter Executive Pack aus Audit-Readiness, Controls, Reviews und Operations-Resilience.
          </p>
        </div>
        <button type="button" onClick={() => void onGenerateMonthly()} className={CH_BTN_PRIMARY} disabled={busy}>
          {busy ? "Generiert..." : "Monatsreport erzeugen"}
        </button>
      </div>

      {error ? (
        <p className="text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}

      <article className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Vorhandene Reports</p>
        <ul className="mt-3 divide-y divide-slate-100">
          {rows.length === 0 ? (
            <li className="py-4 text-sm text-slate-600">Noch kein Board Report vorhanden.</li>
          ) : (
            rows.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-slate-900">{r.title}</p>
                  <p className="text-xs text-slate-500">
                    {r.period_key} · {new Date(r.generated_at_utc).toLocaleString("de-DE")}
                  </p>
                </div>
                <Link
                  href={`/tenant/governance/board-reports/${r.id}`}
                  className="text-sm font-semibold text-[var(--sbs-navy-mid)] no-underline hover:underline"
                >
                  Öffnen
                </Link>
              </li>
            ))
          )}
        </ul>
      </article>
    </div>
  );
}

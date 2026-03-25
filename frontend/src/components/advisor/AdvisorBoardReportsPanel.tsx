"use client";

import React, { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  fetchAdvisorBoardReportDetail,
  fetchAdvisorPortfolioBoardReports,
  type AdvisorBoardReportListRowDto,
  type AiComplianceBoardReportDetailDto,
} from "@/lib/api";
import { CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

const mdComponents = {
  h2: (props: React.ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mt-6 border-b border-slate-200 pb-1 text-sm font-bold text-slate-900" {...props} />
  ),
  p: (props: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mt-2 text-sm leading-relaxed text-slate-700" {...props} />
  ),
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-700" {...props} />
  ),
};

export function AdvisorBoardReportsPanel({ advisorId }: { advisorId: string }) {
  const [rows, setRows] = useState<AdvisorBoardReportListRowDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [detail, setDetail] = useState<AiComplianceBoardReportDetailDto | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await fetchAdvisorPortfolioBoardReports(advisorId);
      setRows(data.reports);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Laden fehlgeschlagen");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (r: AdvisorBoardReportListRowDto) => {
    setDetailBusy(true);
    try {
      const d = await fetchAdvisorBoardReportDetail(advisorId, r.tenant_id, r.report_id);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailBusy(false);
    }
  };

  return (
    <>
      <section className={CH_CARD} aria-label="Mandanten-Reports" data-testid="advisor-board-reports">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className={CH_SECTION_LABEL}>Mandanten-Reports</p>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              AI-Compliance-Board-Reports der verknüpften Mandanten (nur Metadaten in der Liste;
              Vorschau nach Klick).
            </p>
          </div>
          <button
            type="button"
            className={`${CH_BTN_SECONDARY} text-xs`}
            onClick={() => void load()}
            disabled={loading}
          >
            Aktualisieren
          </button>
        </div>

        {loading ? (
          <p className="mt-4 text-sm text-slate-500">Lade Reports…</p>
        ) : null}
        {err ? (
          <p className="mt-4 text-sm text-rose-700">{err}</p>
        ) : null}

        {!loading && !err && rows.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">Keine gespeicherten Reports.</p>
        ) : null}

        {rows.length > 0 ? (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-[720px] w-full border-collapse text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Mandant</th>
                  <th className="px-3 py-2">Report</th>
                  <th className="px-3 py-2">Zielgruppe</th>
                  <th className="px-3 py-2">Datum</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={`${r.tenant_id}-${r.report_id}`} className="border-b border-slate-100">
                    <td className="px-3 py-2 align-top">
                      <div className="font-medium text-slate-900">
                        {r.tenant_display_name || r.tenant_id}
                      </div>
                      <div className="font-mono text-xs text-slate-500">{r.tenant_id}</div>
                    </td>
                    <td className="px-3 py-2 align-top text-slate-800">{r.title}</td>
                    <td className="px-3 py-2 align-top text-xs text-slate-600">{r.audience_type}</td>
                    <td className="px-3 py-2 align-top text-xs text-slate-600">
                      {new Date(r.created_at).toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <button
                        type="button"
                        className={`${CH_BTN_SECONDARY} text-xs`}
                        onClick={() => void openDetail(r)}
                        disabled={detailBusy}
                      >
                        Vorschau
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {detail ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="adv-br-title"
        >
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
            <h2 id="adv-br-title" className="text-lg font-bold text-slate-900">
              {detail.title}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {detail.tenant_id} · {detail.audience_type} ·{" "}
              {new Date(detail.created_at).toLocaleString("de-DE")}
            </p>
            <div className="mt-4 max-h-[60vh] overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/50 p-4">
              <ReactMarkdown components={mdComponents}>{detail.rendered_markdown}</ReactMarkdown>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() => setDetail(null)}
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

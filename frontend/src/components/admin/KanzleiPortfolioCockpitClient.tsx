"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import { GTM_READINESS_CLASSES, GTM_READINESS_SHORT_DE } from "@/lib/gtmAccountReadiness";
import type {
  KanzleiPortfolioPayload,
  KanzleiPortfolioPillarFilter,
  KanzleiPortfolioReadinessFilter,
  KanzleiPortfolioRow,
} from "@/lib/kanzleiPortfolioTypes";

type Props = { adminConfigured: boolean };

function trafficPill(s: BoardReadinessTraffic): string {
  if (s === "green") return "border-emerald-300 bg-emerald-50 text-emerald-950";
  if (s === "amber") return "border-amber-300 bg-amber-50 text-amber-950";
  return "border-rose-300 bg-rose-50 text-rose-950";
}

function trafficLabel(s: BoardReadinessTraffic): string {
  if (s === "green") return "OK";
  if (s === "amber") return "Beobachten";
  return "Handeln";
}

const PILLAR_KEYS: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

const PILLAR_FILTER_LABELS: Record<BoardReadinessPillarKey, string> = {
  eu_ai_act: "EU AI Act",
  iso_42001: "ISO 42001",
  nis2: "NIS2",
  dsgvo: "DSGVO",
};

function topGapMatchesPillar(row: KanzleiPortfolioRow, pk: BoardReadinessPillarKey): boolean {
  const map: Record<string, BoardReadinessPillarKey> = {
    EU_AI_Act: "eu_ai_act",
    ISO_42001: "iso_42001",
    NIS2: "nis2",
    DSGVO: "dsgvo",
  };
  return map[row.top_gap_pillar_code] === pk;
}

function formatIsoDe(iso: string | null): string {
  if (!iso) return "—";
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return iso.slice(0, 10);
  return new Date(d).toLocaleDateString("de-DE");
}

export function KanzleiPortfolioCockpitClient({ adminConfigured }: Props) {
  const [payload, setPayload] = useState<KanzleiPortfolioPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [readinessFilter, setReadinessFilter] = useState<KanzleiPortfolioReadinessFilter>("all");
  const [pillarFilter, setPillarFilter] = useState<KanzleiPortfolioPillarFilter>("all");
  const [staleOnly, setStaleOnly] = useState(false);
  const [manyOpenOnly, setManyOpenOnly] = useState(false);
  const [reviewStaleOnly, setReviewStaleOnly] = useState(false);
  const [reviewBusyId, setReviewBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await fetch("/api/internal/advisor/kanzlei-portfolio", { credentials: "include" });
      if (r.status === 401) {
        setPayload(null);
        setLoadError("unauthorized");
        return;
      }
      if (!r.ok) {
        setLoadError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; kanzlei_portfolio?: KanzleiPortfolioPayload };
      setPayload(data.kanzlei_portfolio ?? null);
    } catch {
      setLoadError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!adminConfigured) return;
    void load();
  }, [adminConfigured, load]);

  const filteredRows = useMemo(() => {
    if (!payload) return [];
    const thr = payload.constants.many_open_points_threshold;
    return payload.rows.filter((row) => {
      if (readinessFilter !== "all" && row.readiness_class !== readinessFilter) return false;
      if (pillarFilter !== "all") {
        const st = row.pillar_traffic[pillarFilter];
        const gapMatch = topGapMatchesPillar(row, pillarFilter);
        if (st === "green" && !gapMatch) return false;
      }
      if (staleOnly && !row.board_report_stale) return false;
      if (manyOpenOnly && row.open_points_count < thr) return false;
      if (reviewStaleOnly && !row.review_stale) return false;
      return true;
    });
  }, [payload, readinessFilter, pillarFilter, staleOnly, manyOpenOnly, reviewStaleOnly]);

  const markReviewDone = useCallback(
    async (tenantId: string) => {
      const raw =
        typeof window !== "undefined"
          ? window.prompt(
              "Optional: kurze Notiz zum Review. Leer = nur Zeitstempel, Abbrechen = keine Aktion.",
              "",
            )
          : null;
      if (raw === null) return;
      setReviewBusyId(tenantId);
      try {
        const r = await fetch("/api/internal/advisor/mandant-review", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            client_id: tenantId,
            ...(raw.trim() ? { note_de: raw.trim() } : {}),
          }),
        });
        if (!r.ok) return;
        await load();
      } finally {
        setReviewBusyId(null);
      }
    },
    [load],
  );

  if (!adminConfigured) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        Kanzlei-Cockpit nicht konfiguriert (<code className="font-mono">LEAD_ADMIN_SECRET</code>).
      </div>
    );
  }

  if (loadError === "unauthorized") {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">Kanzlei-Portfolio</h1>
        <p className="mt-2 text-sm text-slate-600">
          Bitte zuerst unter{" "}
          <a className="text-cyan-700 underline" href="/admin/leads">
            Lead-Inbox
          </a>{" "}
          mit dem Admin-Secret anmelden, dann diese Seite neu laden.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Wave 39–40 · Kanzlei / Berater</p>
          <h1 className="text-2xl font-semibold text-slate-900">Mehrmandanten-Kanzlei-Cockpit</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Welcher Mandant braucht jetzt Aufmerksamkeit? Portfolio über gemappte Mandanten mit Readiness,
            offenen Prüfpunkten, Export-Historie (Readiness / DATEV-ZIP) und Review-Kadenz (Wave 40).
          </p>
          {payload ? (
            <p className="mt-1 font-mono text-xs text-slate-400">
              Stand: {new Date(payload.generated_at).toLocaleString("de-DE")} · Mandanten:{" "}
              {payload.mapped_tenant_count}
              {payload.tenants_partial ? ` · API teilweise: ${payload.tenants_partial}` : ""}
            </p>
          ) : null}
          <p className="mt-2 text-xs text-slate-500">
            API:{" "}
            <code className="rounded bg-slate-100 px-1 text-[11px]">
              GET /api/internal/advisor/kanzlei-portfolio
            </code>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href="/admin/advisor-mandant-export"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Mandanten-Export
          </a>
          <a
            href="/admin/board-readiness"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Board Readiness
          </a>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? "Laden…" : "Aktualisieren"}
          </button>
        </div>
      </div>

      {loadError && loadError !== "unauthorized" ? (
        <p className="text-sm text-red-600">{loadError}</p>
      ) : null}

      {payload ? (
        <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <label className="text-xs font-medium text-slate-700">
            Readiness-Klasse
            <select
              className="mt-1 block rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
              value={readinessFilter}
              onChange={(e) => setReadinessFilter(e.target.value as KanzleiPortfolioReadinessFilter)}
            >
              <option value="all">Alle</option>
              {GTM_READINESS_CLASSES.map((c) => (
                <option key={c} value={c}>
                  {GTM_READINESS_SHORT_DE[c]}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-medium text-slate-700">
            Säule (Lücke)
            <select
              className="mt-1 block rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
              value={pillarFilter}
              onChange={(e) => setPillarFilter(e.target.value as KanzleiPortfolioPillarFilter)}
            >
              <option value="all">Alle</option>
              {PILLAR_KEYS.map((k) => (
                <option key={k} value={k}>
                  {PILLAR_FILTER_LABELS[k]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={staleOnly} onChange={(e) => setStaleOnly(e.target.checked)} />
            Nur überfälliger Mandantenbericht
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={manyOpenOnly}
              onChange={(e) => setManyOpenOnly(e.target.checked)}
            />
            Viele offene Punkte (≥{payload.constants.many_open_points_threshold})
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={reviewStaleOnly}
              onChange={(e) => setReviewStaleOnly(e.target.checked)}
            />
            Review überfällig (&gt;{payload.constants.review_stale_days} Tage)
          </label>
          <p className="text-xs text-slate-500">
            Sortierung: Kanzlei-Aufmerksamkeit (Score) absteigend, wie vom Server geliefert.
          </p>
        </div>
      ) : null}

      {loading && !payload ? <p className="text-sm text-slate-500">Portfolio wird geladen …</p> : null}

      {payload ? (
        <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-[1100px] w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-3 py-2 font-medium">Mandant</th>
                <th className="px-3 py-2 font-medium">Readiness</th>
                <th className="px-3 py-2 font-medium">Fokus-Säule</th>
                <th className="px-3 py-2 font-medium">Bericht</th>
                <th className="px-3 py-2 font-medium">Offen</th>
                <th className="px-3 py-2 font-medium">Signale</th>
                <th className="px-3 py-2 font-medium">Readiness-Export</th>
                <th className="px-3 py-2 font-medium">DATEV-ZIP</th>
                <th className="px-3 py-2 font-medium">Review</th>
                <th className="px-3 py-2 font-medium">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-3 py-6 text-center text-slate-500">
                    Keine Mandanten für die aktuellen Filter.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.tenant_id} className="border-b border-slate-100 hover:bg-slate-50/80">
                    <td className="px-3 py-2 align-top">
                      <div className="font-medium text-slate-900">{row.mandant_label ?? row.tenant_id}</div>
                      <div className="font-mono text-[10px] text-slate-500">{row.tenant_id}</div>
                      {row.primary_segment_label_de ? (
                        <div className="mt-0.5 text-[10px] text-slate-500">{row.primary_segment_label_de}</div>
                      ) : null}
                      <div className="mt-1 flex flex-wrap gap-1">
                        {row.never_any_export ? (
                          <span className="rounded border border-amber-200 bg-amber-50 px-1 py-0.5 text-[9px] font-medium text-amber-900">
                            Kein Export
                          </span>
                        ) : null}
                        {row.review_stale ? (
                          <span className="rounded border border-violet-200 bg-violet-50 px-1 py-0.5 text-[9px] font-medium text-violet-900">
                            Review
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <span className="text-slate-800">{row.readiness_label_de}</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {PILLAR_KEYS.map((k) => (
                          <span
                            key={k}
                            title={PILLAR_FILTER_LABELS[k]}
                            className={`inline-block rounded border px-1 py-0.5 text-[9px] font-semibold ${trafficPill(row.pillar_traffic[k])}`}
                          >
                            {trafficLabel(row.pillar_traffic[k]).charAt(0)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top text-slate-800">{row.top_gap_pillar_label_de}</td>
                    <td className="px-3 py-2 align-top">
                      {row.board_report_stale ? (
                        <span className="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-900">
                          Überfällig
                        </span>
                      ) : (
                        <span className="text-slate-600">OK / n.a.</span>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top font-mono text-slate-800">
                      {row.open_points_count}
                      {row.open_points_hoch > 0 ? (
                        <span className="ml-1 text-rose-700">({row.open_points_hoch} hoch)</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 align-top text-[10px] text-slate-600">
                      <ul className="max-w-[200px] list-inside list-disc">
                        {row.attention_flags_de.slice(0, 3).map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                      <div className="mt-1 font-mono text-slate-400">Score {row.attention_score}</div>
                    </td>
                    <td className="px-3 py-2 align-top text-slate-700">
                      {formatIsoDe(row.last_mandant_readiness_export_at)}
                    </td>
                    <td className="px-3 py-2 align-top text-slate-700">
                      {formatIsoDe(row.last_datev_bundle_export_at)}
                    </td>
                    <td className="px-3 py-2 align-top text-slate-700">
                      <div>{formatIsoDe(row.last_review_marked_at)}</div>
                      {row.last_review_note_de ? (
                        <div className="mt-0.5 max-w-[140px] truncate text-[10px] text-slate-500" title={row.last_review_note_de}>
                          {row.last_review_note_de}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex flex-col gap-1">
                        <button
                          type="button"
                          disabled={reviewBusyId === row.tenant_id}
                          onClick={() => void markReviewDone(row.tenant_id)}
                          className="text-left text-[11px] text-violet-800 underline disabled:opacity-50"
                        >
                          {reviewBusyId === row.tenant_id ? "…" : "Review durchgeführt"}
                        </button>
                        <a
                          className="text-cyan-700 underline"
                          href={row.links.mandant_export_page}
                        >
                          Readiness-Export (UI)
                        </a>
                        <a className="text-cyan-700 underline" href={row.links.datev_bundle_api}>
                          ZIP-Bundle
                        </a>
                        <a className="text-cyan-700 underline" href={row.links.board_readiness_admin}>
                          Board Readiness
                        </a>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      ) : null}

      {payload ? (
        <p className="text-xs text-slate-500">
          Historie: <code className="rounded bg-slate-100 px-1">data/advisor-mandant-history.json</code> (Export-
          Zeitstempel automatisch; Review per Aktion). Optional weiterlesbar:{" "}
          <code className="rounded bg-slate-100 px-1">data/advisor-portfolio-touchpoints.json</code> (Wave 39
          Legacy). Schwellen: Review {payload.constants.review_stale_days} Tage, Export{" "}
          {payload.constants.any_export_max_age_days} Tage – siehe Wave 40.
        </p>
      ) : null}
    </div>
  );
}

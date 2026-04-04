"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { BoardReadinessBriefingPanel } from "@/components/admin/BoardReadinessBriefingPanel";
import { BoardQuarterlyPackPanel } from "@/components/admin/BoardQuarterlyPackPanel";
import type { BoardReadinessPayload, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

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

export function BoardReadinessClient({ adminConfigured }: Props) {
  const [payload, setPayload] = useState<BoardReadinessPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await fetch("/api/admin/board-readiness", { credentials: "include" });
      if (r.status === 401) {
        setPayload(null);
        setLoadError("unauthorized");
        return;
      }
      if (!r.ok) {
        setLoadError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; board_readiness?: BoardReadinessPayload };
      setPayload(data.board_readiness ?? null);
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

  const sortedAttention = useMemo(() => {
    const rank: Record<BoardReadinessTraffic, number> = { red: 0, amber: 1, green: 2 };
    return [...(payload?.attention_items ?? [])].sort((a, b) => rank[a.severity] - rank[b.severity]);
  }, [payload?.attention_items]);

  if (!adminConfigured) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        Board Readiness ist nicht konfiguriert (<code className="font-mono">LEAD_ADMIN_SECRET</code>).
      </div>
    );
  }

  if (loadError === "unauthorized") {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">Board Readiness</h1>
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
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Wave 34–36 · Intern</p>
          <h1 className="text-2xl font-semibold text-slate-900">Board Readiness</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Governance-Signale je Säule (EU AI Act, ISO 42001, NIS2, DSGVO) über gemappte Mandanten –
            anschlussfähig an GTM-Segmente und Wave-33-Readiness-Klassen.
          </p>
          {payload ? (
            <p className="mt-1 font-mono text-xs text-slate-400">
              Stand: {new Date(payload.generated_at).toLocaleString("de-DE")} · Backend:{" "}
              {payload.backend_reachable ? "erreichbar" : "teilweise nicht erreichbar"} · Mandanten (Map):{" "}
              {payload.mapped_tenant_count}
              {payload.tenants_partial ? ` · ohne vollständige API: ${payload.tenants_partial}` : ""}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href="/admin/gtm"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            GTM Command Center
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

      {loading && !payload ? <p className="text-sm text-slate-500">Daten werden geladen …</p> : null}

      <BoardQuarterlyPackPanel />
      <BoardReadinessBriefingPanel />

      {payload ? (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Portfolio-Ampel</h2>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium ${trafficPill(payload.overall.status)}`}
              >
                {trafficLabel(payload.overall.status)}
              </span>
              <p className="text-sm text-slate-700">{payload.overall.label_de}</p>
            </div>
            <ul className="mt-3 list-inside list-disc text-xs text-slate-600">
              {payload.notes_de.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            {payload.pillars.map((p) => (
              <div key={p.pillar} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">{p.title_de}</h3>
                    <p className="mt-1 text-xs text-slate-600">{p.summary_de}</p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${trafficPill(p.status)}`}
                  >
                    {trafficLabel(p.status)}
                  </span>
                </div>
                <ul className="mt-4 space-y-3">
                  {p.indicators.map((ind) => (
                    <li key={ind.key} className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs font-medium text-slate-800">{ind.label_de}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${trafficPill(ind.status)}`}
                        >
                          {trafficLabel(ind.status)}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[11px] text-slate-600">
                        {ind.value_percent !== null
                          ? `${ind.value_percent}%`
                          : "—"}
                        {ind.value_count !== null && ind.value_denominator !== null
                          ? ` · ${ind.value_count}/${ind.value_denominator}`
                          : ""}
                      </p>
                      {ind.source_api_paths.length ? (
                        <p className="mt-1 text-[10px] text-slate-500">
                          Quellen: {ind.source_api_paths.join(", ")}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Segment × Governance (gemappte Mandanten)</h2>
            <p className="mt-1 text-xs text-slate-600">
              Nachfrage-Spalten aus GTM (30 Tage); Ampeln aus Mandanten, die diesem Segment über dominante Leads
              zugeordnet sind.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-medium">Segment</th>
                    <th className="py-2 pr-3 font-medium">Anfragen 30d</th>
                    <th className="py-2 pr-3 font-medium">Qualifiziert</th>
                    <th className="py-2 pr-3 font-medium">Mandanten</th>
                    <th className="py-2 pr-3 font-medium">EU AI Act</th>
                    <th className="py-2 pr-3 font-medium">ISO 42001</th>
                    <th className="py-2 pr-3 font-medium">NIS2</th>
                    <th className="py-2 pr-3 font-medium">DSGVO</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.segment_rollups.map((r) => (
                    <tr key={r.segment} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-800">{r.label_de}</td>
                      <td className="py-2 pr-3 font-mono text-slate-700">{r.inquiries_30d}</td>
                      <td className="py-2 pr-3 font-mono text-slate-700">{r.qualified_30d}</td>
                      <td className="py-2 pr-3 font-mono text-slate-700">{r.mapped_tenant_count}</td>
                      {(["eu_ai_act", "iso_42001", "nis2", "dsgvo"] as const).map((k) => (
                        <td key={k} className="py-2 pr-3">
                          <span
                            className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${trafficPill(r.pillar_status[k])}`}
                          >
                            {trafficLabel(r.pillar_status[k])}
                          </span>
                          {r.pillar_score_proxy[k] !== null ? (
                            <span className="ml-1 font-mono text-[10px] text-slate-500">
                              {Math.round(r.pillar_score_proxy[k] as number)}%
                            </span>
                          ) : null}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Readiness-Klasse (Wave 33)</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-medium">Klasse</th>
                    <th className="py-2 pr-3 font-medium">Mandanten</th>
                    <th className="py-2 pr-3 font-medium">EU AI Act</th>
                    <th className="py-2 pr-3 font-medium">ISO 42001</th>
                    <th className="py-2 pr-3 font-medium">NIS2</th>
                    <th className="py-2 pr-3 font-medium">DSGVO</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.readiness_class_rollups.map((r) => (
                    <tr key={r.readiness_class} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-800">{r.label_de}</td>
                      <td className="py-2 pr-3 font-mono text-slate-700">{r.tenant_count}</td>
                      {(["eu_ai_act", "iso_42001", "nis2", "dsgvo"] as const).map((k) => (
                        <td key={k} className="py-2 pr-3">
                          <span
                            className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${trafficPill(r.pillar_status[k])}`}
                          >
                            {trafficLabel(r.pillar_status[k])}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {payload.gtm_demand_strip ? (
            <section className="rounded-xl border border-cyan-200 bg-cyan-50/40 p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">GTM-Nachfrage vs. dominante Readiness</h2>
              <p className="mt-1 text-xs text-slate-600">
                Kompakte Wave-33-Sicht (gleiche Fensterlogik wie /admin/gtm).
              </p>
              <ul className="mt-3 space-y-2 text-xs text-slate-800">
                {payload.gtm_demand_strip.segment_rows.map((s) => (
                  <li key={s.segment}>
                    <span className="font-medium">{s.label_de}</span>
                    <span className="ml-2 font-mono text-slate-600">
                      {s.inquiries_30d} Anfragen · {s.qualified_30d} qualifiziert · dominant:{" "}
                      {s.dominant_readiness}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Board Attention Items</h2>
            <p className="mt-1 text-xs text-slate-600">
              Konkrete Lücken mit Deep-Links (Workspace-Pfade und API-Pfade für Audit).
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-2 font-medium">Ampel</th>
                    <th className="py-2 pr-2 font-medium">Mandant</th>
                    <th className="py-2 pr-2 font-medium">System / Ebene</th>
                    <th className="py-2 pr-2 font-medium">Fehlend</th>
                    <th className="py-2 pr-2 font-medium">Segment</th>
                    <th className="py-2 pr-2 font-medium">Letzte Änderung</th>
                    <th className="py-2 pr-2 font-medium">Links</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAttention.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-2">
                        <span
                          className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${trafficPill(a.severity)}`}
                        >
                          {trafficLabel(a.severity)}
                        </span>
                      </td>
                      <td className="py-2 pr-2 text-slate-800">
                        {a.tenant_label ?? a.tenant_id}
                        <div className="font-mono text-[10px] text-slate-500">{a.tenant_id}</div>
                      </td>
                      <td className="py-2 pr-2 text-slate-700">
                        {a.subject_type === "ai_system" ? (
                          <>
                            KI-System
                            <div className="font-mono text-[10px] text-slate-500">{a.subject_id}</div>
                            {a.subject_name ? <div>{a.subject_name}</div> : null}
                          </>
                        ) : (
                          <>Mandant / Portfolio</>
                        )}
                      </td>
                      <td className="py-2 pr-2 text-slate-800">{a.missing_artefact_de}</td>
                      <td className="py-2 pr-2 text-slate-600">{a.segment_tag ?? "—"}</td>
                      <td className="py-2 pr-2 font-mono text-[10px] text-slate-600">
                        {a.last_change_at
                          ? new Date(a.last_change_at).toLocaleString("de-DE")
                          : "—"}
                      </td>
                      <td className="py-2 pr-2 text-[10px]">
                        {Object.entries(a.deep_links).map(([k, v]) => (
                          <div key={k} className="text-cyan-800">
                            <span className="text-slate-500">{k}: </span>
                            <code className="break-all">{v}</code>
                          </div>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <p className="text-center text-[11px] text-slate-500">
            Dokumentation:{" "}
            <code className="rounded bg-slate-200/80 px-1">docs/board/wave34-board-readiness-dashboard.md</code>
          </p>
        </>
      ) : null}
    </div>
  );
}

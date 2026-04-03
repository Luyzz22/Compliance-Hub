"use client";

import { useCallback, useEffect, useState } from "react";

import type { GtmDashboardSnapshot, GtmWindowKey } from "@/lib/gtmDashboardTypes";

type Props = { adminConfigured: boolean };

function KpiCard({
  title,
  v7,
  v30,
  sub,
}: {
  title: string;
  v7: number;
  v30: number;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2 flex flex-wrap items-baseline gap-3">
        <div>
          <span className="text-2xl font-semibold text-slate-900">{v7}</span>
          <span className="ml-1 text-xs text-slate-500">7 Tage</span>
        </div>
        <div className="text-slate-300">|</div>
        <div>
          <span className="text-xl font-semibold text-slate-700">{v30}</span>
          <span className="ml-1 text-xs text-slate-500">30 Tage</span>
        </div>
      </div>
      {sub ? <p className="mt-1 text-xs text-slate-500">{sub}</p> : null}
    </div>
  );
}

function attentionLabel(kind: string): string {
  if (kind === "failed_webhook") return "Webhook fehlgeschlagen";
  if (kind === "dead_letter_sync") return "Sync Dead Letter";
  if (kind === "unresolved_repeat_contact") return "Wiederholung ohne Triage";
  if (kind === "crm_sync_failed") return "CRM-Sync fehlgeschlagen";
  return kind;
}

export function GtmCommandCenterClient({ adminConfigured }: Props) {
  const [snapshot, setSnapshot] = useState<GtmDashboardSnapshot | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await fetch("/api/admin/gtm/summary", { credentials: "include" });
      if (r.status === 401) {
        setSnapshot(null);
        setLoadError("unauthorized");
        return;
      }
      if (!r.ok) {
        setLoadError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; snapshot?: GtmDashboardSnapshot };
      setSnapshot(data.snapshot ?? null);
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

  const k = (w: GtmWindowKey) => snapshot?.kpis[w];

  const maxDaily =
    snapshot?.trends.inquiries_per_day_utc.reduce((m, d) => Math.max(m, d.inquiries), 0) ?? 1;

  if (!adminConfigured) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        GTM Command Center ist nicht konfiguriert (<code className="font-mono">LEAD_ADMIN_SECRET</code>
        ).
      </div>
    );
  }

  if (loadError === "unauthorized") {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">GTM Command Center</h1>
        <p className="mt-2 text-sm text-slate-600">
          Bitte zuerst unter{" "}
          <a className="text-cyan-700 underline" href="/admin/leads">
            Lead-Inbox
          </a>{" "}
          mit dem Admin-Secret anmelden (Session-Cookie), dann diese Seite neu laden.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">GTM Command Center</h1>
          <p className="mt-1 text-sm text-slate-600">
            Operative Kennzahlen aus Lead-Store, Triage und Sync-Jobs — kein BI-Tool.
          </p>
          {snapshot ? (
            <p className="mt-1 font-mono text-xs text-slate-400">
              Stand: {new Date(snapshot.generated_at).toLocaleString("de-DE")}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href="/admin/leads"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Lead-Inbox
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

      {loading && !snapshot ? (
        <p className="text-sm text-slate-500">Daten werden geladen …</p>
      ) : null}

      {snapshot ? (
        <>
          <section>
            <h2 className="mb-3 text-sm font-semibold text-slate-800">Kern-KPIs</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <KpiCard
                title="Inbound-Anfragen"
                v7={k("7d")!.inbound_inquiries}
                v30={k("30d")!.inbound_inquiries}
              />
              <KpiCard
                title="Wiederholte Kontakte (Anfragen)"
                v7={k("7d")!.repeated_contact_inquiries}
                v30={k("30d")!.repeated_contact_inquiries}
                sub="Mehrfach-Einreichungen gleiche E-Mail"
              />
              <KpiCard
                title="Qualifiziert"
                v7={k("7d")!.qualified_leads}
                v30={k("30d")!.qualified_leads}
                sub="Triage qualifiziert / Abschluss-Interesse"
              />
              <KpiCard
                title="Kontaktiert (Triage)"
                v7={k("7d")!.contacted_leads}
                v30={k("30d")!.contacted_leads}
                sub="Exakt Status „kontaktiert“"
              />
              <KpiCard
                title="Webhook-Weiterleitung fehlgeschlagen"
                v7={k("7d")!.failed_webhook_forwards}
                v30={k("30d")!.failed_webhook_forwards}
              />
              <KpiCard
                title="Sync Dead Letters"
                v7={k("7d")!.dead_letter_sync_jobs}
                v30={k("30d")!.dead_letter_sync_jobs}
                sub="Alle Ziele, Zeit nach letztem Job-Update"
              />
              <KpiCard
                title="HubSpot erfolgreich (Jobs)"
                v7={k("7d")!.hubspot_synced_jobs}
                v30={k("30d")!.hubspot_synced_jobs}
                sub="Ziel hubspot, Status gesendet"
              />
              <KpiCard
                title="Pipedrive Deals neu"
                v7={k("7d")!.pipedrive_deals_created}
                v30={k("30d")!.pipedrive_deals_created}
                sub="Sync: deal_action created"
              />
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-800">Segmente (30 Tage)</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-2">Segment</th>
                    <th className="py-2 pr-2">Anfragen</th>
                    <th className="py-2 pr-2">Qualifiziert</th>
                    <th className="py-2">CRM-Sync-Probleme</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.segment_table.map((row) => (
                    <tr key={row.segment} className="border-b border-slate-100">
                      <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                      <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                      <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                      <td className="py-2 font-mono text-amber-800">{row.sync_issues_30d}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Sync-Probleme: fehlgeschlagen oder Dead Letter bei HubSpot/Pipedrive (letztes Update im
              30-Tage-Fenster).
            </p>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-800">Trichter (absolute Zahlen)</h2>
            <p className="mt-1 text-xs text-slate-500">{snapshot.data_notes.funnel_note_de}</p>
            <p className="mt-2 text-xs text-amber-800">{snapshot.data_notes.cta_note_de}</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[480px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-2 text-left">Stufe</th>
                    <th className="py-2 pr-2">7 Tage</th>
                    <th className="py-2">30 Tage</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.funnel.map((row) => (
                    <tr key={row.id} className="border-b border-slate-100">
                      <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                      <td className="py-2 pr-2 font-mono text-slate-700">{row.counts["7d"]}</td>
                      <td className="py-2 font-mono text-slate-700">{row.counts["30d"]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-amber-50/80 p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-amber-950">Aufmerksamkeit</h2>
            <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-xs">
              {snapshot.attention.length === 0 ? (
                <li className="text-slate-600">Keine priorisierten Einträge.</li>
              ) : (
                snapshot.attention.map((a, i) => (
                  <li
                    key={`${a.kind}-${a.lead_id ?? a.job_id}-${i}`}
                    className="rounded border border-amber-200/80 bg-white px-2 py-1.5 text-slate-800"
                  >
                    <span className="font-medium text-amber-900">{attentionLabel(a.kind)}</span>
                    {a.lead_id ? (
                      <>
                        {" "}
                        ·{" "}
                        <a
                          className="font-mono text-cyan-800 underline"
                          href={`/admin/leads?focus=${encodeURIComponent(a.lead_id)}`}
                        >
                          {a.lead_id.slice(0, 8)}…
                        </a>
                      </>
                    ) : null}
                    {a.target ? <span className="text-slate-500"> · {a.target}</span> : null}
                    {a.detail ? <span className="block text-slate-600">{a.detail}</span> : null}
                    <span className="text-slate-400">
                      {a.at ? new Date(a.at).toLocaleString("de-DE") : ""}
                    </span>
                  </li>
                ))
              )}
            </ul>
            <p className="mt-2 text-xs text-slate-600">
              Links mit <code className="font-mono">focus</code> dienen als Orientierung — in der
              Inbox die passende UUID auswählen.
            </p>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-800">Anfragen pro Tag (UTC)</h2>
              <p className="text-xs text-slate-500">Letzte 14 Tage, Einreichungsdatum</p>
              <div className="mt-4 flex h-32 items-end gap-0.5">
                {snapshot.trends.inquiries_per_day_utc.map((d) => {
                  const h = maxDaily > 0 ? Math.max(4, (d.inquiries / maxDaily) * 100) : 4;
                  return (
                    <div
                      key={d.day}
                      className="min-w-0 flex-1 rounded-t bg-slate-700"
                      style={{ height: `${h}%` }}
                      title={`${d.day}: ${d.inquiries}`}
                    />
                  );
                })}
              </div>
              <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-400">
                <span>{snapshot.trends.inquiries_per_day_utc[0]?.day}</span>
                <span>{snapshot.trends.inquiries_per_day_utc.at(-1)?.day}</span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-800">Wochen-Trend (UTC)</h2>
              <p className="text-xs text-slate-500">
                Qualifiziert nach Einreichungswoche; Pipedrive-Deals nach Sync-Zeitpunkt
              </p>
              <div className="mt-3 max-h-40 overflow-auto text-xs">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-1 text-left">Woche ab</th>
                      <th className="py-1 text-right">Qual.</th>
                      <th className="py-1 text-right">PD neu</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.trends.qualified_and_deals_per_week_utc.map((w) => (
                      <tr key={w.week_start} className="border-b border-slate-100">
                        <td className="py-1 font-mono text-slate-700">{w.week_start}</td>
                        <td className="py-1 text-right font-mono">{w.qualified}</td>
                        <td className="py-1 text-right font-mono">{w.pipedrive_deals_created}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

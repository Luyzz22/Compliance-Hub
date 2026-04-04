"use client";

import { useCallback, useEffect, useState } from "react";

import { GTM_READINESS_LABELS_DE, GTM_READINESS_SHORT_DE } from "@/lib/gtmAccountReadiness";
import type {
  GtmDashboardSnapshot,
  GtmHealthStatus,
  GtmWeeklyReviewNote,
  GtmWindowKey,
} from "@/lib/gtmDashboardTypes";
import type { BoardReadinessBanner } from "@/lib/boardReadinessTypes";
import type { GtmProductBridgePayload } from "@/lib/gtmProductBridgeTypes";

type Props = { adminConfigured: boolean };

function healthStatusClass(s: GtmHealthStatus): string {
  if (s === "good") return "border-emerald-200 bg-emerald-50/90 text-emerald-950";
  if (s === "watch") return "border-amber-200 bg-amber-50/90 text-amber-950";
  return "border-rose-200 bg-rose-50/90 text-rose-950";
}

function healthStatusLabel(s: GtmHealthStatus): string {
  if (s === "good") return "OK";
  if (s === "watch") return "Beobachten";
  return "Handeln";
}

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

function readinessPillClass(cls: string): string {
  if (cls === "no_footprint") return "border-slate-200 bg-slate-50 text-slate-800";
  if (cls === "early_pilot") return "border-amber-200 bg-amber-50 text-amber-950";
  if (cls === "baseline_governance") return "border-cyan-200 bg-cyan-50 text-cyan-950";
  return "border-emerald-200 bg-emerald-50 text-emerald-950";
}

function attentionLabel(kind: string): string {
  if (kind === "failed_webhook") return "Webhook fehlgeschlagen";
  if (kind === "dead_letter_sync") return "Sync Dead Letter";
  if (kind === "unresolved_repeat_contact") return "Wiederholung ohne Triage";
  if (kind === "crm_sync_failed") return "CRM-Sync fehlgeschlagen";
  return kind;
}

type WeeklyReviewPayload = {
  last_reviewed_at: string | null;
  recent_notes: GtmWeeklyReviewNote[];
};

export function GtmCommandCenterClient({ adminConfigured }: Props) {
  const [snapshot, setSnapshot] = useState<GtmDashboardSnapshot | null>(null);
  const [productBridge, setProductBridge] = useState<GtmProductBridgePayload | null>(null);
  const [weeklyReview, setWeeklyReview] = useState<WeeklyReviewPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [weeklyNoteDraft, setWeeklyNoteDraft] = useState("");
  const [weeklySaving, setWeeklySaving] = useState(false);
  const [weeklyMsg, setWeeklyMsg] = useState<string | null>(null);
  const [boardReadinessBanner, setBoardReadinessBanner] = useState<BoardReadinessBanner | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await fetch("/api/admin/gtm/summary", { credentials: "include" });
      if (r.status === 401) {
        setSnapshot(null);
        setProductBridge(null);
        setWeeklyReview(null);
        setBoardReadinessBanner(null);
        setLoadError("unauthorized");
        return;
      }
      if (!r.ok) {
        setLoadError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as {
        ok?: boolean;
        snapshot?: GtmDashboardSnapshot;
        weekly_review?: WeeklyReviewPayload;
        product_bridge?: GtmProductBridgePayload;
        board_readiness_banner?: BoardReadinessBanner;
      };
      setSnapshot(data.snapshot ?? null);
      setProductBridge(data.product_bridge ?? null);
      setBoardReadinessBanner(data.board_readiness_banner ?? null);
      setWeeklyReview(
        data.weekly_review ?? { last_reviewed_at: null, recent_notes: [] },
      );
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

  async function submitWeeklyReview(mode: "mark_only" | "note_only" | "mark_with_note") {
    setWeeklySaving(true);
    setWeeklyMsg(null);
    try {
      let body: { mark_reviewed?: boolean; note?: string };
      if (mode === "mark_only") body = { mark_reviewed: true };
      else if (mode === "note_only") {
        if (!weeklyNoteDraft.trim()) {
          setWeeklyMsg("Bitte Notiztext eingeben.");
          setWeeklySaving(false);
          return;
        }
        body = { note: weeklyNoteDraft.trim().slice(0, 2000) };
      } else {
        if (!weeklyNoteDraft.trim()) {
          setWeeklyMsg("Bitte Notiztext eingeben oder „nur abhaken“ nutzen.");
          setWeeklySaving(false);
          return;
        }
        body = { mark_reviewed: true, note: weeklyNoteDraft.trim().slice(0, 2000) };
      }
      const r = await fetch("/api/admin/gtm/weekly-review", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        setWeeklyMsg(`Speichern fehlgeschlagen (${r.status})`);
        return;
      }
      setWeeklyMsg("Gespeichert.");
      setWeeklyNoteDraft("");
      await load();
    } catch {
      setWeeklyMsg("Netzwerkfehler beim Speichern.");
    } finally {
      setWeeklySaving(false);
    }
  }

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

      {boardReadinessBanner ? (
        <a
          href="/admin/board-readiness"
          className={`block rounded-xl border p-4 shadow-sm transition hover:opacity-95 ${
            boardReadinessBanner.status === "green"
              ? "border-emerald-200 bg-emerald-50/90"
              : boardReadinessBanner.status === "amber"
                ? "border-amber-200 bg-amber-50/90"
                : "border-rose-200 bg-rose-50/90"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Board Readiness</h2>
            <span className="rounded-full border border-slate-300 bg-white/80 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-800">
              {boardReadinessBanner.status === "green"
                ? "OK"
                : boardReadinessBanner.status === "amber"
                  ? "Beobachten"
                  : "Handeln"}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-700">{boardReadinessBanner.label_de}</p>
          <p className="mt-2 font-mono text-[10px] text-slate-600">
            Mandanten (Map): {boardReadinessBanner.mapped_tenant_count} · Backend:{" "}
            {boardReadinessBanner.backend_reachable ? "OK" : "teilweise offline"}
          </p>
          <p className="mt-2 text-xs font-medium text-cyan-900 underline underline-offset-2">
            Details anzeigen →
          </p>
        </a>
      ) : null}

      {snapshot ? (
        <>
          <section id="gtm-health" className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">GTM Health</h2>
            <p className="mt-1 text-xs text-slate-600">{snapshot.data_notes.health_note_de}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {snapshot.health.tiles.map((t) => (
                <div
                  key={t.id}
                  className={`rounded-lg border p-3 text-sm ${healthStatusClass(t.status)}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{t.label_de}</span>
                    <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide opacity-90">
                      {healthStatusLabel(t.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed opacity-95">{t.explanation_de}</p>
                  <a
                    href={t.href}
                    className="mt-2 inline-block text-xs font-medium text-cyan-900 underline underline-offset-2"
                  >
                    {t.link_label_de} →
                  </a>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Wöchentlicher GTM-Review (15–20 Min.)</h2>
            <p className="mt-1 text-xs text-slate-600">
              Leichte Routine für Founders &amp; GTM — vollständige Checkliste und Alert-Hinweise im Repo:{" "}
              <code className="rounded bg-slate-100 px-1 font-mono text-[11px]">
                docs/gtm/wave32-weekly-gtm-health-review.md
              </code>
            </p>
            <ul className="mt-3 list-inside list-disc space-y-1 text-xs text-slate-700">
              <li>GTM Health-Kacheln (Eingang, Triage, Sync, Pipeline)</li>
              <li>Aufmerksamkeit &amp; operative Hinweise (Backlog, Sync, Pipeline-Proxy)</li>
              <li>Segment-Readiness (Mittelstand, Kanzlei, Enterprise) → Fokus setzen</li>
              <li>Attribution &amp; Noise-Top-Quellen</li>
              <li>2–3 konkrete Aktionen für die kommende Woche festhalten</li>
            </ul>
            <div className="mt-4 border-t border-slate-100 pt-4">
              <p className="text-xs font-medium text-slate-600">
                Zuletzt reviewt:{" "}
                {weeklyReview?.last_reviewed_at
                  ? new Date(weeklyReview.last_reviewed_at).toLocaleString("de-DE")
                  : "noch nicht erfasst"}
              </p>
              {weeklyReview?.recent_notes?.length ? (
                <div className="mt-2 space-y-2">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                    Letzte Notizen
                  </p>
                  {weeklyReview.recent_notes.map((n) => (
                    <div
                      key={n.id}
                      className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-xs text-slate-800"
                    >
                      <p className="font-mono text-[10px] text-slate-500">
                        {n.week_label} · {new Date(n.created_at).toLocaleDateString("de-DE")}
                      </p>
                      <p className="mt-1 whitespace-pre-wrap">{n.text}</p>
                    </div>
                  ))}
                </div>
              ) : null}
              <label className="mt-3 block text-xs font-medium text-slate-600" htmlFor="gtm-weekly-note">
                Optionale Wochen-Notiz (intern)
              </label>
              <textarea
                id="gtm-weekly-note"
                value={weeklyNoteDraft}
                onChange={(e) => setWeeklyNoteDraft(e.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="z. B. Fokus: Kanzlei-Demos; Sync stabil; CTA X testen"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={weeklySaving}
                  onClick={() => void submitWeeklyReview("mark_only")}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  Review heute abhaken
                </button>
                <button
                  type="button"
                  disabled={weeklySaving || !weeklyNoteDraft.trim()}
                  onClick={() => void submitWeeklyReview("note_only")}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 hover:bg-slate-50 disabled:opacity-50"
                >
                  Nur Notiz anhängen
                </button>
                <button
                  type="button"
                  disabled={weeklySaving || !weeklyNoteDraft.trim()}
                  onClick={() => void submitWeeklyReview("mark_with_note")}
                  className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-950 hover:bg-emerald-100 disabled:opacity-50"
                >
                  Abhaken + Notiz
                </button>
              </div>
              {weeklyMsg ? <p className="mt-2 text-xs text-slate-600">{weeklyMsg}</p> : null}
            </div>
          </section>

          {snapshot.health.ops_hints.length > 0 ? (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-800">Operative Hinweise (SLA‑Stil)</h2>
              <p className="mt-1 text-xs text-slate-500">
                Orientierung für den Alltag — keine verbindlichen SLAs, keine Personenbewertung.
              </p>
              <ul className="mt-3 space-y-2 text-sm text-slate-800">
                {snapshot.health.ops_hints.map((h) => (
                  <li key={h.id} className="flex flex-wrap items-baseline gap-2">
                    <span className="font-mono text-xs text-slate-500">×{h.count}</span>
                    <span>{h.message_de}</span>
                    <a href={h.href} className="text-xs text-cyan-800 underline">
                      Öffnen
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

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

          <section
            id="gtm-segment-readiness"
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <h2 className="text-sm font-semibold text-slate-800">Segment-Readiness (30 Tage)</h2>
            <p className="mt-1 text-xs text-slate-500">
              Volumen, Qualifikation, CRM-Touches (gesendete Jobs) und dominante Attributions-Quellen.
              Sync-Probleme: fehlgeschlagen oder Dead Letter (letztes Update im Fenster).
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-2">Segment</th>
                    <th className="py-2 pr-2">Anfr.</th>
                    <th className="py-2 pr-2">Qual.</th>
                    <th className="py-2 pr-2">HubSpot OK</th>
                    <th className="py-2 pr-2">PD Touch</th>
                    <th className="py-2 pr-2">Sync-Issues</th>
                    <th className="py-2 pr-2">Top-Quellen</th>
                    <th className="py-2 pr-2">Status</th>
                    <th className="py-2">Hinweis</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.health.segment_readiness.map((row) => {
                    const syncRow = snapshot.segment_table.find((s) => s.segment === row.segment);
                    return (
                      <tr key={row.segment} className="border-b border-slate-100">
                        <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                        <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                        <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                        <td className="py-2 pr-2 font-mono text-slate-700">{row.hubspot_sent_30d}</td>
                        <td className="py-2 pr-2 font-mono text-slate-700">
                          {row.pipedrive_touch_30d}
                        </td>
                        <td className="py-2 pr-2 font-mono text-amber-800">
                          {syncRow?.sync_issues_30d ?? 0}
                        </td>
                        <td className="max-w-[200px] py-2 pr-2 text-xs text-slate-600">
                          {row.dominant_sources_de}
                        </td>
                        <td className="py-2 pr-2">
                          <span
                            className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase ${healthStatusClass(row.status)}`}
                          >
                            {healthStatusLabel(row.status)}
                          </span>
                        </td>
                        <td className="max-w-[220px] py-2 text-xs text-slate-600">{row.note_de}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {productBridge ? (
            <section
              id="gtm-product-readiness-overlay"
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <h2 className="text-sm font-semibold text-slate-800">Product Readiness Overlay (Wave 33)</h2>
              <p className="mt-1 text-xs text-slate-500">
                GTM-Segmente (30 Tage) plus grobe Produkt-/Governance-Readiness aus Mapping + Mandanten-API.
                Doku:{" "}
                <code className="rounded bg-slate-100 px-1 font-mono text-[11px]">
                  docs/gtm/wave33-product-gtm-bridge.md
                </code>
              </p>
              <p className="mt-2 text-xs text-slate-600">
                Mapping: {productBridge.map_entry_count} Einträge · {productBridge.mapped_tenant_count}{" "}
                Mandanten · Backend:{" "}
                {productBridge.backend_reachable ? (
                  <span className="text-emerald-800">erreichbar</span>
                ) : (
                  <span className="text-amber-800">nicht bestätigt</span>
                )}{" "}
                · {productBridge.note_de}
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500">
                      <th className="py-2 pr-2">Segment</th>
                      <th className="py-2 pr-2">Anfr.</th>
                      <th className="py-2 pr-2">Qual.</th>
                      <th className="py-2 pr-2">PD neu</th>
                      <th className="py-2 pr-2">Readiness-Schwerpunkt</th>
                      <th className="py-2">Verteilung</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productBridge.segment_overlay.map((row) => (
                      <tr key={row.segment} className="border-b border-slate-100">
                        <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                        <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                        <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                        <td className="py-2 pr-2 font-mono">{row.pipedrive_deals_created_30d}</td>
                        <td className="py-2 pr-2">
                          <span
                            className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold ${readinessPillClass(row.dominant_readiness)}`}
                          >
                            {GTM_READINESS_LABELS_DE[row.dominant_readiness]}
                          </span>
                        </td>
                        <td className="max-w-[280px] py-2 text-[11px] text-slate-600">
                          {productBridge.matrix.rows.map((rc) => (
                            <span key={rc} className="mr-2 inline-block whitespace-nowrap">
                              <span className="font-mono text-slate-800">{row.readiness_breakdown[rc]}</span>{" "}
                              {GTM_READINESS_SHORT_DE[rc]}
                            </span>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {productBridge ? (
            <section
              id="gtm-readiness-matrix"
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <h2 className="text-sm font-semibold text-slate-800">GTM × Readiness-Matrix (Anfragen 30 Tage)</h2>
              <p className="mt-1 text-xs text-slate-500">
                Zeilen: Readiness-Klassen. Spalten: Segmente. Zellen: Anzahl Anfragen im Fenster.
              </p>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500">
                      <th className="py-2 pr-2">Readiness</th>
                      {productBridge.matrix.columns.map((col) => (
                        <th key={col} className="py-2 pr-2 text-right">
                          {productBridge.matrix.column_labels_de[col]}
                        </th>
                      ))}
                      <th className="py-2 text-right">Σ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productBridge.matrix.rows.map((rc) => (
                      <tr key={rc} className="border-b border-slate-100">
                        <td className="py-2 pr-2 text-xs text-slate-800">{GTM_READINESS_LABELS_DE[rc]}</td>
                        {productBridge.matrix.columns.map((col) => (
                          <td key={col} className="py-2 pr-2 text-right font-mono">
                            {productBridge.matrix.cells[rc][col]}
                          </td>
                        ))}
                        <td className="py-2 text-right font-mono text-slate-700">
                          {productBridge.matrix.row_totals[rc]}
                        </td>
                      </tr>
                    ))}
                    <tr className="border-t border-slate-200 text-xs font-medium text-slate-700">
                      <td className="py-2 pr-2">Σ</td>
                      {productBridge.matrix.columns.map((col) => (
                        <td key={col} className="py-2 pr-2 text-right font-mono">
                          {productBridge.matrix.column_totals[col]}
                        </td>
                      ))}
                      <td className="py-2 text-right font-mono">
                        {productBridge.matrix.rows.reduce((s, rc) => s + productBridge.matrix.row_totals[rc], 0)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-800">Attribution (30 Tage)</h2>
            <p className="mt-1 text-xs text-slate-500">{snapshot.data_notes.attribution_note_de}</p>
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Nach Quelle (heuristisch)
                </h3>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full min-w-[320px] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2 pr-2">Quelle</th>
                        <th className="py-2 pr-2">Anfr.</th>
                        <th className="py-2 pr-2">Qual.</th>
                        <th className="py-2">PD neu</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.attribution_by_source_30d.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-3 text-xs text-slate-500">
                            Keine Daten im Fenster.
                          </td>
                        </tr>
                      ) : (
                        snapshot.attribution_by_source_30d.map((row) => (
                          <tr key={row.key} className="border-b border-slate-100">
                            <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                            <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                            <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                            <td className="py-2 font-mono text-slate-700">
                              {row.pipedrive_deals_created_30d}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div>
                <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Nach Campaign (utm_campaign)
                </h3>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full min-w-[320px] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2 pr-2">Campaign</th>
                        <th className="py-2 pr-2">Anfr.</th>
                        <th className="py-2 pr-2">Qual.</th>
                        <th className="py-2">PD neu</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.attribution_by_campaign_30d.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-3 text-xs text-slate-500">
                            Keine Daten im Fenster.
                          </td>
                        </tr>
                      ) : (
                        snapshot.attribution_by_campaign_30d.map((row) => (
                          <tr key={row.key} className="border-b border-slate-100">
                            <td className="py-2 pr-2 font-mono text-slate-800">{row.label_de}</td>
                            <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                            <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                            <td className="py-2 font-mono text-slate-700">
                              {row.pipedrive_deals_created_30d}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>

          <section
            id="gtm-attribution-health"
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <h2 className="text-sm font-semibold text-slate-800">Attribution &amp; Signalqualität (Top 3)</h2>
            <p className="mt-1 text-xs text-slate-500">
              Stärkste Quellen nach Volumen; „Noise“ = viele Leads, sehr wenig Qualifikation
              (heuristisch, kein Bot-Nachweis).
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[480px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-2">Quelle</th>
                    <th className="py-2 pr-2">Leads</th>
                    <th className="py-2 pr-2">Qual.</th>
                    <th className="py-2 pr-2">Deals</th>
                    <th className="py-2 pr-2">Qual.-Quote</th>
                    <th className="py-2">Hinweis</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.health.attribution_health_top3.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-3 text-xs text-slate-500">
                        Keine Daten.
                      </td>
                    </tr>
                  ) : (
                    snapshot.health.attribution_health_top3.map((row) => (
                      <tr key={row.key} className="border-b border-slate-100">
                        <td className="py-2 pr-2 text-slate-800">{row.label_de}</td>
                        <td className="py-2 pr-2 font-mono">{row.inquiries_30d}</td>
                        <td className="py-2 pr-2 font-mono">{row.qualified_30d}</td>
                        <td className="py-2 pr-2 font-mono">{row.pipedrive_deals_created_30d}</td>
                        <td className="py-2 pr-2 font-mono text-slate-600">
                          {row.inquiries_30d > 0
                            ? `${Math.round(row.qual_ratio * 100)}%`
                            : "—"}
                        </td>
                        <td className="py-2 text-xs">
                          {row.noise_suspected ? (
                            <span className="text-amber-800">Viel Volumen, wenig Qual. prüfen</span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
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

          <section id="gtm-attention" className="rounded-xl border border-slate-200 bg-amber-50/80 p-4 shadow-sm">
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

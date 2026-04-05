"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  KanzleiReviewPlaybookHelper,
  type KanzleiPlaybookMandateSnapshot,
} from "@/components/admin/KanzleiReviewPlaybookHelper";
import {
  MANDANT_REMINDER_CATEGORY_LABEL_DE,
  type MandantReminderRecord,
} from "@/lib/advisorMandantReminderTypes";
import type { MandantReadinessAdvisorPayload } from "@/lib/mandantReadinessAdvisorTypes";
import { naechsterSchrittForRow } from "@/lib/kanzleiAttentionQueue";
import type { AdvisorMandantHistoryApiDto, KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_MANY_OPEN_POINTS } from "@/lib/kanzleiPortfolioScoring";
import { daysSinceValidIso, isNonEmptyUnparsableIso } from "@/lib/mandantHistoryMerge";

type Props = { adminConfigured: boolean };

function advisorExportHistSignalDe(h: AdvisorMandantHistoryApiDto): string {
  const exportMalformed =
    isNonEmptyUnparsableIso(h.last_mandant_readiness_export_at) ||
    isNonEmptyUnparsableIso(h.last_datev_bundle_export_at);
  if (h.never_any_export && !exportMalformed) return "Noch kein Export erfasst";
  if (exportMalformed) return "Export-Zeitstempel ungültig (Historie prüfen)";
  if (h.any_export_stale) return `Export älter als ${h.constants.any_export_max_age_days} Tage`;
  return "Export im Zeitraum OK";
}

function advisorReviewHistSignalDe(h: AdvisorMandantHistoryApiDto): string {
  if (isNonEmptyUnparsableIso(h.last_review_marked_at)) {
    return "Review-Zeitstempel ungültig (Historie prüfen)";
  }
  if (h.review_stale) return `Review überfällig (>${h.constants.review_stale_days} Tage oder nie)`;
  return "Review im Zeitraum OK";
}

function buildExportPagePlaybookSnapshot(
  row: KanzleiPortfolioRow | null,
  history: AdvisorMandantHistoryApiDto | null,
  nowMs: number,
): KanzleiPlaybookMandateSnapshot | null {
  if (row) {
    return {
      open_points_count: row.open_points_count,
      open_points_hoch: row.open_points_hoch,
      export_days_since: daysSinceValidIso(row.last_any_export_at, nowMs),
      review_stale: row.review_stale,
      any_export_stale: row.any_export_stale,
      never_any_export: row.never_any_export,
      board_report_stale: row.board_report_stale,
      top_gap_pillar_label_de: row.top_gap_pillar_label_de,
      api_fetch_ok: row.api_fetch_ok,
    };
  }
  if (history) {
    return {
      export_days_since: daysSinceValidIso(history.last_any_export_at, nowMs),
      review_stale: history.review_stale,
      any_export_stale: history.any_export_stale,
      never_any_export: history.never_any_export,
    };
  }
  return null;
}

export function AdvisorMandantExportClient({ adminConfigured }: Props) {
  const [clientId, setClientId] = useState("");
  const [payload, setPayload] = useState<MandantReadinessAdvisorPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [bundleLoading, setBundleLoading] = useState(false);
  const [history, setHistory] = useState<AdvisorMandantHistoryApiDto | null>(null);
  const [histLoading, setHistLoading] = useState(false);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [portfolioRow, setPortfolioRow] = useState<KanzleiPortfolioRow | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [tenantReminders, setTenantReminders] = useState<MandantReminderRecord[]>([]);
  const [remLoading, setRemLoading] = useState(false);
  const [remPatchId, setRemPatchId] = useState<string | null>(null);
  const [newRemDue, setNewRemDue] = useState("");
  const [newRemCat, setNewRemCat] = useState<"manual" | "follow_up_note">("follow_up_note");
  const [newRemNote, setNewRemNote] = useState("");
  const [newRemBusy, setNewRemBusy] = useState(false);

  const fetchTenantReminders = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setTenantReminders([]);
      return;
    }
    setRemLoading(true);
    try {
      const q = new URLSearchParams({ client_id: id, status: "open" });
      const r = await fetch(`/api/internal/advisor/mandant-reminders?${q}`, { credentials: "include" });
      if (!r.ok) {
        setTenantReminders([]);
        return;
      }
      const data = (await r.json()) as { reminders?: MandantReminderRecord[] };
      setTenantReminders(data.reminders ?? []);
    } catch {
      setTenantReminders([]);
    } finally {
      setRemLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    void fetchTenantReminders();
  }, [fetchTenantReminders]);

  useEffect(() => {
    if (!clientId.trim()) return;
    setNewRemDue((prev) => {
      if (prev) return prev;
      const d = new Date();
      d.setDate(d.getDate() + 7);
      return d.toISOString().slice(0, 10);
    });
  }, [clientId]);

  const fetchPortfolioRow = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setPortfolioRow(null);
      return;
    }
    setPortfolioLoading(true);
    try {
      const r = await fetch("/api/internal/advisor/kanzlei-portfolio", { credentials: "include" });
      if (!r.ok) {
        setPortfolioRow(null);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; kanzlei_portfolio?: KanzleiPortfolioPayload };
      const rows = data.kanzlei_portfolio?.rows ?? [];
      setPortfolioRow(rows.find((x) => x.tenant_id === id) ?? null);
    } catch {
      setPortfolioRow(null);
    } finally {
      setPortfolioLoading(false);
    }
  }, [clientId]);

  const fetchHistory = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setHistory(null);
      return;
    }
    setHistLoading(true);
    try {
      const q = new URLSearchParams({ client_id: id });
      const r = await fetch(`/api/internal/advisor/mandant-history?${q}`, { credentials: "include" });
      if (!r.ok) {
        setHistory(null);
        return;
      }
      const data = (await r.json()) as { mandant_history?: AdvisorMandantHistoryApiDto };
      setHistory(data.mandant_history ?? null);
    } catch {
      setHistory(null);
    } finally {
      setHistLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const c = new URLSearchParams(window.location.search).get("client_id")?.trim();
    if (c) setClientId(c);
  }, []);

  useEffect(() => {
    void fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    void fetchPortfolioRow();
  }, [fetchPortfolioRow]);

  const playbookSnapshot = useMemo(
    () => buildExportPagePlaybookSnapshot(portfolioRow, history, Date.now()),
    [portfolioRow, history],
  );

  const load = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setError("Bitte Mandanten-ID (client_id) eingeben.");
      return;
    }
    setLoading(true);
    setError(null);
    setMsg(null);
    try {
      const q = new URLSearchParams({ client_id: id });
      const r = await fetch(`/api/internal/advisor/mandant-readiness-export?${q}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        setPayload(null);
        return;
      }
      if (r.status === 400) {
        const j = (await r.json()) as { detail?: string };
        setError(j.detail ?? "Ungültige Mandanten-ID.");
        setPayload(null);
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        setPayload(null);
        return;
      }
      const data = (await r.json()) as {
        ok?: boolean;
        mandant_readiness_export?: MandantReadinessAdvisorPayload;
      };
      setPayload(data.mandant_readiness_export ?? null);
      void fetchHistory();
      void fetchPortfolioRow();
      void fetchTenantReminders();
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, [clientId, fetchHistory, fetchPortfolioRow, fetchTenantReminders]);

  const copyMd = useCallback(async () => {
    if (!payload?.markdown_de) return;
    try {
      await navigator.clipboard.writeText(payload.markdown_de);
      setMsg("Markdown kopiert.");
    } catch {
      setMsg("Kopieren fehlgeschlagen.");
    }
  }, [payload?.markdown_de]);

  const downloadMd = useCallback(() => {
    if (!payload?.markdown_de) return;
    const blob = new Blob([payload.markdown_de], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mandant-readiness-${payload.kompakt.mandant_id}-${payload.meta.generated_at.slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [payload]);

  const downloadDatevBundle = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setError("Bitte Mandanten-ID (client_id) eingeben.");
      return;
    }
    setBundleLoading(true);
    setError(null);
    setMsg(null);
    try {
      const q = new URLSearchParams({ client_id: id });
      const r = await fetch(`/api/internal/advisor/datev-export-bundle?${q}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        return;
      }
      if (r.status === 400) {
        const j = (await r.json()) as { detail?: string };
        setError(j.detail ?? "Ungültige Mandanten-ID.");
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const blob = await r.blob();
      const cd = r.headers.get("Content-Disposition");
      const match = cd?.match(/filename="([^"]+)"/);
      const name = match?.[1] ?? `datev-kanzlei-bundle-${id}.zip`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
      setMsg("ZIP-Arbeitspaket geladen.");
      void fetchHistory();
      void fetchPortfolioRow();
      void fetchTenantReminders();
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setBundleLoading(false);
    }
  }, [clientId, fetchHistory, fetchPortfolioRow, fetchTenantReminders]);

  const submitReview = useCallback(async () => {
    const id = clientId.trim();
    if (!id) {
      setError("Bitte Mandanten-ID (client_id) eingeben.");
      return;
    }
    setReviewBusy(true);
    setError(null);
    setMsg(null);
    try {
      const body: { client_id: string; note_de?: string } = { client_id: id };
      const n = reviewNote.trim();
      if (n) body.note_de = n.slice(0, 500);
      const r = await fetch("/api/internal/advisor/mandant-review", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.status === 401) {
        setError("Nicht angemeldet (Admin-Secret).");
        return;
      }
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as { mandant_history?: AdvisorMandantHistoryApiDto };
      setHistory(data.mandant_history ?? null);
      setReviewNote("");
      setMsg("Review gespeichert.");
      void fetchPortfolioRow();
      void fetchTenantReminders();
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setReviewBusy(false);
    }
  }, [clientId, reviewNote, fetchPortfolioRow, fetchTenantReminders]);

  const patchTenantReminder = useCallback(
    async (reminderId: string, status: "done" | "dismissed") => {
      setRemPatchId(reminderId);
      try {
        const r = await fetch("/api/internal/advisor/mandant-reminders", {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reminder_id: reminderId, status }),
        });
        if (r.ok) void fetchTenantReminders();
      } finally {
        setRemPatchId(null);
      }
    },
    [fetchTenantReminders],
  );

  const submitNewReminder = useCallback(async () => {
    const id = clientId.trim();
    if (!id || !newRemDue.trim()) return;
    setNewRemBusy(true);
    try {
      const r = await fetch("/api/internal/advisor/mandant-reminders", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: id,
          category: newRemCat,
          due_at: newRemDue.trim(),
          ...(newRemNote.trim() ? { note: newRemNote.trim() } : {}),
        }),
      });
      if (r.ok) {
        setNewRemNote("");
        void fetchTenantReminders();
        setMsg("Reminder gespeichert.");
      } else {
        const j = (await r.json()) as { detail?: string };
        setError(j.detail ?? `Reminder HTTP ${r.status}`);
      }
    } catch {
      setError("Netzwerkfehler");
    } finally {
      setNewRemBusy(false);
    }
  }, [clientId, fetchTenantReminders, newRemCat, newRemDue, newRemNote]);

  function formatHist(iso: string | null): string {
    if (!iso) return "—";
    const d = Date.parse(iso);
    if (Number.isNaN(d)) return iso.slice(0, 10);
    return new Date(d).toLocaleString("de-DE");
  }

  if (!adminConfigured) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        Nicht konfiguriert (<code className="font-mono">LEAD_ADMIN_SECRET</code>).
      </div>
    );
  }

  return (
    <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Wave 37–43 · Kanzlei / Berater</p>
        <h1 className="text-xl font-semibold text-slate-900">Mandanten-Readiness-Export</h1>
        <p className="mt-2 text-sm text-slate-600">
          Kompakter Status für Steuerberater, WP und GRC-Berater – ein Mandant pro Export. Nutzt dieselben
          API-Signale wie das Board-Readiness-Dashboard, aber mandantenzentriert und ohne Board-Pack-Ton.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          API:{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET /api/internal/advisor/mandant-readiness-export?client_id=…
          </code>
          <br />
          ZIP (Wave 38):{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET /api/internal/advisor/datev-export-bundle?client_id=…
          </code>
          <br />
          Historie / Review (Wave 40):{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET /api/internal/advisor/mandant-history
          </code>{" "}
          ·{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            POST /api/internal/advisor/mandant-review
          </code>
          <br />
          Reminders (Wave 43):{" "}
          <code className="rounded bg-slate-100 px-1 text-[11px]">
            GET/POST/PATCH /api/internal/advisor/mandant-reminders
          </code>
        </p>
      </div>

      <KanzleiReviewPlaybookHelper
        variant={clientId.trim() ? "full" : "compact"}
        snapshot={clientId.trim() ? playbookSnapshot : null}
        footerHint={
          clientId.trim()
            ? portfolioLoading
              ? "Portfolio-Zeile für dynamische Kennzahlen wird geladen …"
              : portfolioRow
                ? null
                : "Keine Portfolio-Zeile für diese ID – Kennzahlen nur aus Historie, falls geladen."
            : "Mandanten-ID eintragen für dynamische Kennzahlen; vollständige Queue siehe Kanzlei-Cockpit."
        }
      />
      {clientId.trim() && portfolioRow ? (
        <p className="rounded-lg border border-violet-100 bg-violet-50/60 px-3 py-2 text-xs text-violet-950">
          <span className="font-semibold">Nächster Schritt (Queue-Regel):</span>{" "}
          {naechsterSchrittForRow(portfolioRow, KANZLEI_MANY_OPEN_POINTS)}
        </p>
      ) : null}

      {clientId.trim() ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-xs text-slate-700">
          <p className="font-semibold text-slate-900">Kanzlei-Historie (Export und Review)</p>
          {histLoading ? (
            <p className="mt-1 text-slate-500">Lade Historie…</p>
          ) : history ? (
            <ul className="mt-2 list-inside list-disc space-y-0.5">
              <li>Letzter Readiness-Export: {formatHist(history.last_mandant_readiness_export_at)}</li>
              <li>Letzter DATEV-/ZIP-Export: {formatHist(history.last_datev_bundle_export_at)}</li>
              <li>Letzter Review: {formatHist(history.last_review_marked_at)}</li>
              {history.last_review_note_de ? (
                <li className="text-slate-600">Notiz: {history.last_review_note_de}</li>
              ) : null}
              <li>
                Signale: {advisorExportHistSignalDe(history)} · {advisorReviewHistSignalDe(history)}
              </li>
            </ul>
          ) : (
            <p className="mt-1 text-slate-500">Historie nicht geladen.</p>
          )}
          <div className="mt-2 flex flex-wrap items-end gap-2">
            <label className="block min-w-[200px] flex-1 text-[11px] font-medium text-slate-600">
              Optional: Notiz zum Review
              <input
                className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                placeholder="Kurz für die Kanzlei-Dokumentation"
                maxLength={500}
              />
            </label>
            <button
              type="button"
              disabled={reviewBusy}
              onClick={() => void submitReview()}
              className="rounded-lg bg-violet-900 px-3 py-1.5 text-xs text-white hover:bg-violet-800 disabled:opacity-50"
            >
              {reviewBusy ? "Speichere…" : "Review durchgeführt"}
            </button>
          </div>
        </div>
      ) : null}

      {clientId.trim() ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50/40 p-3 text-xs text-slate-800">
          <p className="font-semibold text-rose-950">Offene Reminders (Wave 43)</p>
          {remLoading ? (
            <p className="mt-1 text-slate-500">Lade Reminder…</p>
          ) : tenantReminders.length === 0 ? (
            <p className="mt-1 text-slate-600">Keine offenen Reminder für diesen Mandanten.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {tenantReminders.map((r) => (
                <li key={r.reminder_id} className="rounded border border-rose-100 bg-white/90 p-2">
                  <div className="font-medium">{MANDANT_REMINDER_CATEGORY_LABEL_DE[r.category]}</div>
                  <div className="text-slate-600">Fällig: {formatHist(r.due_at)}</div>
                  {r.note ? <div className="mt-0.5 text-slate-700">{r.note}</div> : null}
                  <div className="mt-1 flex gap-2">
                    <button
                      type="button"
                      disabled={remPatchId === r.reminder_id}
                      onClick={() => void patchTenantReminder(r.reminder_id, "done")}
                      className="text-cyan-800 underline disabled:opacity-50"
                    >
                      Erledigt
                    </button>
                    <button
                      type="button"
                      disabled={remPatchId === r.reminder_id}
                      onClick={() => void patchTenantReminder(r.reminder_id, "dismissed")}
                      className="text-slate-600 underline disabled:opacity-50"
                    >
                      Zurückstellen
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-rose-100 pt-2">
            <label className="text-[11px] font-medium text-slate-700">
              Neu · Fällig
              <input
                type="date"
                className="mt-0.5 block rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                value={newRemDue}
                onChange={(e) => setNewRemDue(e.target.value)}
              />
            </label>
            <label className="text-[11px] font-medium text-slate-700">
              Art
              <select
                className="mt-0.5 block rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                value={newRemCat}
                onChange={(e) => setNewRemCat(e.target.value as "manual" | "follow_up_note")}
              >
                <option value="follow_up_note">Follow-up</option>
                <option value="manual">Manuell</option>
              </select>
            </label>
            <label className="min-w-[160px] flex-1 text-[11px] font-medium text-slate-700">
              Notiz
              <input
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-[11px]"
                value={newRemNote}
                onChange={(e) => setNewRemNote(e.target.value)}
                placeholder="Kurztext"
                maxLength={500}
              />
            </label>
            <button
              type="button"
              disabled={newRemBusy || !newRemDue.trim()}
              onClick={() => void submitNewReminder()}
              className="rounded bg-rose-800 px-2 py-1 text-[11px] text-white hover:bg-rose-900 disabled:opacity-50"
            >
              {newRemBusy ? "…" : "Reminder anlegen"}
            </button>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-end gap-2">
        <label className="block text-xs font-medium text-slate-700" htmlFor="mandant-id">
          Mandanten-ID (client_id)
        </label>
        <input
          id="mandant-id"
          className="min-w-[240px] flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm"
          placeholder="z. B. tenant-acme-001"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
        />
        <button
          type="button"
          disabled={loading}
          onClick={() => void load()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? "Lade…" : "Export erzeugen"}
        </button>
        <button
          type="button"
          disabled={bundleLoading}
          onClick={() => void downloadDatevBundle()}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-900 hover:bg-slate-50 disabled:opacity-50"
        >
          {bundleLoading ? "ZIP…" : "DATEV-/Kanzlei-Export erstellen"}
        </button>
      </div>

      <p className="text-xs text-slate-500">
        <a className="text-cyan-700 underline" href="/admin/advisor-portfolio">
          Kanzlei-Cockpit
        </a>
        {" · "}
        <a className="text-cyan-700 underline" href="/admin/board-readiness">
          Board Readiness
        </a>
      </p>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {msg ? <p className="text-sm text-emerald-800">{msg}</p> : null}

      {payload ? (
        <div className="space-y-4 border-t border-slate-100 pt-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">1. Mandantenstatus</h2>
            <p className="mt-1 text-sm text-slate-800">{payload.kompakt.readiness_kurzfassung_de}</p>
            <ul className="mt-2 list-inside list-disc text-xs text-slate-700">
              <li>Bezeichnung: {payload.kompakt.mandanten_bezeichnung}</li>
              <li>KI-Systeme: {payload.kompakt.ki_systeme_gesamt} · Hochrisiko: {payload.kompakt.ki_hochrisiko_anzahl}</li>
              <li>Reife-Orientierung: {payload.kompakt.governance_reifeklasse_de}</li>
              <li>Ansprechpartner: {payload.kompakt.ansprechpartner_hinweis_de}</li>
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">2. Offene Prüfpunkte</h2>
            <ul className="mt-2 space-y-1 text-xs text-slate-800">
              {payload.offene_punkte.length ? (
                payload.offene_punkte.map((o) => (
                  <li key={o.referenz_id + o.pruefpunkt_de.slice(0, 20)}>
                    <span className="font-mono text-violet-800">{o.referenz_id}</span> · {o.pruefpunkt_de}
                  </li>
                ))
              ) : (
                <li>Keine automatisch erkannten offenen Punkte.</li>
              )}
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">3. Nächste Schritte</h2>
            <ul className="mt-2 list-inside list-disc text-xs text-slate-800">
              {payload.naechste_schritte.map((s, i) => (
                <li key={i}>
                  <strong>{s.fuer}:</strong> {s.schritt_de}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void copyMd()}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800"
            >
              Markdown kopieren
            </button>
            <button
              type="button"
              onClick={() => downloadMd()}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800"
            >
              .md laden
            </button>
          </div>
          <textarea
            readOnly
            className="h-56 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-2 font-mono text-[11px]"
            value={payload.markdown_de}
            aria-label="Mandanten-Readiness Markdown"
          />
        </div>
      ) : null}
    </div>
  );
}

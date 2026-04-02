"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { LEAD_SEGMENTS } from "@/lib/leadCapture";
import type { LeadContactHistoryEntry, LeadInboxItem } from "@/lib/leadInboxTypes";
import type { LeadSyncJobApi } from "@/lib/leadSyncTypes";
import { LEAD_TRIAGE_LABELS_DE, LEAD_TRIAGE_STATUSES } from "@/lib/leadTriage";

type Props = {
  /** Wenn gesetzt, zeigt die UI einen Hinweis (kein Secret im Client-Build). */
  adminConfigured: boolean;
};

function forwardingLabel(s: LeadInboxItem["forwarding_status"]): string {
  if (s === "ok") return "Weitergeleitet";
  if (s === "failed") return "Weiterleitung fehlgeschlagen";
  return "Kein Webhook / nicht gesendet";
}

const DUPLICATE_REVIEW_LABELS: Record<LeadInboxItem["duplicate_review"], string> = {
  none: "Keine Markierung",
  suggested: "Zur Prüfung (mögliche Dublette)",
  confirmed: "Zusammenhang bestätigt (manuell)",
};

const SYNC_TARGET_LABELS: Record<LeadSyncJobApi["target"], string> = {
  n8n_webhook: "n8n (Webhook)",
  hubspot: "HubSpot",
  hubspot_stub: "HubSpot (Stub)",
  pipedrive_stub: "Pipedrive (Stub)",
};

const HUBSPOT_COMPANY_ASSOC_DE: Record<string, string> = {
  linked: "Firma verknüpft",
  skipped_no_match: "Firma: kein exakter Treffer (Anlegen nicht aktiv)",
  skipped_ambiguous: "Firma: mehrere Treffer, Zuordnung übersprungen",
  skipped_weak_name: "Firma: Name zu kurz oder Platzhalter",
  skipped_create_disabled: "Firma: Anlegen deaktiviert",
};

/** Client-sichere Auswertung von `mock_result` (kein server-only Import). */
function hubspotMockDetails(mock: unknown): {
  contact_id: string;
  company_id?: string;
  note_id?: string;
  note_action: string;
  company_association: string;
  synced_at?: string;
} | null {
  if (!mock || typeof mock !== "object") return null;
  const m = mock as Record<string, unknown>;
  if (m.system !== "hubspot" || typeof m.contact_id !== "string") return null;
  return {
    contact_id: m.contact_id,
    company_id: typeof m.company_id === "string" ? m.company_id : undefined,
    note_id: typeof m.note_id === "string" ? m.note_id : undefined,
    note_action: typeof m.note_action === "string" ? m.note_action : "—",
    company_association:
      typeof m.company_association === "string" ? m.company_association : "—",
    synced_at: typeof m.synced_at === "string" ? m.synced_at : undefined,
  };
}

function syncStatusLabel(s: LeadSyncJobApi["status"]): string {
  if (s === "pending") return "Ausstehend";
  if (s === "retrying") return "Wiederholung";
  if (s === "sent") return "Gesendet";
  if (s === "failed") return "Fehlgeschlagen";
  return "Dead Letter";
}

type PatchBody = {
  triage_status?: string;
  owner?: string;
  internal_note?: string;
  manual_related_lead_ids?: string[];
  duplicate_review?: LeadInboxItem["duplicate_review"];
};

export function AdminLeadInboxClient({ adminConfigured }: Props) {
  const [secretInput, setSecretInput] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [items, setItems] = useState<LeadInboxItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailItem, setDetailItem] = useState<LeadInboxItem | null>(null);
  const [contactHistory, setContactHistory] = useState<LeadContactHistoryEntry[]>([]);
  const [syncJobs, setSyncJobs] = useState<LeadSyncJobApi[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncRetryingId, setSyncRetryingId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    triage_status: "",
    segment: "",
    source_page: "",
    forwarding_status: "",
    repeated_contacts: false,
    unresolved_repeated: false,
  });
  const [draftOwner, setDraftOwner] = useState("");
  const [draftNote, setDraftNote] = useState("");
  const [draftDuplicateReview, setDraftDuplicateReview] =
    useState<LeadInboxItem["duplicate_review"]>("none");
  const [draftRelatedRaw, setDraftRelatedRaw] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const selected = useMemo(
    () => items.find((i) => i.lead_id === selectedId) ?? null,
    [items, selectedId],
  );

  const displayLead = detailItem ?? selected;

  useEffect(() => {
    if (!displayLead) {
      setDraftOwner("");
      setDraftNote("");
      setDraftDuplicateReview("none");
      setDraftRelatedRaw("");
      return;
    }
    setDraftOwner(displayLead.owner);
    setDraftNote(displayLead.internal_note);
    setDraftDuplicateReview(displayLead.duplicate_review);
    setDraftRelatedRaw(displayLead.manual_related_lead_ids.join(", "));
  }, [displayLead]);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (filters.triage_status) p.set("triage_status", filters.triage_status);
    if (filters.segment) p.set("segment", filters.segment);
    if (filters.source_page) p.set("source_page", filters.source_page);
    if (filters.forwarding_status) p.set("forwarding_status", filters.forwarding_status);
    if (filters.repeated_contacts) p.set("repeated_contacts", "1");
    if (filters.unresolved_repeated) p.set("unresolved_repeated", "1");
    p.set("limit", "500");
    return `?${p.toString()}`;
  }, [filters]);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const r = await fetch(`/api/admin/lead-inquiries${queryString}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setAuthed(false);
        setItems([]);
        return;
      }
      if (!r.ok) {
        setAuthed(true);
        setLoadError(`Laden fehlgeschlagen (${r.status})`);
        return;
      }
      const data = (await r.json()) as { ok?: boolean; items?: LeadInboxItem[] };
      setAuthed(true);
      setItems(data.items ?? []);
    } catch {
      setAuthed(true);
      setLoadError("Netzwerkfehler");
    } finally {
      setLoading(false);
    }
  }, [queryString]);

  useEffect(() => {
    if (!adminConfigured) return;
    void fetchLeads();
  }, [adminConfigured, fetchLeads]);

  useEffect(() => {
    if (!selectedId || authed !== true) {
      setDetailItem(null);
      setContactHistory([]);
      setSyncJobs([]);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    void fetch(`/api/admin/lead-inquiries/${selectedId}`, { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) return null;
        return (await r.json()) as {
          item?: LeadInboxItem;
          contact_history?: LeadContactHistoryEntry[];
          sync_jobs?: LeadSyncJobApi[];
        };
      })
      .then((data) => {
        if (cancelled || !data) return;
        if (data.item) setDetailItem(data.item);
        if (data.contact_history) setContactHistory(data.contact_history);
        setSyncJobs(Array.isArray(data.sync_jobs) ? data.sync_jobs : []);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, authed]);

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    try {
      const r = await fetch("/api/admin/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ secret: secretInput }),
      });
      if (!r.ok) {
        setLoginError("Zugang verweigert oder Secret ungültig.");
        return;
      }
      setSecretInput("");
      setAuthed(true);
      await fetchLeads();
    } catch {
      setLoginError("Anmeldung fehlgeschlagen.");
    }
  }

  async function logout() {
    try {
      await fetch("/api/admin/session", { method: "DELETE", credentials: "include" });
    } catch {
      /* ignore */
    }
    setAuthed(false);
    setItems([]);
    setSelectedId(null);
    setDetailItem(null);
    setContactHistory([]);
    setSyncJobs([]);
  }

  function parseRelatedIds(raw: string): string[] {
    return raw
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 20);
  }

  async function patchLead(leadId: string, body: PatchBody) {
    setSaving(true);
    setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/lead-inquiries/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const data = (await r.json()) as {
        ok?: boolean;
        item?: LeadInboxItem | null;
        contact_history?: LeadContactHistoryEntry[];
      };
      if (!r.ok) {
        setActionMsg("Speichern fehlgeschlagen.");
        return;
      }
      if (data.item) {
        setItems((prev) => prev.map((x) => (x.lead_id === data.item!.lead_id ? data.item! : x)));
        if (selectedId === leadId) setDetailItem(data.item);
      } else {
        await fetchLeads();
      }
      if (data.contact_history && selectedId === leadId) {
        setContactHistory(data.contact_history);
      }
      setActionMsg("Gespeichert.");
    } catch {
      setActionMsg("Netzwerkfehler beim Speichern.");
    } finally {
      setSaving(false);
    }
  }

  async function retryLeadSyncJob(leadId: string, jobId: string) {
    setSyncRetryingId(jobId);
    setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/lead-inquiries/${leadId}/sync-retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ job_id: jobId }),
      });
      const data = (await r.json()) as { ok?: boolean; job?: LeadSyncJobApi | null };
      if (!r.ok) {
        setActionMsg("Sync-Retry fehlgeschlagen.");
        return;
      }
      if (data.job) {
        setSyncJobs((prev) => {
          const rest = prev.filter((j) => j.job_id !== data.job!.job_id);
          return [...rest, data.job!].sort((a, b) => a.target.localeCompare(b.target));
        });
      }
      const detailR = await fetch(`/api/admin/lead-inquiries/${leadId}`, { credentials: "include" });
      if (detailR.ok) {
        const d = (await detailR.json()) as { item?: LeadInboxItem; sync_jobs?: LeadSyncJobApi[] };
        if (d.item && selectedId === leadId) setDetailItem(d.item);
        if (Array.isArray(d.sync_jobs) && selectedId === leadId) setSyncJobs(d.sync_jobs);
      }
      setActionMsg("Sync-Job erneut ausgeführt.");
    } catch {
      setActionMsg("Netzwerkfehler beim Sync-Retry.");
    } finally {
      setSyncRetryingId(null);
    }
  }

  async function retryWebhook(leadId: string) {
    setSaving(true);
    setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/lead-inquiries/${leadId}/retry-webhook`, {
        method: "POST",
        credentials: "include",
      });
      const data = (await r.json()) as {
        ok?: boolean;
        webhook_ok?: boolean;
        webhook_error?: string;
        item?: LeadInboxItem | null;
        error?: string;
      };
      if (r.status === 400 && data.error === "webhook_not_configured") {
        setActionMsg("Webhook-URL ist nicht konfiguriert.");
        return;
      }
      if (!r.ok) {
        setActionMsg("Retry fehlgeschlagen.");
        return;
      }
      if (data.item) {
        setItems((prev) => prev.map((x) => (x.lead_id === data.item!.lead_id ? data.item! : x)));
        if (selectedId === leadId) setDetailItem(data.item);
      }
      setActionMsg(
        data.webhook_ok ? "Webhook erneut erfolgreich." : `Webhook-Fehler: ${data.webhook_error ?? "?"}`,
      );
    } catch {
      setActionMsg("Netzwerkfehler beim Retry.");
    } finally {
      setSaving(false);
    }
  }

  if (!adminConfigured) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        <p className="font-medium">Lead-Inbox nicht verfügbar</p>
        <p className="mt-2 text-amber-800">
          <code className="rounded bg-amber-100 px-1 font-mono text-xs">LEAD_ADMIN_SECRET</code> ist auf
          dieser Umgebung nicht gesetzt. Die interne Ansicht bleibt absichtlich deaktiviert.
        </p>
      </div>
    );
  }

  if (authed === null || (loading && items.length === 0 && authed !== false)) {
    return (
      <div className="py-16 text-center text-sm text-slate-600">Session wird geprüft …</div>
    );
  }

  if (authed === false) {
    return (
      <div className="mx-auto max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">Internes Lead-Postfach</h1>
        <p className="mt-2 text-sm text-slate-600">
          Anmeldung mit dem konfigurierten Admin-Secret (wie Bearer für die API). Session-Cookie, httpOnly.
        </p>
        <form className="mt-6 space-y-4" onSubmit={login}>
          <label className="block text-sm font-medium text-slate-700">
            Admin-Secret
            <input
              type="password"
              autoComplete="off"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={secretInput}
              onChange={(e) => setSecretInput(e.target.value)}
            />
          </label>
          {loginError ? <p className="text-sm text-red-600">{loginError}</p> : null}
          <button
            type="submit"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Anmelden
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Lead-Inbox</h1>
          <p className="text-sm text-slate-600">
            Triage und Nachverfolgung – nicht öffentlich, kein CRM. Kontakt-Historie gruppiert nach
            E-Mail-Schlüssel; jede Einreichung bleibt eigener Datensatz. Sortierung: zuerst
            Aufmerksamkeit, dann neueste zuerst.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Abmelden
        </button>
      </div>

      <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Triage</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
            value={filters.triage_status}
            onChange={(e) => setFilters((f) => ({ ...f, triage_status: e.target.value }))}
          >
            <option value="">Alle</option>
            {LEAD_TRIAGE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {LEAD_TRIAGE_LABELS_DE[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Segment</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
            value={filters.segment}
            onChange={(e) => setFilters((f) => ({ ...f, segment: e.target.value }))}
          >
            <option value="">Alle</option>
            {LEAD_SEGMENTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Quelle (enthält)</span>
          <input
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
            value={filters.source_page}
            onChange={(e) => setFilters((f) => ({ ...f, source_page: e.target.value }))}
            placeholder="z. B. kontakt"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-600">Weiterleitung</span>
          <select
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
            value={filters.forwarding_status}
            onChange={(e) => setFilters((f) => ({ ...f, forwarding_status: e.target.value }))}
          >
            <option value="">Alle</option>
            <option value="ok">OK</option>
            <option value="failed">Fehlgeschlagen</option>
            <option value="not_sent">Nicht gesendet</option>
          </select>
        </label>
        <label className="flex items-center gap-2 self-end pb-1">
          <input
            type="checkbox"
            checked={filters.repeated_contacts}
            onChange={(e) => setFilters((f) => ({ ...f, repeated_contacts: e.target.checked }))}
          />
          <span className="text-slate-700">Wiederholte Kontakte</span>
        </label>
        <label className="flex items-center gap-2 self-end pb-1">
          <input
            type="checkbox"
            checked={filters.unresolved_repeated}
            onChange={(e) => setFilters((f) => ({ ...f, unresolved_repeated: e.target.checked }))}
          />
          <span className="text-slate-700">Offen &amp; mehrfach</span>
        </label>
        <button
          type="button"
          onClick={() => void fetchLeads()}
          disabled={loading}
          className="self-end rounded-lg bg-slate-200 px-3 py-1.5 text-slate-800 hover:bg-slate-300 disabled:opacity-50"
        >
          {loading ? "Laden…" : "Aktualisieren"}
        </button>
      </div>

      {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-[980px] w-full border-collapse text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 font-medium">Eingang</th>
              <th className="px-3 py-2 font-medium">Kontext</th>
              <th className="px-3 py-2 font-medium">Triage</th>
              <th className="px-3 py-2 font-medium">Weiterleitung</th>
              <th className="px-3 py-2 font-medium">Segment</th>
              <th className="px-3 py-2 font-medium">Firma</th>
              <th className="px-3 py-2 font-medium">Kontakt</th>
              <th className="px-3 py-2 font-medium">E-Mail</th>
              <th className="px-3 py-2 font-medium">Quelle</th>
              <th className="px-3 py-2 font-medium">Route</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr
                key={row.lead_id}
                className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 ${
                  selectedId === row.lead_id ? "bg-slate-100" : ""
                } ${row.needs_attention ? "border-l-4 border-l-amber-400" : ""}`}
                onClick={() => setSelectedId(row.lead_id)}
              >
                <td className="whitespace-nowrap px-3 py-2 text-slate-800">
                  {new Date(row.created_at).toLocaleString("de-DE")}
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {row.contact_submission_count > 1 ? (
                      <span
                        className="rounded bg-violet-100 px-1.5 py-0.5 text-xs text-violet-900"
                        title="Mehrfach eingereicht (gleiche E-Mail)"
                      >
                        ×{row.contact_submission_count}
                      </span>
                    ) : null}
                    {row.duplicate_hint === "same_email_repeat" ? (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">
                        Wdh.
                      </span>
                    ) : null}
                    {row.other_contacts_on_same_account > 0 ? (
                      <span
                        className="rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-900"
                        title="Weitere Kontakte unter gleicher Firmen-/Domain-Gruppe"
                      >
                        Firma+
                      </span>
                    ) : null}
                    {row.duplicate_review !== "none" ? (
                      <span className="rounded border border-slate-300 px-1.5 py-0.5 text-xs text-slate-700">
                        {row.duplicate_review === "confirmed" ? "OK manuell" : "Prüfen"}
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-3 py-2">{LEAD_TRIAGE_LABELS_DE[row.triage_status]}</td>
                <td className="px-3 py-2 text-slate-700">{forwardingLabel(row.forwarding_status)}</td>
                <td className="px-3 py-2 text-slate-700">{row.segment}</td>
                <td className="max-w-[120px] truncate px-3 py-2" title={row.company}>
                  {row.company}
                </td>
                <td className="max-w-[100px] truncate px-3 py-2" title={row.name}>
                  {row.name}
                </td>
                <td className="max-w-[140px] truncate px-3 py-2" title={row.business_email}>
                  {row.business_email}
                </td>
                <td className="max-w-[90px] truncate px-3 py-2" title={row.source_page}>
                  {row.source_page}
                </td>
                <td className="max-w-[140px] truncate px-3 py-2 text-slate-600" title={row.queue_label}>
                  {row.route_key}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && !loading ? (
          <p className="p-6 text-center text-sm text-slate-500">Keine Leads für die aktuellen Filter.</p>
        ) : null}
      </div>

      {displayLead ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {detailLoading ? (
            <p className="mb-4 text-sm text-slate-500">Detail &amp; Historie werden geladen …</p>
          ) : null}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Detail</h2>
              <p className="text-xs text-slate-500">
                lead_id: {displayLead.lead_id} · trace_id: {displayLead.trace_id}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Kontakt #{displayLead.contact_inquiry_sequence} von {displayLead.contact_submission_count}{" "}
                (Schlüssel: <span className="font-mono">{displayLead.lead_contact_key.slice(0, 18)}…</span>)
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                onClick={() => void patchLead(displayLead.lead_id, { triage_status: "triaged" })}
              >
                Triage erledigt
              </button>
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                onClick={() => void patchLead(displayLead.lead_id, { triage_status: "contacted" })}
              >
                Kontaktiert
              </button>
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm text-red-800 hover:bg-red-100 disabled:opacity-50"
                onClick={() => void patchLead(displayLead.lead_id, { triage_status: "spam" })}
              >
                Spam
              </button>
              {displayLead.forwarding_status === "failed" ? (
                <button
                  type="button"
                  disabled={saving}
                  className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                  onClick={() => void retryWebhook(displayLead.lead_id)}
                >
                  Webhook erneut senden
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <h3 className="text-sm font-medium text-slate-800">Kontakt-Historie (gleiche E-Mail)</h3>
            <p className="mt-1 text-xs text-slate-500">
              Chronologisch; jede Zeile ist eine eigene Formular-Einreichung (unverändert gespeichert).
            </p>
            <ul className="mt-3 max-h-56 space-y-2 overflow-auto text-sm">
              {contactHistory.map((h) => (
                <li
                  key={h.lead_id}
                  className={`rounded-lg border px-3 py-2 ${
                    h.lead_id === displayLead.lead_id ? "border-violet-300 bg-violet-50" : "border-slate-200"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs text-slate-600">
                      #{h.contact_inquiry_sequence} · {new Date(h.created_at).toLocaleString("de-DE")}
                    </span>
                    {h.lead_id !== displayLead.lead_id ? (
                      <button
                        type="button"
                        className="text-xs text-cyan-700 underline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedId(h.lead_id);
                        }}
                      >
                        öffnen
                      </button>
                    ) : (
                      <span className="text-xs text-violet-700">aktuell</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    {forwardingLabel(h.forwarding_status)} · {LEAD_TRIAGE_LABELS_DE[h.triage_status]}
                    {h.owner ? ` · Owner: ${h.owner}` : ""}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-700">{h.message_preview}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <h3 className="text-sm font-medium text-slate-800">GTM-Sync (Wave 28)</h3>
            <p className="mt-1 text-xs text-slate-500">
              Status pro Ziel (n8n, HubSpot, Stubs). Ohne konfigurierte Ziele entstehen keine Jobs.
            </p>
            {syncJobs.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Keine Sync-Jobs für diesen Lead.</p>
            ) : (
              <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full min-w-[880px] border-collapse text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-2 py-2 font-medium">Ziel</th>
                      <th className="px-2 py-2 font-medium">Status</th>
                      <th className="px-2 py-2 font-medium">Versuche</th>
                      <th className="px-2 py-2 font-medium">Letzter Versuch</th>
                      <th className="px-2 py-2 font-medium">Nächster Retry</th>
                      <th className="px-2 py-2 font-medium">Fehler</th>
                      <th className="px-2 py-2 font-medium">HubSpot-Referenz</th>
                      <th className="px-2 py-2 font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {syncJobs.map((j) => {
                      const hs = hubspotMockDetails(j.mock_result);
                      return (
                          <tr key={j.job_id} className="border-b border-slate-100">
                            <td className="px-2 py-2 text-slate-800">{SYNC_TARGET_LABELS[j.target]}</td>
                            <td className="px-2 py-2">{syncStatusLabel(j.status)}</td>
                            <td className="px-2 py-2 font-mono">{j.attempt_count}</td>
                            <td className="px-2 py-2 text-slate-600">
                              {j.last_attempt_at
                                ? new Date(j.last_attempt_at).toLocaleString("de-DE")
                                : "—"}
                            </td>
                            <td className="px-2 py-2 text-slate-600">
                              {j.next_retry_at ? new Date(j.next_retry_at).toLocaleString("de-DE") : "—"}
                            </td>
                            <td
                              className="max-w-[200px] truncate px-2 py-2 text-red-700"
                              title={j.last_error}
                            >
                              {j.last_error ?? "—"}
                            </td>
                            <td className="max-w-[220px] px-2 py-2 align-top text-[10px] text-slate-600">
                              {hs ? (
                                <ul className="list-inside list-disc space-y-0.5 font-mono">
                                  <li>Kontakt {hs.contact_id}</li>
                                  {hs.company_id ? <li>Firma {hs.company_id}</li> : null}
                                  {hs.note_id ? (
                                    <li>
                                      Notiz {hs.note_id} ({hs.note_action})
                                    </li>
                                  ) : null}
                                  <li className="list-none pl-0 font-sans text-slate-500">
                                    {HUBSPOT_COMPANY_ASSOC_DE[hs.company_association] ??
                                      hs.company_association}
                                  </li>
                                  {hs.synced_at ? (
                                    <li className="list-none pl-0 font-sans text-slate-400">
                                      Sync {new Date(hs.synced_at).toLocaleString("de-DE")}
                                    </li>
                                  ) : null}
                                </ul>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="px-2 py-2">
                              {j.status === "failed" ||
                              j.status === "dead_letter" ||
                              j.status === "pending" ||
                              j.status === "retrying" ? (
                                <button
                                  type="button"
                                  disabled={syncRetryingId === j.job_id}
                                  className="text-cyan-700 underline disabled:opacity-50"
                                  onClick={() => void retryLeadSyncJob(displayLead.lead_id, j.job_id)}
                                >
                                  {syncRetryingId === j.job_id ? "…" : "Retry"}
                                </button>
                              ) : null}
                            </td>
                          </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="text-sm font-medium text-slate-700">Nachricht</h3>
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-800">
                {displayLead.message || "(leer)"}
              </pre>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-600">Pipeline (Speicher):</span>{" "}
                <span className="font-mono text-slate-900">{displayLead.pipeline_status}</span>
              </div>
              <div>
                <span className="text-slate-600">Weiterleitung:</span>{" "}
                {forwardingLabel(displayLead.forwarding_status)}
                {displayLead.webhook_at ? (
                  <span className="ml-2 text-slate-500">({displayLead.webhook_at})</span>
                ) : null}
              </div>
              {displayLead.webhook_error ? (
                <div className="rounded-lg bg-red-50 p-2 text-red-800">
                  Fehler: {displayLead.webhook_error}
                </div>
              ) : null}
              <div>
                <span className="text-slate-600">Priorität / SLA-Bucket:</span> {displayLead.priority} /{" "}
                {displayLead.sla_bucket}
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 border-t border-slate-100 pt-4 md:grid-cols-2">
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Owner (intern)</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={draftOwner}
                onChange={(e) => setDraftOwner(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Dubletten-Review</span>
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={draftDuplicateReview}
                onChange={(e) =>
                  setDraftDuplicateReview(e.target.value as LeadInboxItem["duplicate_review"])
                }
              >
                {(Object.keys(DUPLICATE_REVIEW_LABELS) as LeadInboxItem["duplicate_review"][]).map((k) => (
                  <option key={k} value={k}>
                    {DUPLICATE_REVIEW_LABELS[k]}
                  </option>
                ))}
              </select>
            </label>
            <div className="md:col-span-2">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">
                  Verknüpfte Anfrage-IDs (UUID, kommagetrennt, max. 20)
                </span>
                <textarea
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
                  rows={2}
                  placeholder="z. B. manuell zusammenhängende Leads"
                  value={draftRelatedRaw}
                  onChange={(e) => setDraftRelatedRaw(e.target.value)}
                />
              </label>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Interne Notiz</span>
                <textarea
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  rows={4}
                  value={draftNote}
                  onChange={(e) => setDraftNote(e.target.value)}
                />
              </label>
            </div>
            <button
              type="button"
              disabled={saving}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              onClick={() =>
                void patchLead(displayLead.lead_id, {
                  owner: draftOwner,
                  internal_note: draftNote,
                  duplicate_review: draftDuplicateReview,
                  manual_related_lead_ids: parseRelatedIds(draftRelatedRaw),
                })
              }
            >
              Ops-Felder speichern
            </button>
            {actionMsg ? <p className="text-sm text-slate-600">{actionMsg}</p> : null}
          </div>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <h3 className="text-sm font-medium text-slate-700">Aktivität (intern)</h3>
            <ul className="mt-2 max-h-48 space-y-2 overflow-auto text-xs text-slate-600">
              {[...displayLead.activities].reverse().map((a, i) => (
                <li key={`${a.at}-${i}`} className="border-b border-slate-100 pb-2">
                  <span className="font-mono text-slate-500">{a.at}</span> · {a.action}
                  {a.detail ? <span className="text-slate-700"> — {a.detail}</span> : null}
                </li>
              ))}
              {displayLead.activities.length === 0 ? <li>Keine Einträge.</li> : null}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { LEAD_SEGMENTS } from "@/lib/leadCapture";
import type { LeadInboxItem } from "@/lib/leadInboxTypes";
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

export function AdminLeadInboxClient({ adminConfigured }: Props) {
  const [secretInput, setSecretInput] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [items, setItems] = useState<LeadInboxItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    triage_status: "",
    segment: "",
    source_page: "",
    forwarding_status: "",
  });
  const [draftOwner, setDraftOwner] = useState("");
  const [draftNote, setDraftNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const selected = useMemo(
    () => items.find((i) => i.lead_id === selectedId) ?? null,
    [items, selectedId],
  );

  useEffect(() => {
    if (!selected) {
      setDraftOwner("");
      setDraftNote("");
      return;
    }
    setDraftOwner(selected.owner);
    setDraftNote(selected.internal_note);
  }, [selected]);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (filters.triage_status) p.set("triage_status", filters.triage_status);
    if (filters.segment) p.set("segment", filters.segment);
    if (filters.source_page) p.set("source_page", filters.source_page);
    if (filters.forwarding_status) p.set("forwarding_status", filters.forwarding_status);
    p.set("limit", "500");
    const q = p.toString();
    return q ? `?${q}` : "?limit=500";
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
  }

  async function patchLead(
    leadId: string,
    body: { triage_status?: string; owner?: string; internal_note?: string },
  ) {
    setSaving(true);
    setActionMsg(null);
    try {
      const r = await fetch(`/api/admin/lead-inquiries/${leadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const data = (await r.json()) as { ok?: boolean; item?: LeadInboxItem | null };
      if (!r.ok) {
        setActionMsg("Speichern fehlgeschlagen.");
        return;
      }
      if (data.item) {
        setItems((prev) => prev.map((x) => (x.lead_id === data.item!.lead_id ? data.item! : x)));
      } else {
        await fetchLeads();
      }
      setActionMsg("Gespeichert.");
    } catch {
      setActionMsg("Netzwerkfehler beim Speichern.");
    } finally {
      setSaving(false);
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
            Triage und Nachverfolgung – nicht öffentlich, kein CRM. Sortierung: zuerst Aufmerksamkeit
            (fehlgeschlagene Weiterleitung oder Status &quot;Neu&quot;), dann neueste zuerst.
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
        <table className="min-w-[900px] w-full border-collapse text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 font-medium">Eingang</th>
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
                <td className="px-3 py-2">{LEAD_TRIAGE_LABELS_DE[row.triage_status]}</td>
                <td className="px-3 py-2 text-slate-700">{forwardingLabel(row.forwarding_status)}</td>
                <td className="px-3 py-2 text-slate-700">{row.segment}</td>
                <td className="max-w-[140px] truncate px-3 py-2" title={row.company}>
                  {row.company}
                </td>
                <td className="max-w-[120px] truncate px-3 py-2" title={row.name}>
                  {row.name}
                </td>
                <td className="max-w-[160px] truncate px-3 py-2" title={row.business_email}>
                  {row.business_email}
                </td>
                <td className="max-w-[100px] truncate px-3 py-2" title={row.source_page}>
                  {row.source_page}
                </td>
                <td className="max-w-[160px] truncate px-3 py-2 text-slate-600" title={row.queue_label}>
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

      {selected ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Detail</h2>
              <p className="text-xs text-slate-500">
                lead_id: {selected.lead_id} · trace_id: {selected.trace_id}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                onClick={() => void patchLead(selected.lead_id, { triage_status: "triaged" })}
              >
                Triage erledigt
              </button>
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                onClick={() => void patchLead(selected.lead_id, { triage_status: "contacted" })}
              >
                Kontaktiert
              </button>
              <button
                type="button"
                disabled={saving}
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm text-red-800 hover:bg-red-100 disabled:opacity-50"
                onClick={() => void patchLead(selected.lead_id, { triage_status: "spam" })}
              >
                Spam
              </button>
              {selected.forwarding_status === "failed" ? (
                <button
                  type="button"
                  disabled={saving}
                  className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                  onClick={() => void retryWebhook(selected.lead_id)}
                >
                  Webhook erneut senden
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="text-sm font-medium text-slate-700">Nachricht</h3>
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-800">
                {selected.message || "(leer)"}
              </pre>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-600">Pipeline (Speicher):</span>{" "}
                <span className="font-mono text-slate-900">{selected.pipeline_status}</span>
              </div>
              <div>
                <span className="text-slate-600">Weiterleitung:</span> {forwardingLabel(selected.forwarding_status)}
                {selected.webhook_at ? (
                  <span className="ml-2 text-slate-500">({selected.webhook_at})</span>
                ) : null}
              </div>
              {selected.webhook_error ? (
                <div className="rounded-lg bg-red-50 p-2 text-red-800">
                  Fehler: {selected.webhook_error}
                </div>
              ) : null}
              <div>
                <span className="text-slate-600">Priorität / SLA-Bucket:</span> {selected.priority} /{" "}
                {selected.sla_bucket}
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
                void patchLead(selected.lead_id, { owner: draftOwner, internal_note: draftNote })
              }
            >
              Notiz &amp; Owner speichern
            </button>
            {actionMsg ? <p className="text-sm text-slate-600">{actionMsg}</p> : null}
          </div>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <h3 className="text-sm font-medium text-slate-700">Aktivität (intern)</h3>
            <ul className="mt-2 max-h-48 space-y-2 overflow-auto text-xs text-slate-600">
              {[...selected.activities].reverse().map((a, i) => (
                <li key={`${a.at}-${i}`} className="border-b border-slate-100 pb-2">
                  <span className="font-mono text-slate-500">{a.at}</span> · {a.action}
                  {a.detail ? <span className="text-slate-700"> — {a.detail}</span> : null}
                </li>
              ))}
              {selected.activities.length === 0 ? <li>Keine Einträge.</li> : null}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}

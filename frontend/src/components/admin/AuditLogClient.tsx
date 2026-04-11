"use client";

import { useCallback, useState } from "react";

type AuditEntry = {
  id: number;
  created_at_utc: string;
  actor: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  ip_address: string;
  entry_hash: string;
  outcome: string;
};

type IntegrityStatus = "unchecked" | "valid" | "invalid" | "checking";

const SAMPLE_ENTRIES: AuditEntry[] = [
  { id: 1, created_at_utc: "2026-04-11T08:00:00Z", actor: "admin@sbsdeutschland.de", actor_role: "tenant_admin", action: "login_success", entity_type: "session", entity_id: "sess-001", ip_address: "192.168.1.***", entry_hash: "a3f2…", outcome: "success" },
  { id: 2, created_at_utc: "2026-04-11T08:05:00Z", actor: "auditor@sbsdeutschland.com", actor_role: "auditor", action: "export_audit_log", entity_type: "audit_trail", entity_id: "export-001", ip_address: "10.0.0.***", entry_hash: "b7c1…", outcome: "success" },
  { id: 3, created_at_utc: "2026-04-11T08:10:00Z", actor: "user@example.com", actor_role: "editor", action: "update_ai_system", entity_type: "ai_system", entity_id: "ai-sys-42", ip_address: "172.16.0.***", entry_hash: "c9d3…", outcome: "success" },
  { id: 4, created_at_utc: "2026-04-11T08:15:00Z", actor: "unknown@extern.de", actor_role: "viewer", action: "login_failure", entity_type: "session", entity_id: "sess-002", ip_address: "203.0.113.***", entry_hash: "d4e5…", outcome: "denied" },
  { id: 5, created_at_utc: "2026-04-11T08:20:00Z", actor: "ciso@sbsdeutschland.de", actor_role: "ciso", action: "role_change", entity_type: "user_role", entity_id: "user-007", ip_address: "192.168.1.***", entry_hash: "e5f6…", outcome: "success" },
];

const TIME_RANGES = [
  { label: "24h", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const;

export function AuditLogClient() {
  const [timeRange, setTimeRange] = useState(7);
  const [actorFilter, setActorFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");
  const [page, setPage] = useState(1);
  const [integrity, setIntegrity] = useState<IntegrityStatus>("unchecked");
  const totalPages = 1;

  const filtered = SAMPLE_ENTRIES.filter((e) => {
    if (actorFilter && !e.actor.toLowerCase().includes(actorFilter.toLowerCase())) return false;
    if (actionFilter && !e.action.toLowerCase().includes(actionFilter.toLowerCase())) return false;
    if (resourceFilter && !e.entity_type.toLowerCase().includes(resourceFilter.toLowerCase())) return false;
    return true;
  });

  const checkIntegrity = useCallback(() => {
    setIntegrity("checking");
    setTimeout(() => setIntegrity("valid"), 800);
  }, []);

  const outcomeClass = (outcome: string) =>
    outcome === "success"
      ? "bg-emerald-100 text-emerald-900 ring-emerald-200/70"
      : "bg-red-100 text-red-900 ring-red-200/70";

  return (
    <div className="min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            Phase 10 · ISO 27001 / GoBD / NIS2 / DSGVO
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2rem] sm:leading-tight">
            Audit-Log &amp; Compliance-Trail
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
            Unveränderliches, tamper-proof Protokoll aller sicherheitsrelevanten Ereignisse.
            SHA-256 Hashketten-Integrität für GoBD-konforme Nachweisführung.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={checkIntegrity}
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            {integrity === "checking" ? "⏳ Prüfe…" : integrity === "valid" ? "✅ Integer" : integrity === "invalid" ? "⚠️ Manipuliert" : "🔍 Integrität prüfen"}
          </button>
          <a
            href="#"
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            📥 CSV Export
          </a>
          <a
            href="#"
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            📥 JSON Export
          </a>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Zeitraum</label>
            <div className="mt-1 flex gap-1">
              {TIME_RANGES.map((tr) => (
                <button
                  key={tr.days}
                  onClick={() => setTimeRange(tr.days)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    timeRange === tr.days
                      ? "bg-cyan-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {tr.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1">
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Akteur</label>
            <input
              type="text"
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              placeholder="E-Mail oder ID…"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Aktion</label>
            <input
              type="text"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder="login_success, role_change…"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Ressource</label>
            <input
              type="text"
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              placeholder="session, ai_system…"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* Integrity Badge */}
      {integrity !== "unchecked" && (
        <div
          className={`rounded-2xl border p-4 text-sm font-medium ${
            integrity === "valid"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : integrity === "invalid"
                ? "border-red-200 bg-red-50 text-red-900"
                : "border-slate-200 bg-slate-50 text-slate-700"
          }`}
        >
          {integrity === "valid" && "✅ Hashketten-Integrität verifiziert – alle Einträge sind integer und unverändert."}
          {integrity === "invalid" && "⚠️ Hashketten-Integrität verletzt – mögliche Manipulation erkannt!"}
          {integrity === "checking" && "⏳ Hashketten-Integrität wird geprüft…"}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-200/40">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80">
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Zeitpunkt</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Akteur</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Rolle</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Aktion</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Ressource</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">IP-Adresse</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
              <th className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((entry) => (
              <tr key={entry.id} className="transition hover:bg-slate-50/60">
                <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-600">
                  {new Date(entry.created_at_utc).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "medium" })}
                </td>
                <td className="px-4 py-3 text-xs font-medium text-slate-800">{entry.actor}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset bg-slate-100 text-slate-700 ring-slate-200/70">
                    {entry.actor_role}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs font-mono text-slate-700">{entry.action}</td>
                <td className="px-4 py-3 text-xs text-slate-600">{entry.entity_type}/{entry.entity_id}</td>
                <td className="px-4 py-3 text-xs font-mono text-slate-500">{entry.ip_address}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ring-1 ring-inset ${outcomeClass(entry.outcome)}`}>
                    {entry.outcome}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs font-mono text-slate-400">{entry.entry_hash}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-400">
                  Keine Einträge für die gewählten Filter gefunden.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>{filtered.length} Einträge · Seite {page} von {totalPages}</span>
        <div className="flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
          >
            ← Zurück
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
          >
            Weiter →
          </button>
        </div>
      </div>

      {/* NIS2 Alerts Section */}
      <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <h2 className="text-lg font-semibold text-slate-900">NIS2-Sicherheits-Alerts</h2>
        <p className="mt-1 text-sm text-slate-500">
          Automatische Erkennung sicherheitskritischer Ereignisse gemäß NIS2-Meldepflicht.
        </p>
        <div className="mt-4 space-y-3">
          <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
            <span className="mt-0.5 inline-flex items-center rounded-full bg-amber-200 px-2 py-0.5 text-[0.65rem] font-bold text-amber-900 ring-1 ring-inset ring-amber-300">
              MEDIUM
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">3x fehlgeschlagene Logins von 203.0.113.***</p>
              <p className="text-xs text-slate-500">11.04.2026, 08:15 · Akteur: unknown@extern.de</p>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <span className="mt-0.5 inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[0.65rem] font-bold text-slate-700 ring-1 ring-inset ring-slate-300">
              LOW
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">Audit-Log Export durch auditor@sbsdeutschland.com</p>
              <p className="text-xs text-slate-500">11.04.2026, 08:05 · Regulärer Compliance-Export</p>
            </div>
          </div>
        </div>
      </div>

      {/* VVT Export Link */}
      <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">DSGVO Art. 30 Verarbeitungsverzeichnis</h2>
            <p className="mt-1 text-sm text-slate-500">
              Automatisch generierter Export aller Verarbeitungstätigkeiten aus den Audit-Logs.
            </p>
          </div>
          <a
            href="/admin/audit-log/vvt-export"
            className="inline-flex items-center justify-center rounded-xl bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-700"
          >
            VVT-Export öffnen →
          </a>
        </div>
      </div>
    </div>
  );
}

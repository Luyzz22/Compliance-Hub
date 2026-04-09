"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_PAGE_NAV_LINK,
  CH_SECTION_LABEL,
} from "@/lib/boardLayout";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";
const TENANT_ID =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

type DeadlineCategory =
  | "eu_ai_act"
  | "nis2"
  | "iso_27001"
  | "iso_42001"
  | "dsgvo"
  | "gobd"
  | "kritis"
  | "custom";

type DeadlineStatus = "open" | "in_progress" | "completed" | "overdue";

type EscalationLevel = "none" | "info" | "warning" | "critical" | "overdue";

interface Deadline {
  id: string;
  tenant_id: string | null;
  title: string;
  description: string | null;
  category: DeadlineCategory;
  due_date: string;
  status: DeadlineStatus;
  owner: string | null;
  regulation_reference: string | null;
  recurrence_months: number | null;
  is_system: boolean;
  escalation_level: EscalationLevel;
  days_remaining: number;
  created_at_utc: string;
}

const CATEGORY_LABELS: Record<DeadlineCategory, string> = {
  eu_ai_act: "EU AI Act",
  nis2: "NIS2",
  iso_27001: "ISO 27001",
  iso_42001: "ISO 42001",
  dsgvo: "DSGVO",
  gobd: "GoBD",
  kritis: "KRITIS",
  custom: "Individuell",
};

const STATUS_LABELS: Record<DeadlineStatus, string> = {
  open: "Offen",
  in_progress: "In Bearbeitung",
  completed: "Erledigt",
  overdue: "Überfällig",
};

function trafficLightClass(
  daysRemaining: number,
  status: DeadlineStatus,
): string {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (daysRemaining < 0) return "bg-red-100 text-red-800";
  if (daysRemaining < 7) return "bg-red-100 text-red-800";
  if (daysRemaining <= 30) return "bg-amber-100 text-amber-900";
  return "bg-emerald-100 text-emerald-800";
}

function trafficDot(daysRemaining: number, status: DeadlineStatus): string {
  if (status === "completed") return "bg-emerald-500";
  if (daysRemaining < 0) return "bg-red-500";
  if (daysRemaining < 7) return "bg-red-500";
  if (daysRemaining <= 30) return "bg-amber-500";
  return "bg-emerald-500";
}

function buildHeaders(): Record<string, string> {
  const opaRole = process.env.NEXT_PUBLIC_OPA_USER_ROLE?.trim();
  const h: Record<string, string> = {
    "x-api-key": API_KEY,
    "x-tenant-id": TENANT_ID,
  };
  if (opaRole) h["x-opa-user-role"] = opaRole;
  return h;
}

export default function ComplianceCalendarPage() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSystemOnly, setFilterSystemOnly] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] =
    useState<DeadlineCategory>("custom");
  const [newDueDate, setNewDueDate] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newRegRef, setNewRegRef] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchDeadlines = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/compliance-calendar/deadlines`,
        { headers: buildHeaders() },
      );
      if (!res.ok) {
        setError(`Fehler beim Laden (HTTP ${res.status})`);
        return;
      }
      const data: Deadline[] = await res.json();
      setDeadlines(data);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Unbekannter Fehler",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDeadlines();
  }, [fetchDeadlines]);

  async function handleCreate() {
    if (!newTitle.trim() || !newDueDate) return;
    setCreating(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/compliance-calendar/deadlines`,
        {
          method: "POST",
          headers: {
            ...buildHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: newTitle,
            category: newCategory,
            due_date: newDueDate,
            description: newDescription || null,
            regulation_reference: newRegRef || null,
          }),
        },
      );
      if (res.status === 403) {
        setError(
          "Zugriff verweigert – nur TENANT_ADMIN / COMPLIANCE_ADMIN.",
        );
        return;
      }
      if (!res.ok) {
        setError(`Erstellen fehlgeschlagen (HTTP ${res.status})`);
        return;
      }
      setShowCreateForm(false);
      setNewTitle("");
      setNewDueDate("");
      setNewDescription("");
      setNewRegRef("");
      await fetchDeadlines();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Fehler beim Erstellen",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleIcalDownload() {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/compliance-calendar/export/ical`,
        { headers: buildHeaders() },
      );
      if (!res.ok) {
        setError(`iCal-Export fehlgeschlagen (HTTP ${res.status})`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "compliance-calendar.ics";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Fehler beim iCal-Export",
      );
    }
  }

  const filtered = deadlines.filter((d) => {
    if (filterCategory !== "all" && d.category !== filterCategory)
      return false;
    if (filterStatus !== "all" && d.status !== filterStatus)
      return false;
    if (filterSystemOnly && !d.is_system) return false;
    return true;
  });

  return (
    <div className="min-w-0">
      {/* ── Header ── */}
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Compliance Calendar
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Regulatorische Fristen
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          DACH-System-Deadlines, tenant-spezifische Fristen und
          Ampel-Status – EU AI Act, NIS2, DSGVO, GoBD, KRITIS.
        </p>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">
          <Link
            href="/board/executive-dashboard"
            className={CH_PAGE_NAV_LINK}
          >
            Executive Dashboard
          </Link>
          <Link href="/board/n8n-workflows" className={CH_PAGE_NAV_LINK}>
            n8n Workflows
          </Link>
        </div>
      </header>

      {/* ── Action Buttons ── */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          onClick={() => setShowCreateForm((v) => !v)}
          className={CH_BTN_PRIMARY}
        >
          {showCreateForm ? "Abbrechen" : "Neue Frist anlegen"}
        </button>
        <button onClick={handleIcalDownload} className={CH_BTN_SECONDARY}>
          iCal herunterladen (.ics)
        </button>
      </div>

      {/* ── Create Form ── */}
      {showCreateForm && (
        <section className={`${CH_CARD} mb-6 space-y-4`}>
          <p className={CH_SECTION_LABEL}>Neue Frist</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Titel *
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="z. B. ISO 27001 Re-Zertifizierung"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Kategorie
              <select
                value={newCategory}
                onChange={(e) =>
                  setNewCategory(e.target.value as DeadlineCategory)
                }
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Fälligkeitsdatum *
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Beschreibung
              <input
                type="text"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Optional"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Norm-Referenz
              <input
                type="text"
                value={newRegRef}
                onChange={(e) => setNewRegRef(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="z. B. DSGVO Art. 33"
              />
            </label>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newTitle.trim() || !newDueDate}
            className={CH_BTN_PRIMARY}
          >
            {creating ? "Erstelle…" : "Frist erstellen"}
          </button>
        </section>
      )}

      {/* ── Error ── */}
      {error && (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 font-medium underline"
          >
            Schließen
          </button>
        </div>
      )}

      {/* ── Filters ── */}
      <section className={`${CH_CARD} mb-6`}>
        <p className={CH_SECTION_LABEL}>Filter</p>
        <div className="mt-3 flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Kategorie
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="all">Alle</option>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Status
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="all">Alle</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={filterSystemOnly}
              onChange={(e) => setFilterSystemOnly(e.target.checked)}
              className="rounded"
            />
            Nur System-Deadlines
          </label>
        </div>
      </section>

      {/* ── Deadline List ── */}
      {loading ? (
        <p className="py-8 text-center text-sm text-slate-400">
          Lade Fristen…
        </p>
      ) : filtered.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-400">
          Keine Fristen gefunden.
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((d) => (
            <article
              key={d.id}
              className={`${CH_CARD} flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between`}
            >
              <div className="flex items-start gap-3">
                {/* Traffic-light dot */}
                <span
                  className={`mt-1.5 h-3 w-3 shrink-0 rounded-full ${trafficDot(d.days_remaining, d.status)}`}
                  title={
                    d.days_remaining < 0
                      ? "Überfällig"
                      : d.days_remaining < 7
                        ? "Kritisch"
                        : d.days_remaining <= 30
                          ? "Warnung"
                          : "Im Plan"
                  }
                />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-900">
                      {d.title}
                    </h3>
                    {d.is_system && (
                      <span className="rounded border border-cyan-200 bg-cyan-50 px-1.5 py-0.5 text-[0.6rem] font-semibold uppercase tracking-wide text-cyan-700">
                        System
                      </span>
                    )}
                    <span
                      className={`rounded px-1.5 py-0.5 text-[0.6rem] font-semibold ${trafficLightClass(d.days_remaining, d.status)}`}
                    >
                      {STATUS_LABELS[d.status]}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {CATEGORY_LABELS[d.category]}
                    {d.regulation_reference
                      ? ` · ${d.regulation_reference}`
                      : ""}
                    {d.owner ? ` · ${d.owner}` : ""}
                  </p>
                  {d.description && (
                    <p className="mt-1 text-xs text-slate-400">
                      {d.description}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1 text-right">
                <span className="text-sm font-medium text-slate-700">
                  {d.due_date}
                </span>
                <span
                  className={`text-xs font-medium ${
                    d.days_remaining < 0
                      ? "text-red-600"
                      : d.days_remaining < 7
                        ? "text-red-600"
                        : d.days_remaining <= 30
                          ? "text-amber-600"
                          : "text-emerald-600"
                  }`}
                >
                  {d.days_remaining < 0
                    ? `${Math.abs(d.days_remaining)} Tage überfällig`
                    : d.days_remaining === 0
                      ? "Heute fällig"
                      : `${d.days_remaining} Tage verbleibend`}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* ── Info ── */}
      <section className={`${CH_CARD} mt-6 space-y-2`}>
        <p className={CH_SECTION_LABEL}>Hinweise</p>
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
          <li>
            <strong>Grün:</strong> Mehr als 30 Tage verbleibend
          </li>
          <li>
            <strong>Gelb:</strong> 7–30 Tage verbleibend
          </li>
          <li>
            <strong>Rot:</strong> Weniger als 7 Tage oder überfällig
          </li>
          <li>
            System-Deadlines (
            <span className="rounded border border-cyan-200 bg-cyan-50 px-1 text-[0.6rem] font-semibold uppercase text-cyan-700">
              System
            </span>
            ) sind für alle Mandanten sichtbar und nicht editierbar.
          </li>
          <li>
            iCal-Export ist kompatibel mit Google Calendar und Outlook.
          </li>
        </ul>
      </section>
    </div>
  );
}

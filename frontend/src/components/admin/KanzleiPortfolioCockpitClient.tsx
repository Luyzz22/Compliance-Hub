"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import { GTM_READINESS_CLASSES, GTM_READINESS_SHORT_DE } from "@/lib/gtmAccountReadiness";
import { KanzleiReviewPlaybookHelper } from "@/components/admin/KanzleiReviewPlaybookHelper";
import type { AdvisorKpiPortfolioSnapshot, AdvisorKpiTrend, AdvisorKpiTraffic } from "@/lib/advisorKpiTypes";
import type { KanzleiMonthlyReportDto } from "@/lib/kanzleiMonthlyReportTypes";
import type { PartnerReviewPackageDto } from "@/lib/partnerReviewPackageTypes";
import {
  MANDANT_REMINDER_CATEGORY_LABEL_DE,
  type MandantReminderApiEntry,
} from "@/lib/advisorMandantReminderTypes";
import { isDueThisCalendarWeek, isDueTodayOrOverdue } from "@/lib/advisorMandantReminderRules";
import type {
  KanzleiAttentionQueueItem,
  KanzleiPortfolioPayload,
  KanzleiPortfolioPillarFilter,
  KanzleiPortfolioReadinessFilter,
  KanzleiPortfolioRow,
} from "@/lib/kanzleiPortfolioTypes";
import { isNonEmptyUnparsableIso } from "@/lib/mandantHistoryMerge";

type Props = { adminConfigured: boolean };

function kpiTrendSymbol(t: AdvisorKpiTrend): string {
  if (t === "up") return "↑";
  if (t === "down") return "↓";
  if (t === "flat") return "→";
  return "○";
}

function kpiTileBorder(t: AdvisorKpiTraffic): string {
  if (t === "green") return "border-emerald-300 bg-emerald-50/70";
  if (t === "amber") return "border-amber-300 bg-amber-50/70";
  if (t === "red") return "border-rose-300 bg-rose-50/70";
  return "border-slate-200 bg-slate-50/80";
}

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

function showKeinExportBadge(row: KanzleiPortfolioRow): boolean {
  if (!row.never_any_export) return false;
  return (
    !isNonEmptyUnparsableIso(row.last_mandant_readiness_export_at) &&
    !isNonEmptyUnparsableIso(row.last_datev_bundle_export_at)
  );
}

function AttentionQueuePanel({
  items,
  onMarkReview,
  reviewBusyId,
}: {
  items: KanzleiAttentionQueueItem[];
  onMarkReview: (tenantId: string) => void;
  reviewBusyId: string | null;
}) {
  return (
    <section className="max-h-[min(70vh,520px)] overflow-y-auto rounded-xl border border-amber-200 bg-amber-50/50 p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-amber-950">Attention-Queue</h2>
      <p className="mt-1 text-[11px] leading-snug text-slate-600">
        Priorisiert nach Kanzlei-Attention-Score und harten Signalen (Review, Export, Lücken, Ampeln). Kein
        Workflow-Tool – nur die Reihenfolge für Ihre wöchentliche Durcharbeitung.
      </p>
      {items.length === 0 ? (
        <p className="mt-3 text-xs text-slate-600">
          Kein Mandant erfüllt die Queue-Kriterien – gute Ausgangslage oder Daten noch nicht vollständig.
        </p>
      ) : (
        <ol className="mt-3 space-y-3">
          {items.map((q, idx) => (
            <li
              key={q.tenant_id}
              className="rounded-lg border border-amber-100 bg-white/90 p-3 text-xs text-slate-800 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <span className="font-mono text-[10px] text-slate-400">#{idx + 1}</span>{" "}
                  <span className="font-semibold text-slate-900">{q.mandant_label ?? q.tenant_id}</span>
                  <div className="font-mono text-[10px] text-slate-500">{q.tenant_id}</div>
                </div>
                <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
                  Score {q.attention_score}
                </span>
              </div>
              <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Warum jetzt?
              </p>
              <ul className="mt-0.5 list-inside list-disc space-y-0.5 text-[11px] text-slate-700">
                {q.warum_jetzt_de.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-slate-800">
                <span className="font-semibold text-violet-900">Nächster Schritt:</span>{" "}
                {q.naechster_schritt_de}
              </p>
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                <a className="text-cyan-700 underline" href={q.links.mandant_export_page}>
                  Mandanten-Export
                </a>
                <a className="text-cyan-700 underline" href={q.links.datev_bundle_api}>
                  DATEV-ZIP
                </a>
                <button
                  type="button"
                  disabled={reviewBusyId === q.tenant_id}
                  onClick={() => onMarkReview(q.tenant_id)}
                  className="text-violet-800 underline disabled:opacity-50"
                >
                  {reviewBusyId === q.tenant_id ? "…" : "Review durchgeführt"}
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
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

function ReminderRowItem({
  r,
  busy,
  onDone,
  onDismiss,
}: {
  r: MandantReminderApiEntry;
  busy: boolean;
  onDone: () => void;
  onDismiss: () => void;
}) {
  return (
    <li className="rounded border border-rose-100 bg-white/90 p-2 text-[11px] text-slate-800">
      <div className="font-medium text-slate-900">
        {r.mandant_label ?? r.tenant_id}{" "}
        <span className="font-mono text-[10px] text-slate-400">({r.tenant_id})</span>
      </div>
      <div className="text-slate-600">{MANDANT_REMINDER_CATEGORY_LABEL_DE[r.category]}</div>
      <div className="text-slate-500">Fällig: {formatIsoDe(r.due_at)}</div>
      {r.note ? <div className="mt-0.5 text-slate-600">{r.note}</div> : null}
      <div className="mt-1 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onDone}
          className="text-cyan-800 underline disabled:opacity-50"
        >
          Erledigt
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onDismiss}
          className="text-slate-600 underline disabled:opacity-50"
        >
          Zurückstellen
        </button>
      </div>
    </li>
  );
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

  const [reportPeriod, setReportPeriod] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [reportCompare, setReportCompare] = useState(true);
  const [reportSaveBaseline, setReportSaveBaseline] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportErr, setReportErr] = useState<string | null>(null);
  const [reportMd, setReportMd] = useState<string | null>(null);
  const [reportDto, setReportDto] = useState<KanzleiMonthlyReportDto | null>(null);

  const [partnerLoading, setPartnerLoading] = useState(false);
  const [partnerErr, setPartnerErr] = useState<string | null>(null);
  const [partnerMd, setPartnerMd] = useState<string | null>(null);
  const [partnerDto, setPartnerDto] = useState<PartnerReviewPackageDto | null>(null);
  const [partnerCompare, setPartnerCompare] = useState(true);
  const [partnerTopN, setPartnerTopN] = useState(8);

  const [kpiSnapshot, setKpiSnapshot] = useState<AdvisorKpiPortfolioSnapshot | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);
  const [kpiErr, setKpiErr] = useState<string | null>(null);
  const [kpiWindowDays, setKpiWindowDays] = useState(90);

  const [reminderPatchBusyId, setReminderPatchBusyId] = useState<string | null>(null);
  const [manualRemTenantId, setManualRemTenantId] = useState("");
  const [manualRemDue, setManualRemDue] = useState("");
  const [manualRemCat, setManualRemCat] = useState<"manual" | "follow_up_note">("follow_up_note");
  const [manualRemNote, setManualRemNote] = useState("");
  const [manualRemBusy, setManualRemBusy] = useState(false);

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

  const fetchKpi = useCallback(async () => {
    setKpiLoading(true);
    setKpiErr(null);
    try {
      const w = Math.min(365, Math.max(7, kpiWindowDays));
      const r = await fetch(`/api/internal/advisor/kpi-portfolio?window_days=${w}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setKpiErr("KPI: nicht angemeldet.");
        setKpiSnapshot(null);
        return;
      }
      if (!r.ok) {
        setKpiErr(`KPI: HTTP ${r.status}`);
        setKpiSnapshot(null);
        return;
      }
      const data = (await r.json()) as { advisor_kpi_portfolio?: AdvisorKpiPortfolioSnapshot };
      setKpiSnapshot(data.advisor_kpi_portfolio ?? null);
    } catch {
      setKpiErr("KPI: Netzwerkfehler");
      setKpiSnapshot(null);
    } finally {
      setKpiLoading(false);
    }
  }, [kpiWindowDays]);

  useEffect(() => {
    if (!adminConfigured || !payload?.generated_at) return;
    void fetchKpi();
  }, [adminConfigured, payload?.generated_at, fetchKpi]);

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

  const fetchMonthlyReport = useCallback(async () => {
    setReportLoading(true);
    setReportErr(null);
    try {
      const q = new URLSearchParams();
      q.set("period", reportPeriod.trim());
      if (!reportCompare) q.set("compare", "0");
      if (reportSaveBaseline) q.set("update_baseline", "1");
      const r = await fetch(`/api/internal/advisor/kanzlei-monthly-report?${q}`, { credentials: "include" });
      if (r.status === 401) {
        setReportErr("Nicht angemeldet (Admin-Secret).");
        setReportMd(null);
        setReportDto(null);
        return;
      }
      if (!r.ok) {
        setReportErr(`HTTP ${r.status}`);
        setReportMd(null);
        setReportDto(null);
        return;
      }
      const data = (await r.json()) as {
        ok?: boolean;
        report?: KanzleiMonthlyReportDto;
        markdown_de?: string;
        baseline_updated?: boolean;
      };
      setReportDto(data.report ?? null);
      setReportMd(data.markdown_de ?? null);
      if (data.baseline_updated) {
        void load();
      }
    } catch {
      setReportErr("Netzwerkfehler");
      setReportMd(null);
      setReportDto(null);
    } finally {
      setReportLoading(false);
    }
  }, [load, reportCompare, reportPeriod, reportSaveBaseline]);

  const copyReportMd = useCallback(async () => {
    if (!reportMd) return;
    try {
      await navigator.clipboard.writeText(reportMd);
    } catch {
      /* ignore */
    }
  }, [reportMd]);

  const fetchPartnerReviewPackage = useCallback(async () => {
    setPartnerLoading(true);
    setPartnerErr(null);
    try {
      const q = new URLSearchParams();
      const top = Math.min(15, Math.max(3, Number.isFinite(partnerTopN) ? partnerTopN : 8));
      q.set("top_n", String(top));
      if (!partnerCompare) q.set("compare", "0");
      const r = await fetch(`/api/internal/advisor/partner-review-package?${q}`, {
        credentials: "include",
      });
      if (r.status === 401) {
        setPartnerErr("Nicht angemeldet (Admin-Secret).");
        setPartnerMd(null);
        setPartnerDto(null);
        return;
      }
      if (!r.ok) {
        setPartnerErr(`HTTP ${r.status}`);
        setPartnerMd(null);
        setPartnerDto(null);
        return;
      }
      const data = (await r.json()) as {
        ok?: boolean;
        partner_review_package?: PartnerReviewPackageDto;
        markdown_de?: string;
      };
      setPartnerDto(data.partner_review_package ?? null);
      setPartnerMd(data.markdown_de ?? null);
    } catch {
      setPartnerErr("Netzwerkfehler");
      setPartnerMd(null);
      setPartnerDto(null);
    } finally {
      setPartnerLoading(false);
    }
  }, [partnerCompare, partnerTopN]);

  const copyPartnerMd = useCallback(async () => {
    if (!partnerMd) return;
    try {
      await navigator.clipboard.writeText(partnerMd);
    } catch {
      /* ignore */
    }
  }, [partnerMd]);

  const downloadPartnerMd = useCallback(() => {
    if (!partnerMd) return;
    const blob = new Blob([partnerMd], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `partner-review-package-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [partnerMd]);

  const patchReminderStatus = useCallback(
    async (reminderId: string, status: "done" | "dismissed") => {
      setReminderPatchBusyId(reminderId);
      try {
        const r = await fetch("/api/internal/advisor/mandant-reminders", {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reminder_id: reminderId, status }),
        });
        if (r.ok) await load();
      } finally {
        setReminderPatchBusyId(null);
      }
    },
    [load],
  );

  const submitManualReminder = useCallback(async () => {
    const tid = manualRemTenantId.trim();
    if (!tid || !manualRemDue.trim()) return;
    setManualRemBusy(true);
    try {
      const r = await fetch("/api/internal/advisor/mandant-reminders", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: tid,
          category: manualRemCat,
          due_at: manualRemDue.trim(),
          ...(manualRemNote.trim() ? { note: manualRemNote.trim() } : {}),
        }),
      });
      if (r.ok) {
        setManualRemNote("");
        await load();
      }
    } finally {
      setManualRemBusy(false);
    }
  }, [load, manualRemCat, manualRemDue, manualRemNote, manualRemTenantId]);

  const remindersDueUrgent = useMemo(() => {
    const list = payload?.open_reminders ?? [];
    const now = Date.now();
    return list.filter((r) => isDueTodayOrOverdue(r.due_at, now));
  }, [payload?.open_reminders]);

  const remindersDueWeekNotUrgent = useMemo(() => {
    const list = payload?.open_reminders ?? [];
    const now = Date.now();
    return list.filter((r) => isDueThisCalendarWeek(r.due_at, now) && !isDueTodayOrOverdue(r.due_at, now));
  }, [payload?.open_reminders]);

  useEffect(() => {
    if (!payload?.rows.length) return;
    setManualRemTenantId((prev) => (prev ? prev : payload.rows[0]!.tenant_id));
    setManualRemDue((prev) => {
      if (prev) return prev;
      const d = new Date();
      d.setDate(d.getDate() + 7);
      return d.toISOString().slice(0, 10);
    });
  }, [payload?.rows]);

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
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Wave 39–45 · Kanzlei / Berater</p>
          <h1 className="text-2xl font-semibold text-slate-900">Mehrmandanten-Kanzlei-Cockpit</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Welcher Mandant braucht jetzt Aufmerksamkeit? Portfolio über gemappte Mandanten mit Readiness,
            offenen Prüfpunkten, Export-Historie (Readiness / DATEV-ZIP), Review-Kadenz (Wave 40),
            Attention-Queue, Review-Playbook (Wave 41), Monatsreport (Wave 42), Reminders / Follow-ups
            (Wave 43), Partner-Review-Paket (Wave 44) und Kanzlei-KPIs (Wave 45) für internes Steering.
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
            </code>{" "}
            ·{" "}
            <code className="rounded bg-slate-100 px-1 text-[11px]">
              GET /api/internal/advisor/partner-review-package
            </code>{" "}
            ·{" "}
            <code className="rounded bg-slate-100 px-1 text-[11px]">
              GET /api/internal/advisor/kpi-portfolio
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
        <section
          id="kanzlei-kpi-strip"
          className="rounded-xl border border-teal-200 bg-teal-50/40 p-4 shadow-sm"
        >
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-teal-950">Kanzlei-KPIs (Wave 45)</h2>
              <p className="mt-1 text-[11px] text-slate-600">
                Operative Kennzahlen für Regelmäßigkeit (Review, Export, Reminder-Reaktion). Kein BI-System –{" "}
                <code className="rounded bg-white px-1">GET /api/internal/advisor/kpi-portfolio</code>.
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <label className="text-[11px] font-medium text-slate-700">
                Fenster (Tage)
                <select
                  className="mt-0.5 block rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                  value={kpiWindowDays}
                  onChange={(e) => setKpiWindowDays(Number.parseInt(e.target.value, 10) || 90)}
                >
                  <option value={30}>30</option>
                  <option value={60}>60</option>
                  <option value={90}>90</option>
                </select>
              </label>
              <button
                type="button"
                disabled={kpiLoading}
                onClick={() => void fetchKpi()}
                className="rounded-lg border border-teal-700 bg-teal-800 px-2 py-1 text-[11px] text-white hover:bg-teal-900 disabled:opacity-50"
              >
                {kpiLoading ? "…" : "KPI aktualisieren"}
              </button>
            </div>
          </div>
          {kpiErr ? <p className="mt-2 text-[11px] text-red-600">{kpiErr}</p> : null}
          {kpiSnapshot ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
              {kpiSnapshot.strip.map((tile) => (
                <a
                  key={tile.id}
                  href={tile.href ?? "#"}
                  className={`block rounded-lg border p-2.5 text-[11px] shadow-sm transition hover:opacity-95 ${kpiTileBorder(tile.traffic_light)}`}
                >
                  <div className="font-semibold text-slate-900">{tile.label_de}</div>
                  <div className="mt-1 flex items-baseline gap-1.5 tabular-nums">
                    <span className="text-base font-bold text-slate-900">{tile.value_display_de}</span>
                    <span className="text-slate-600" title="Trend vs. Vorperiode (wo verfügbar)">
                      {kpiTrendSymbol(tile.trend)}
                    </span>
                  </div>
                  <p className="mt-1 leading-snug text-slate-600">{tile.hint_de}</p>
                </a>
              ))}
            </div>
          ) : !kpiLoading ? (
            <p className="mt-2 text-[11px] text-slate-500">KPI werden nach Portfolio-Laden geladen …</p>
          ) : null}
        </section>
      ) : null}

      {payload ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <KanzleiReviewPlaybookHelper
            variant="full"
            footerHint={
              (payload.attention_queue ?? []).length > 0
                ? `Aktuell ${(payload.attention_queue ?? []).length} Mandant(en) in der Attention-Queue (rechts).`
                : "Keine Mandanten in der Queue – Playbook trotzdem für Stichproben nutzen."
            }
          />
          <section id="kanzlei-kpi-queue" className="min-w-0">
            <AttentionQueuePanel
              items={payload.attention_queue ?? []}
              onMarkReview={(tid) => void markReviewDone(tid)}
              reviewBusyId={reviewBusyId}
            />
          </section>
        </div>
      ) : null}

      {payload ? (
        <section id="kanzlei-kpi-reminders" className="rounded-xl border border-rose-200 bg-rose-50/20 p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-rose-950">Reminders & Follow-ups (Wave 43)</h2>
          <p className="mt-1 text-[11px] text-slate-600">
            Gespeichert in{" "}
            <code className="rounded bg-white px-1">data/advisor-mandant-reminders.json</code> – Auto-Hooks aus
            Kadenz, Lücken und Attention-Queue; manuell ergänzbar. Kein Ticket-System.
          </p>
          <p className="mt-2 text-xs text-slate-700">
            <span className="font-semibold">Heute / überfällig:</span>{" "}
            {payload.reminders_due_today_or_overdue_count} ·{" "}
            <span className="font-semibold">Offen diese Kalenderwoche:</span>{" "}
            {payload.reminders_due_this_week_open_count} ·{" "}
            <span className="font-semibold">Offen gesamt:</span> {payload.open_reminders.length}
          </p>
          <div className="mt-3 grid gap-4 lg:grid-cols-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-rose-800">Heute / überfällig</p>
              {remindersDueUrgent.length === 0 ? (
                <p className="mt-1 text-[11px] text-slate-500">Keine offenen Reminder in dieser Kategorie.</p>
              ) : (
                <ul className="mt-1 space-y-2">
                  {remindersDueUrgent.map((r) => (
                    <ReminderRowItem
                      key={r.reminder_id}
                      r={r}
                      busy={reminderPatchBusyId === r.reminder_id}
                      onDone={() => void patchReminderStatus(r.reminder_id, "done")}
                      onDismiss={() => void patchReminderStatus(r.reminder_id, "dismissed")}
                    />
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                Später diese Woche
              </p>
              {remindersDueWeekNotUrgent.length === 0 ? (
                <p className="mt-1 text-[11px] text-slate-500">Keine weiteren in dieser Woche (außer oben).</p>
              ) : (
                <ul className="mt-1 max-h-48 space-y-2 overflow-y-auto">
                  {remindersDueWeekNotUrgent.map((r) => (
                    <ReminderRowItem
                      key={r.reminder_id}
                      r={r}
                      busy={reminderPatchBusyId === r.reminder_id}
                      onDone={() => void patchReminderStatus(r.reminder_id, "done")}
                      onDismiss={() => void patchReminderStatus(r.reminder_id, "dismissed")}
                    />
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="mt-4 rounded-lg border border-rose-100 bg-white/80 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">Manuell anlegen</p>
            <div className="mt-2 flex flex-wrap items-end gap-2">
              <label className="text-[11px] font-medium text-slate-700">
                Mandant
                <select
                  className="mt-0.5 block max-w-[200px] rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                  value={manualRemTenantId}
                  onChange={(e) => setManualRemTenantId(e.target.value)}
                >
                  {payload.rows.map((row) => (
                    <option key={row.tenant_id} value={row.tenant_id}>
                      {row.mandant_label ?? row.tenant_id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-[11px] font-medium text-slate-700">
                Fällig
                <input
                  type="date"
                  className="mt-0.5 block rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                  value={manualRemDue}
                  onChange={(e) => setManualRemDue(e.target.value)}
                />
              </label>
              <label className="text-[11px] font-medium text-slate-700">
                Art
                <select
                  className="mt-0.5 block rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
                  value={manualRemCat}
                  onChange={(e) => setManualRemCat(e.target.value as "manual" | "follow_up_note")}
                >
                  <option value="follow_up_note">Follow-up (Notiz Pflicht)</option>
                  <option value="manual">Manuell</option>
                </select>
              </label>
              <label className="block min-w-[180px] flex-1 text-[11px] font-medium text-slate-700">
                Notiz
                <input
                  className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-[11px]"
                  value={manualRemNote}
                  onChange={(e) => setManualRemNote(e.target.value)}
                  placeholder={manualRemCat === "follow_up_note" ? "z. B. ISO-Rollen anrufen" : "optional"}
                  maxLength={500}
                />
              </label>
              <button
                type="button"
                disabled={manualRemBusy || !manualRemTenantId || !manualRemDue}
                onClick={() => void submitManualReminder()}
                className="rounded bg-rose-800 px-2 py-1 text-[11px] text-white hover:bg-rose-900 disabled:opacity-50"
              >
                {manualRemBusy ? "…" : "Speichern"}
              </button>
            </div>
          </div>
          <p className="mt-2 text-[10px] text-slate-500">
            API:{" "}
            <code className="rounded bg-white px-1">GET/POST/PATCH /api/internal/advisor/mandant-reminders</code>
          </p>
        </section>
      ) : null}

      {payload ? (
        <section className="rounded-xl border border-cyan-200 bg-cyan-50/30 p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Monatsreport / Sammelreport (Wave 42–45)</h2>
          <p className="mt-1 text-[11px] text-slate-600">
            Portfolio-weiter Überblick für interne Kanzlei-Reviews und Status-Mails. JSON + Markdown über{" "}
            <code className="rounded bg-white px-1">GET /api/internal/advisor/kanzlei-monthly-report</code>.
            Vergleich nutzt optional{" "}
            <code className="rounded bg-white px-1">data/kanzlei-monthly-report-baseline.json</code> (siehe
            Doku). Abschnitt 5 (KPIs):{" "}
            <code className="rounded bg-white px-1">kpi_window_days</code>, abschalten mit{" "}
            <code className="rounded bg-white px-1">kpi=0</code>.
          </p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-xs font-medium text-slate-700">
              Periode (YYYY-MM)
              <input
                className="mt-1 block w-36 rounded-lg border border-slate-300 bg-white px-2 py-1.5 font-mono text-sm"
                value={reportPeriod}
                onChange={(e) => setReportPeriod(e.target.value)}
                placeholder="2026-04"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={reportCompare}
                onChange={(e) => setReportCompare(e.target.checked)}
              />
              Vergleich mit Baseline
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={reportSaveBaseline}
                onChange={(e) => setReportSaveBaseline(e.target.checked)}
              />
              Baseline nach Erzeugung speichern
            </label>
            <button
              type="button"
              disabled={reportLoading}
              onClick={() => void fetchMonthlyReport()}
              className="rounded-lg bg-cyan-800 px-3 py-1.5 text-sm text-white hover:bg-cyan-900 disabled:opacity-50"
            >
              {reportLoading ? "Erzeuge…" : "Monatsreport erstellen"}
            </button>
            <button
              type="button"
              disabled={!reportMd}
              onClick={() => void copyReportMd()}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Markdown kopieren
            </button>
          </div>
          {reportErr ? <p className="mt-2 text-xs text-red-600">{reportErr}</p> : null}
          {reportDto ? (
            <p className="mt-2 font-mono text-[10px] text-slate-500">
              Schema {reportDto.version} · compared_to_baseline={String(reportDto.compared_to_baseline)} · Top{" "}
              {reportDto.section_2_attention_top.length}
            </p>
          ) : null}
          {reportMd ? (
            <pre className="mt-3 max-h-[min(55vh,480px)] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 font-mono text-[11px] leading-relaxed text-slate-800">
              {reportMd}
            </pre>
          ) : null}
        </section>
      ) : null}

      {payload ? (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Partner-Review-Paket (Wave 44–45)</h2>
          <p className="mt-1 text-[11px] text-slate-600">
            Kompaktes Sammelpaket für Partnerrunden und Portfolio-Steuerung (nicht Mandanten-Einzel, nicht
            Board-Pack). Teil C nutzt dieselbe Baseline wie der Monatsreport; Teil E enthält Kanzlei-KPIs
            (Wave 45).{" "}
            <code className="rounded bg-white px-1">GET /api/internal/advisor/partner-review-package</code> ·{" "}
            <code className="rounded bg-white px-1">?format=markdown</code> · optional{" "}
            <code className="rounded bg-white px-1">kpi=0</code>.
          </p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-xs font-medium text-slate-700">
              Top-Mandanten (3–15)
              <input
                type="number"
                min={3}
                max={15}
                className="mt-1 block w-20 rounded-lg border border-slate-300 bg-white px-2 py-1.5 font-mono text-sm"
                value={Number.isFinite(partnerTopN) ? partnerTopN : 8}
                onChange={(e) => {
                  const v = Number.parseInt(e.target.value, 10);
                  setPartnerTopN(Number.isFinite(v) ? v : 8);
                }}
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={partnerCompare}
                onChange={(e) => setPartnerCompare(e.target.checked)}
              />
              Vergleich mit Baseline (Teil C)
            </label>
            <button
              type="button"
              disabled={partnerLoading}
              onClick={() => void fetchPartnerReviewPackage()}
              className="rounded-lg bg-indigo-800 px-3 py-1.5 text-sm text-white hover:bg-indigo-900 disabled:opacity-50"
            >
              {partnerLoading ? "Erzeuge…" : "Partner-Review-Paket erstellen"}
            </button>
            <button
              type="button"
              disabled={!partnerMd}
              onClick={() => void copyPartnerMd()}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Markdown kopieren
            </button>
            <button
              type="button"
              disabled={!partnerMd}
              onClick={() => downloadPartnerMd()}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Als Markdown speichern
            </button>
          </div>
          {partnerErr ? <p className="mt-2 text-xs text-red-600">{partnerErr}</p> : null}
          {partnerDto ? (
            <p className="mt-2 font-mono text-[10px] text-slate-500">
              Schema {partnerDto.meta.version} · compared_to_baseline={String(partnerDto.meta.compared_to_baseline)}{" "}
              · Top {partnerDto.part_b_top_attention.length}
            </p>
          ) : null}
          {partnerMd ? (
            <pre className="mt-3 max-h-[min(50vh,420px)] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 font-mono text-[11px] leading-relaxed text-slate-800">
              {partnerMd}
            </pre>
          ) : null}
        </section>
      ) : null}

      {payload ? (
        <div
          id="kanzlei-kpi-filters"
          className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
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
          <label
            id="kanzlei-kpi-review"
            className="flex cursor-pointer items-center gap-2 text-xs text-slate-700"
          >
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
        <section
          id="kanzlei-kpi-table"
          className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm"
        >
          <table className="min-w-[1180px] w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-3 py-2 font-medium">Mandant</th>
                <th className="px-3 py-2 font-medium">Readiness</th>
                <th className="px-3 py-2 font-medium">Fokus-Säule</th>
                <th className="px-3 py-2 font-medium">Bericht</th>
                <th className="px-3 py-2 font-medium">Offen</th>
                <th className="px-3 py-2 font-medium">Signale</th>
                <th id="kanzlei-kpi-export" className="px-3 py-2 font-medium">
                  Readiness-Export
                </th>
                <th className="px-3 py-2 font-medium">DATEV-ZIP</th>
                <th className="px-3 py-2 font-medium">Review</th>
                <th className="px-3 py-2 font-medium">Reminder</th>
                <th className="px-3 py-2 font-medium">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={11} className="px-3 py-6 text-center text-slate-500">
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
                        {showKeinExportBadge(row) ? (
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
                    <td className="px-3 py-2 align-top text-[10px] text-slate-700">
                      {row.open_reminders_count > 0 ? (
                        <>
                          <div>{formatIsoDe(row.next_reminder_due_at)}</div>
                          <div className="mt-0.5 font-mono text-slate-500">{row.open_reminders_count} offen</div>
                        </>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
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
          Zeitstempel automatisch; Review per Aktion). Reminders:{" "}
          <code className="rounded bg-slate-100 px-1">data/advisor-mandant-reminders.json</code>. Optional
          weiterlesbar: <code className="rounded bg-slate-100 px-1">data/advisor-portfolio-touchpoints.json</code>{" "}
          (Wave 39–45). Schwellen: Review {payload.constants.review_stale_days} Tage, Export{" "}
          {payload.constants.any_export_max_age_days} Tage – siehe Wave 40–43 (
          <code className="rounded bg-slate-100 px-1">docs/advisors/</code>
          ).
        </p>
      ) : null}
    </div>
  );
}

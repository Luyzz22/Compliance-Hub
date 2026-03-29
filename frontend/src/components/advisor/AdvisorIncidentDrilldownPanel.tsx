"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchAdvisorTenantIncidentDrilldown,
  fetchAdvisorTenantIncidentDrilldownCsvBlob,
} from "@/lib/api";
import {
  type AdvisorIncidentDrilldownItem,
  type AdvisorIncidentDrilldownOut,
  type CategoryFocusFilterId,
  SUPPLIER_FILTER_OPTIONS,
  CATEGORY_FOCUS_OPTIONS,
  applyDrilldownFilters,
  isAvailabilityDominant,
  isSafetyDominant,
  mapTenantDrilldownDtoToAdvisorOut,
  type SupplierFilterId,
} from "@/lib/advisorIncidentDrilldownModel";
import { CH_BTN_PRIMARY, CH_BTN_SECONDARY, CH_CARD, CH_SECTION_LABEL, CH_SHELL } from "@/lib/boardLayout";
import { featureGovernanceMaturity } from "@/lib/config";

function FocusBadges({ it }: { it: AdvisorIncidentDrilldownItem }) {
  const s = isSafetyDominant(it);
  const a = isAvailabilityDominant(it);
  return (
    <div className="flex flex-wrap gap-1">
      {s ? (
        <span
          className="rounded bg-amber-100 px-1.5 py-0.5 text-[0.65rem] font-semibold text-amber-950"
          title="Gewichteter Schwerpunkt Sicherheit (OAMI-Logik)"
        >
          Safety
        </span>
      ) : null}
      {a ? (
        <span
          className="rounded bg-sky-100 px-1.5 py-0.5 text-[0.65rem] font-semibold text-sky-950"
          title="Gewichteter Schwerpunkt Verfügbarkeit"
        >
          Verfügbarkeit
        </span>
      ) : null}
      {!s && !a ? (
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.65rem] font-medium text-slate-700">
          Ausgewogen
        </span>
      ) : null}
    </div>
  );
}

function DrilldownTable({
  rows,
  compact,
}: {
  rows: AdvisorIncidentDrilldownItem[];
  compact: boolean;
}) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="min-w-[520px] w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <th className="py-2 pr-2">System</th>
            <th className="py-2 pr-2">Lieferant</th>
            <th className="py-2 pr-2 tabular-nums">Σ</th>
            {!compact ? (
              <>
                <th className="py-2 pr-2 tabular-nums" title="Rohzähler Sicherheit / Verfügbarkeit / Sonstige">
                  S / V / O
                </th>
                <th className="py-2 pr-2 tabular-nums" title="Gewichtete Anteile (normiert)">
                  % S / V
                </th>
              </>
            ) : null}
            <th className="py-2">Fokus</th>
            {!compact ? <th className="py-2">Hinweis</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((it) => (
            <tr key={it.aiSystemId} className="border-b border-slate-100">
              <td className="py-2 pr-2 font-medium text-slate-900">{it.aiSystemName}</td>
              <td className="py-2 pr-2 text-slate-700">{it.supplierSourceLabelDe}</td>
              <td className="py-2 pr-2 tabular-nums text-slate-800">{it.incidentCountTotal}</td>
              {!compact ? (
                <>
                  <td className="py-2 pr-2 tabular-nums text-xs text-slate-600">
                    {it.incidentCountByCategory.safety} / {it.incidentCountByCategory.availability} /{" "}
                    {it.incidentCountByCategory.other}
                  </td>
                  <td className="py-2 pr-2 tabular-nums text-xs text-slate-600">
                    {Math.round(it.weightedShareSafety * 100)} /{" "}
                    {Math.round(it.weightedShareAvailability * 100)}
                  </td>
                </>
              ) : null}
              <td className="py-2">
                <FocusBadges it={it} />
              </td>
              {!compact ? (
                <td className="max-w-[220px] py-2 text-xs text-slate-600" title={it.localOamiHintDe}>
                  {it.localOamiHintDe}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type AdvisorIncidentDrilldownPanelProps = {
  advisorId: string;
  clientTenantId: string;
  /** snapshot: Karte im Governance-Snapshot; full: Detailseite mit Export. */
  variant?: "snapshot" | "full";
};

export function AdvisorIncidentDrilldownPanel({
  advisorId,
  clientTenantId,
  variant = "snapshot",
}: AdvisorIncidentDrilldownPanelProps) {
  const [raw, setRaw] = useState<AdvisorIncidentDrilldownOut | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [supplier, setSupplier] = useState<SupplierFilterId>("all");
  const [focus, setFocus] = useState<CategoryFocusFilterId>("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [csvBusy, setCsvBusy] = useState(false);

  const load = useCallback(async () => {
    if (!featureGovernanceMaturity() || !advisorId) {
      setRaw(null);
      setBusy(false);
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const dto = await fetchAdvisorTenantIncidentDrilldown(advisorId, clientTenantId, 90);
      const mapped = mapTenantDrilldownDtoToAdvisorOut(dto, new Date().toISOString());
      setRaw(mapped);
    } catch (e) {
      setRaw(null);
      setErr(e instanceof Error ? e.message : "Drilldown nicht verfügbar");
    } finally {
      setBusy(false);
    }
  }, [advisorId, clientTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!raw?.items.length) {
      return [];
    }
    return applyDrilldownFilters(raw.items, supplier, focus);
  }, [raw, supplier, focus]);

  const exportCsv = async () => {
    setCsvBusy(true);
    try {
      const blob = await fetchAdvisorTenantIncidentDrilldownCsvBlob(advisorId, clientTenantId, 90);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `incident-drilldown-${clientTenantId.slice(0, 24)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "CSV-Export fehlgeschlagen");
    } finally {
      setCsvBusy(false);
    }
  };

  if (!featureGovernanceMaturity()) {
    return null;
  }

  if (busy && !raw) {
    return variant === "snapshot" ? (
      <section className={CH_CARD} data-testid="advisor-incident-drilldown-loading">
        <p className={CH_SECTION_LABEL}>Incidents nach KI-System und Lieferant</p>
        <p className="mt-2 text-sm text-slate-600">Lade Drilldown…</p>
      </section>
    ) : (
      <div className={CH_SHELL} data-testid="advisor-incident-drilldown-loading">
        <p className="text-sm text-slate-600">Lade Drilldown…</p>
      </div>
    );
  }

  if (err && !raw) {
    return variant === "snapshot" ? (
      <section className={CH_CARD} data-testid="advisor-incident-drilldown-error">
        <p className={CH_SECTION_LABEL}>Incidents nach KI-System und Lieferant</p>
        <p className="mt-2 text-sm text-rose-800">{err}</p>
      </section>
    ) : (
      <div className={CH_SHELL} data-testid="advisor-incident-drilldown-error">
        <p className="text-sm text-rose-800">{err}</p>
      </div>
    );
  }

  if (!raw || raw.items.length === 0) {
    return null;
  }

  const detailHref = `/advisor/clients/${encodeURIComponent(clientTenantId)}/incident-drilldown`;

  const inner = (
    <>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          <span className="font-semibold text-slate-700">Lieferant</span>
          <select
            className="rounded border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900"
            value={supplier}
            onChange={(e) => setSupplier(e.target.value as SupplierFilterId)}
            data-testid="advisor-drilldown-filter-supplier"
          >
            {SUPPLIER_FILTER_OPTIONS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          <span className="font-semibold text-slate-700">Fokus (OAMI)</span>
          <select
            className="rounded border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900"
            value={focus}
            onChange={(e) => setFocus(e.target.value as CategoryFocusFilterId)}
            data-testid="advisor-drilldown-filter-focus"
          >
            {CATEGORY_FOCUS_OPTIONS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className={`${CH_BTN_SECONDARY} text-xs self-start sm:self-auto`}
          onClick={() => void load()}
          data-testid="advisor-drilldown-refresh"
        >
          Aktualisieren
        </button>
      </div>

      <p className="mt-2 text-xs text-slate-500">
        Fenster: {raw.windowDays} Tage · Systeme mit Incidents: {raw.systemsWithIncidents} · Stand:{" "}
        {raw.generatedAt.slice(0, 19).replace("T", " ")} UTC
      </p>

      {filtered.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600" data-testid="advisor-drilldown-empty-filter">
          Keine Zeilen für die gewählten Filter.
        </p>
      ) : (
        <DrilldownTable rows={filtered} compact={variant === "snapshot"} />
      )}

      {variant === "snapshot" ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className={`${CH_BTN_SECONDARY} text-xs`}
            onClick={() => setModalOpen(true)}
            data-testid="advisor-drilldown-open-modal"
          >
            Details anzeigen
          </button>
          <Link href={detailHref} className={`${CH_BTN_SECONDARY} inline-flex items-center text-xs no-underline`}>
            Vollansicht
          </Link>
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className={`${CH_BTN_PRIMARY} text-xs`}
            disabled={csvBusy}
            onClick={() => void exportCsv()}
            data-testid="advisor-drilldown-export-csv"
          >
            {csvBusy ? "Export…" : "Export CSV"}
          </button>
        </div>
      )}
    </>
  );

  return (
    <>
      {variant === "snapshot" ? (
        <section className={CH_CARD} data-testid="advisor-incident-drilldown-section">
          <p className={CH_SECTION_LABEL}>Incidents nach KI-System und Lieferant</p>
          <p className="mt-1 text-xs text-slate-600">
            90-Tage-Überblick zu Laufzeit-Incidents und OAMI-Treibern.
          </p>
          {inner}
        </section>
      ) : (
        <div className={CH_SHELL} data-testid="advisor-incident-drilldown-full">
          <header className="mb-6">
            <p className="text-[0.7rem] font-bold uppercase tracking-[0.14em] text-cyan-800">Berater</p>
            <h1 className="mt-2 text-xl font-bold text-slate-900">Incident-Drilldown</h1>
            <p className="mt-1 font-mono text-sm text-slate-600">{clientTenantId}</p>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Welche KI-Systeme und Lieferanten treiben Laufzeit-Incidents und das operative Monitoring (OAMI)?
              Kurzhinweise folgen der mandantenweiten OAMI-Subtype-Gewichtung.
            </p>
            <div className="mt-3">
              <Link href={`/advisor/clients/${encodeURIComponent(clientTenantId)}/governance-snapshot`} className="text-xs text-cyan-800 underline">
                Zurück zum Governance-Snapshot
              </Link>
            </div>
          </header>
          <div className={CH_CARD}>{inner}</div>
        </div>
      )}

      {modalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="advisor-drilldown-modal-title"
          data-testid="advisor-drilldown-modal"
        >
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
            <h2 id="advisor-drilldown-modal-title" className="text-lg font-bold text-slate-900">
              Incident-Drilldown – Details
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Vollständige Tabelle inkl. Kategoriezählern und Kurzhinweisen.
            </p>
            <DrilldownTable rows={filtered} compact={false} />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className={`${CH_BTN_SECONDARY} text-xs`}
                onClick={() => setModalOpen(false)}
              >
                Schließen
              </button>
              <button
                type="button"
                className={`${CH_BTN_PRIMARY} text-xs`}
                disabled={csvBusy}
                onClick={() => void exportCsv()}
              >
                {csvBusy ? "Export…" : "CSV exportieren"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchAdvisorTenantUsageMetrics,
  fetchTenantUsageMetrics,
  type TenantUsageMetrics,
} from "@/lib/api";
import { CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

function formatLastActive(iso: string | null): string {
  if (!iso) {
    return "Keine Aktivität erfasst";
  }
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

type Props =
  | {
      mode: "tenant";
      tenantId: string;
    }
  | {
      mode: "advisor";
      advisorId: string;
      tenantId: string;
    };

type TenantUsageSummaryProps = Props & {
  /** Ohne äußere Karte (z. B. eingebettet im Advisor-Picker). */
  variant?: "card" | "inline";
};

export function TenantUsageSummary(props: TenantUsageSummaryProps) {
  const variant = props.variant ?? "card";
  const mode = props.mode;
  const tenantId = props.tenantId;
  const advisorId = mode === "advisor" ? props.advisorId : "";
  const [metrics, setMetrics] = useState<TenantUsageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m =
        mode === "tenant"
          ? await fetchTenantUsageMetrics(tenantId)
          : await fetchAdvisorTenantUsageMetrics(advisorId, tenantId);
      setMetrics(m);
    } catch (e) {
      setMetrics(null);
      setError(e instanceof Error ? e.message : "Metriken nicht ladbar.");
    } finally {
      setLoading(false);
    }
  }, [mode, tenantId, advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const tid = tenantId;

  const inner = (
    <>
      {variant === "card" ? (
        <>
          <p className={CH_SECTION_LABEL}>Tenant Usage (30 Tage)</p>
          <p className="mt-1 font-mono text-xs text-slate-600">{tid}</p>
        </>
      ) : (
        <p className="font-mono text-xs text-slate-600">{tid}</p>
      )}

      {error ? (
        <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {error}
          <button
            type="button"
            className="ml-2 text-sm font-semibold text-rose-800 underline"
            onClick={() => void load()}
          >
            Erneut versuchen
          </button>
        </p>
      ) : null}

      {loading ? (
        <p className="mt-3 text-sm text-slate-500">Lade Kennzahlen…</p>
      ) : metrics ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold text-slate-500">Zuletzt aktiv</dt>
            <dd className="text-slate-900">{formatLastActive(metrics.last_active_at)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-500">Board-Views</dt>
            <dd className="tabular-nums text-slate-900">{metrics.board_views_last_30d}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-500">Advisor-Views</dt>
            <dd className="tabular-nums text-slate-900">{metrics.advisor_views_last_30d}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold text-slate-500">Evidence-Uploads</dt>
            <dd className="tabular-nums text-slate-900">{metrics.evidence_uploads_last_30d}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold text-slate-500">Governance-Actions (neu)</dt>
            <dd className="tabular-nums text-slate-900">{metrics.actions_created_last_30d}</dd>
          </div>
        </dl>
      ) : !error ? (
        <p className="mt-3 text-sm text-slate-500">Keine Daten.</p>
      ) : null}
    </>
  );

  if (variant === "inline") {
    return <div aria-label="Mandanten-Nutzung">{inner}</div>;
  }

  return (
    <section className={CH_CARD} aria-label="Mandanten-Nutzung">
      {inner}
    </section>
  );
}

export function AdvisorTenantUsagePicker({
  advisorId,
  tenantIds,
}: {
  advisorId: string;
  tenantIds: string[];
}) {
  const [pickedTenantId, setPickedTenantId] = useState<string | null>(null);
  const fallbackId = tenantIds[0] ?? "";
  const selectedTenantId =
    pickedTenantId !== null && tenantIds.includes(pickedTenantId)
      ? pickedTenantId
      : fallbackId;

  if (!advisorId || tenantIds.length === 0) {
    return (
      <section className={CH_CARD} aria-label="Mandanten-Nutzung">
        <p className={CH_SECTION_LABEL}>Tenant Usage</p>
        <p className="mt-2 text-sm text-slate-600">
          Sobald Mandanten im Portfolio erscheinen, können Nutzungskennzahlen je Mandant geladen
          werden.
        </p>
      </section>
    );
  }

  return (
    <section className={CH_CARD} aria-label="Mandanten-Nutzung">
      <p className={CH_SECTION_LABEL}>Tenant Usage (30 Tage)</p>
      <label className="mt-2 block text-xs font-semibold text-slate-600" htmlFor="usage-tenant">
        Mandant
      </label>
      <select
        id="usage-tenant"
        className="mt-1 w-full max-w-md rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm"
        value={selectedTenantId}
        onChange={(e) => setPickedTenantId(e.target.value)}
      >
        {tenantIds.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
      {selectedTenantId ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <TenantUsageSummary
            mode="advisor"
            advisorId={advisorId}
            tenantId={selectedTenantId}
            variant="inline"
          />
        </div>
      ) : null}
    </section>
  );
}

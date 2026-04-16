import type { GovernanceAuditEventRow } from "@/lib/aiActSelfAssessmentModels";
import { CH_BTN_GHOST, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

export interface AuditTrailPanelProps {
  sectionLabel?: string;
  title?: string;
  rows: GovernanceAuditEventRow[];
  initialLoadError?: string | null;
  onRefresh?: () => void | Promise<void>;
}

/**
 * Audit-Trail-Tabelle für Governance-Workspaces.
 */
export function AuditTrailPanel({
  sectionLabel = "Nachvollziehbarkeit",
  title = "Audit-Trail",
  rows,
  initialLoadError,
  onRefresh,
}: AuditTrailPanelProps) {
  return (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>{sectionLabel}</p>
      <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
      {initialLoadError ? (
        <p className="mt-4 text-sm text-amber-900" role="alert">
          {initialLoadError}
        </p>
      ) : null}
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200/80">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Ereignis</th>
              <th className="px-4 py-3">Nutzer</th>
              <th className="px-4 py-3">Zeitpunkt</th>
              <th className="px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  Keine Events.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.rowKey} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 font-medium text-slate-900">{r.eventType}</td>
                  <td className="px-4 py-3 text-slate-700">{r.actor}</td>
                  <td className="px-4 py-3 text-slate-600">{r.whenDisplay}</td>
                  <td className="max-w-md truncate px-4 py-3 text-slate-600" title={r.details}>
                    {r.details}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {onRefresh ? (
        <button type="button" className={`${CH_BTN_GHOST} mt-4`} onClick={() => void onRefresh()}>
          Audit-Liste aktualisieren
        </button>
      ) : null}
    </article>
  );
}

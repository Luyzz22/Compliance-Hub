"use client";

/**
 * Aktivitätsübersicht aus dem Audit-Trail.
 *
 * Diese Ansicht hieß zuvor "Verarbeitungsverzeichnis (VVT)" und zeigte konstante
 * Platzhalter für Rechtsgrundlage, Aufbewahrungsfrist und technische Maßnahmen mit einem
 * "Art. 30 DSGVO"-Badge. Ein aus Platzhaltern erzeugtes Dokument, das wie ein
 * Verarbeitungsverzeichnis aussieht, ist gegenüber einer Aufsichtsbehörde irreführend –
 * die Angaben sind vom Verantwortlichen zu bestimmen und lassen sich nicht aus
 * Audit-Log-Einträgen ableiten.
 */

type ActivityEntry = {
  action: string;
  entity_types: string[];
  event_count: number;
};

/** Beispielhafte Struktur der API-Antwort von GET /api/v1/audit-logs/activity-export. */
const SAMPLE_ACTIVITY: ActivityEntry[] = [
  { action: "login", entity_types: ["session"], event_count: 128 },
  { action: "role_change", entity_types: ["user_role"], event_count: 6 },
  { action: "update_ai_system", entity_types: ["ai_system"], event_count: 41 },
];

export function AuditActivityExportClient() {
  return (
    <div className="min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <nav className="mb-2 flex items-center gap-1 text-xs">
            <a
              href="/admin/audit-log"
              className="text-xs font-medium text-slate-500 transition hover:text-cyan-700"
            >
              Audit-Log
            </a>
            <span className="select-none text-xs text-slate-300">/</span>
            <span className="text-xs font-semibold text-slate-800">Aktivitätsübersicht</span>
          </nav>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            Audit-Trail · Aggregation
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2rem] sm:leading-tight">
            Aktivitätsübersicht
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
            Aggregation der protokollierten Systemaktivitäten: welche Aktionen auf welchen
            Objekttypen wie häufig stattgefunden haben.
          </p>
        </div>
      </div>

      {/* Abgrenzungshinweis – bewusst prominent */}
      <div className="rounded-2xl border border-amber-300/70 bg-amber-50 p-5">
        <h2 className="text-sm font-semibold text-amber-900">
          Kein Verzeichnis von Verarbeitungstätigkeiten
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-amber-900">
          Diese Übersicht ist <strong>kein</strong> Verzeichnis von Verarbeitungstätigkeiten
          nach Art. 30 DSGVO und kann ein solches nicht ersetzen. Verarbeitungszweck,
          Rechtsgrundlage, Empfängerkategorien, Löschfristen und technisch-organisatorische
          Maßnahmen sind rechtliche Festlegungen des Verantwortlichen. Sie lassen sich nicht
          aus Audit-Log-Einträgen ableiten und werden hier deshalb bewusst nicht ausgewiesen.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-amber-900">
          Ein eigenständiges ROPA-Modul mit Zweck, Rechtsgrundlage, Datenkategorien und
          Aufbewahrungsregeln befindet sich in Vorbereitung.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Protokollierte Aktionsarten
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{SAMPLE_ACTIVITY.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Erfasste Ereignisse
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {SAMPLE_ACTIVITY.reduce((sum, e) => sum + e.event_count, 0)}
          </p>
        </div>
      </div>

      {/* Entries */}
      <div className="space-y-4">
        {SAMPLE_ACTIVITY.map((entry) => (
          <div
            key={entry.action}
            className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40"
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-base font-semibold text-slate-900">{entry.action}</h3>
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold text-slate-700 ring-1 ring-inset ring-slate-200/70">
                {entry.event_count} Ereignisse
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                Betroffene Objekttypen
              </p>
              <p className="mt-0.5 text-sm text-slate-700">{entry.entity_types.join(", ")}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

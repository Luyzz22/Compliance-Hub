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

/**
 * Strukturbeispiel für die Antwort von GET /api/v1/audit-logs/activity-export.
 *
 * Bewusst ohne Ereigniszahlen: Die Vorgängerseite zeigte erfundene Zahlen und
 * Rechtsangaben in einer Aufmachung, die sie wie Mandantendaten aussehen ließ. Solange
 * die Ansicht nicht an die API angebunden ist, darf sie nichts zeigen, was mit echten
 * Auswertungen verwechselt werden kann.
 */
const STRUCTURE_EXAMPLE: Pick<ActivityEntry, "action" | "entity_types">[] = [
  { action: "login", entity_types: ["session"] },
  { action: "role_change", entity_types: ["user_role"] },
  { action: "update_ai_system", entity_types: ["ai_system"] },
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

      {/* Strukturbeispiel — bewusst ohne Zahlen und klar als solches markiert. */}
      <section
        aria-labelledby="structure-example"
        className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5"
      >
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="structure-example" className="text-sm font-semibold text-slate-900">
            Aufbau der Auswertung
          </h2>
          <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.1em] text-slate-700">
            Strukturbeispiel — keine Mandantendaten
          </span>
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Diese Ansicht ist noch nicht an die Auswertungs-API angebunden. Sie zeigt, welche
          Felder{" "}
          <code className="rounded bg-white px-1 py-0.5 text-xs">
            GET /api/v1/audit-logs/activity-export
          </code>{" "}
          liefert: Aktion, betroffene Objekttypen, Ereigniszahl sowie erstes und letztes
          Auftreten. Beispielzahlen werden bewusst nicht dargestellt, damit nichts mit einer
          echten Auswertung Ihres Mandanten verwechselt werden kann.
        </p>
        <ul className="mt-4 space-y-2">
          {STRUCTURE_EXAMPLE.map((entry) => (
            <li
              key={entry.action}
              className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl bg-white px-4 py-3"
            >
              <span className="font-mono text-sm text-slate-900">{entry.action}</span>
              <span className="text-xs text-slate-500">
                Objekttypen: {entry.entity_types.join(", ")}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-slate-600">
          Bis zur Anbindung rufen Sie die vollständige Auswertung direkt über die API ab.
        </p>
      </section>

    </div>
  );
}

"use client";

const PLAYBOOK_STEPS: { title: string; hint: string }[] = [
  {
    title: "Status und Artefakte",
    hint: "Readiness-Ampel prüfen; überfällige Board-/Statusberichte und Export-Kadenz gegen Historie legen.",
  },
  {
    title: "Offene Prüfpunkte",
    hint: "Nach Säule bündeln; Dringlichkeit und Gesprächstermin mit dem Mandanten festlegen.",
  },
  {
    title: "Export bei Bedarf",
    hint: "Mandanten-Readiness oder DATEV-ZIP erzeugen, wenn Unterlagen oder Kadenz es erfordern.",
  },
  {
    title: "Review abschließen",
    hint: "Kanzlei-Review in der Historie speichern; optional kurze Notiz oder nächste Ausführung festhalten.",
  },
];

export type KanzleiPlaybookMandateSnapshot = {
  open_points_count?: number;
  open_points_hoch?: number;
  export_days_since?: number | null;
  review_stale?: boolean;
  any_export_stale?: boolean;
  never_any_export?: boolean;
  board_report_stale?: boolean;
  top_gap_pillar_label_de?: string | null;
  api_fetch_ok?: boolean;
};

function SnapshotLines({ s }: { s: KanzleiPlaybookMandateSnapshot }) {
  const lines: string[] = [];
  if (s.api_fetch_ok === false) {
    lines.push("API: Mandantendaten derzeit unvollständig – Zugriff prüfen.");
  }
  if (typeof s.open_points_count === "number") {
    const h = s.open_points_hoch && s.open_points_hoch > 0 ? `, davon ${s.open_points_hoch} mit hoher Dringlichkeit` : "";
    lines.push(`Offene Prüfpunkte: ${s.open_points_count}${h}.`);
  }
  if (s.never_any_export) {
    lines.push("Letzter Export: noch kein Readiness-/DATEV-Zeitstempel erfasst.");
  } else if (typeof s.export_days_since === "number") {
    lines.push(`Letzter Export (jüngster Readiness/DATEV): vor ${s.export_days_since} Tag(en).`);
  } else if (s.any_export_stale) {
    lines.push("Letzter Export: Kadenz überschritten oder Zeitstempel ungültig.");
  }
  if (s.board_report_stale) {
    lines.push("Board-/Statusbericht: als überfällig geführt.");
  }
  if (s.review_stale) {
    lines.push("Kanzlei-Review: fällig oder noch nicht erfasst.");
  }
  if (s.top_gap_pillar_label_de && lines.length < 6) {
    lines.push(`Aktueller Fokus (größte Lücke): ${s.top_gap_pillar_label_de}.`);
  }
  if (lines.length === 0) return null;
  return (
    <ul className="mt-3 list-inside list-disc space-y-0.5 text-[11px] text-slate-700">
      {lines.map((x) => (
        <li key={x}>{x}</li>
      ))}
    </ul>
  );
}

type Props = {
  variant?: "full" | "compact";
  snapshot?: KanzleiPlaybookMandateSnapshot | null;
  /** Zusatzzeile unterhalb (z. B. Verweis auf Cockpit). */
  footerHint?: string | null;
};

export function KanzleiReviewPlaybookHelper({ variant = "full", snapshot, footerHint }: Props) {
  const compact = variant === "compact";
  return (
    <section
      className={`rounded-xl border border-violet-200 bg-gradient-to-br from-violet-50/90 to-white shadow-sm ${
        compact ? "p-3" : "p-4"
      }`}
    >
      <h2 className={`font-semibold text-violet-950 ${compact ? "text-xs" : "text-sm"}`}>
        Kanzlei-Review-Playbook (Wave 41)
      </h2>
      <p className={`mt-1 text-slate-600 ${compact ? "text-[10px] leading-snug" : "text-xs"}`}>
        Standardablauf für Mandanten, die im Portfolio Aufmerksamkeit haben – ohne Ticketsystem, nur als
        Leitfaden.
      </p>
      <ol className={`mt-3 list-decimal space-y-2 pl-4 text-slate-800 ${compact ? "text-[10px]" : "text-xs"}`}>
        {PLAYBOOK_STEPS.map((step) => (
          <li key={step.title}>
            <span className="font-medium text-slate-900">{step.title}:</span> {step.hint}
          </li>
        ))}
      </ol>
      {snapshot ? <SnapshotLines s={snapshot} /> : null}
      {footerHint ? (
        <p className={`mt-2 text-slate-500 ${compact ? "text-[10px]" : "text-xs"}`}>{footerHint}</p>
      ) : null}
    </section>
  );
}

import Link from "next/link";

export function LegalReleaseGate() {
  return (
    <section className="rounded-xl border border-[var(--mk-warn-100)] bg-[var(--mk-warn-50)] p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--mk-warn-700)]">
        Veröffentlichung gesperrt
      </p>
      <h2 className="mt-2 text-lg font-semibold tracking-tight text-[var(--mk-fg)]">
        Rechtliche Freigabe ausstehend
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--mk-fg-soft)]">
        Diese Instanz veröffentlicht bewusst keine Platzhalter oder erfundenen
        Unternehmensangaben. Vor einem Produktiv-Release müssen die geprüften Angaben über
        die Release-Konfiguration bereitgestellt werden.
      </p>
      <Link
        href="/kontakt"
        className="mk-btn mk-btn--primary mt-5"
      >
        Verantwortliche Stelle kontaktieren
      </Link>
    </section>
  );
}

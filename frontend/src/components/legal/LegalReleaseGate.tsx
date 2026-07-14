import Link from "next/link";

export function LegalReleaseGate() {
  return (
    <section className="rounded-[1.75rem] border border-amber-200 bg-amber-50/70 p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-800">
        Veröffentlichung gesperrt
      </p>
      <h2 className="mt-2 text-lg font-semibold tracking-tight text-slate-950">
        Rechtliche Freigabe ausstehend
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">
        Diese Instanz veröffentlicht bewusst keine Platzhalter oder erfundenen
        Unternehmensangaben. Vor einem Produktiv-Release müssen die geprüften Angaben über
        die Release-Konfiguration bereitgestellt werden.
      </p>
      <Link
        href="/kontakt"
        className="mt-5 inline-flex rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
      >
        Verantwortliche Stelle kontaktieren
      </Link>
    </section>
  );
}

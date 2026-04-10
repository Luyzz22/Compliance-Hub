import type { Metadata } from "next";
import React from "react";

import { CH_CARD, CH_SHELL } from "@/lib/boardLayout";

export const metadata: Metadata = {
  title: "AGB · Compliance Hub",
};

export default function AgbPage() {
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Allgemeine Geschäftsbedingungen
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Nutzungsbedingungen der Compliance Hub Plattform.
        </p>
      </header>
      <div className={CH_CARD}>
        <p className="text-sm leading-relaxed text-slate-600">
          <strong>Hinweis:</strong> Bitte ersetzen Sie diesen Platzhalter durch Ihre
          vollständigen Allgemeinen Geschäftsbedingungen. Diese sollten Vertragsgegenstand,
          Leistungsbeschreibung, Vergütung, Haftung, Laufzeit und Kündigung regeln.
        </p>
      </div>
    </div>
  );
}

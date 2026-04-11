import type { Metadata } from "next";
import React from "react";

import { CH_CARD, CH_SHELL } from "@/lib/boardLayout";

export const metadata: Metadata = {
  title: "Datenschutzerklärung · Compliance Hub",
};

export default function DatenschutzPage() {
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Datenschutzerklärung
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Informationen gemäß DSGVO Art. 13 / Art. 14.
        </p>
      </header>
      <div className={CH_CARD}>
        <p className="text-sm leading-relaxed text-slate-600">
          <strong>Hinweis:</strong> Bitte ersetzen Sie diesen Platzhalter durch Ihre
          vollständige Datenschutzerklärung gemäß DSGVO Art. 13 / Art. 14. Diese muss
          Verantwortlichen, Zweck und Rechtsgrundlage der Verarbeitung,
          Empfängerkategorien, Speicherdauer, Betroffenenrechte und ggf. den
          Datenschutzbeauftragten benennen.
        </p>
      </div>
    </div>
  );
}

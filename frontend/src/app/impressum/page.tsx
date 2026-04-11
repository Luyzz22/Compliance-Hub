import type { Metadata } from "next";
import React from "react";

import { CH_CARD, CH_SHELL } from "@/lib/boardLayout";

export const metadata: Metadata = {
  title: "Impressum · Compliance Hub",
};

export default function ImpressumPage() {
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Impressum
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Angaben gemäß § 5 TMG / § 5a UWG.
        </p>
      </header>
      <div className={CH_CARD}>
        <p className="text-sm leading-relaxed text-slate-600">
          <strong>Hinweis:</strong> Bitte ersetzen Sie diesen Platzhalter durch Ihren
          vollständigen Impressumstext gemäß TMG § 5 / § 5a UWG. Dieser muss Name,
          Anschrift, Kontaktdaten, Handelsregister, USt-IdNr. und ggf. die zuständige
          Aufsichtsbehörde enthalten.
        </p>
      </div>
    </div>
  );
}

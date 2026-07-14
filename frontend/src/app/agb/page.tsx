import type { Metadata } from "next";
import React from "react";

import { LegalReleaseGate } from "@/components/legal/LegalReleaseGate";
import { CH_SHELL } from "@/lib/boardLayout";

export const metadata: Metadata = {
  title: "Vertragsbedingungen · Compliance Hub",
  robots: { index: false, follow: false },
};

export default function AgbPage() {
  return (
    <div className={CH_SHELL}>
      <header className="mb-8 border-b border-slate-200/80 pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Vertragsbedingungen
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
          Geprüfte Bedingungen für die Compliance Hub Plattform.
        </p>
      </header>
      <LegalReleaseGate />
    </div>
  );
}

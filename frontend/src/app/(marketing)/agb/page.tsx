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
    <div className={`mk-container mk-section ${CH_SHELL}`}>
      <header className="mb-8 border-b border-[var(--mk-bd)] pb-8">
        <p className="mk-eyebrow">
          Rechtliches
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--mk-fg)]">
          Vertragsbedingungen
        </h1>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-[var(--mk-fg-muted)]">
          Geprüfte Bedingungen für die Compliance Hub Plattform.
        </p>
      </header>
      <LegalReleaseGate />
    </div>
  );
}

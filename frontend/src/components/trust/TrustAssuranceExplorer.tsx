"use client";

import React, { useState } from "react";

const assuranceViews = [
  {
    id: "public-release",
    label: "Public Release",
    status: "Produktiv · stateless",
    title: "Klar begrenzter öffentlicher Scope.",
    description:
      "Die öffentliche Website ist von der Enterprise-Datenebene getrennt. Sie bietet Produktinformation und direkten E-Mail-Kontakt, aber keine Anmeldung oder lokale Lead-Speicherung.",
    controls: [
      "Nonce-basierte Content Security Policy",
      "Keine zustandsbehafteten Daten-APIs",
      "Legal- und Privacy-Freigabe als Build-Gate",
    ],
  },
  {
    id: "enterprise-boundary",
    label: "Enterprise Boundary",
    status: "Evidenzpflichtig",
    title: "Enterprise-Funktionen bleiben fail-closed.",
    description:
      "Identität, Tenant-Isolation, Datenregion und Wiederherstellung werden erst nach dokumentierter Betriebsfreigabe aktiviert. Ein UI-Status ersetzt keinen technischen Nachweis.",
    controls: [
      "Microsoft Entra ID und Conditional Access",
      "Azure-Datenebene und Tenant-Isolation",
      "Backup-, Restore- und Retention-Evidence",
    ],
  },
  {
    id: "governance-model",
    label: "Governance Model",
    status: "Im Produkt modelliert",
    title: "Regelwerke in einem Kontrollmodell verbinden.",
    description:
      "EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO werden auf gemeinsame Controls und Evidence-Pfade abgebildet. Das unterstützt Reviews, ist aber keine Zertifizierung.",
    controls: [
      "Gemeinsame Control- und Evidence-Struktur",
      "Owner-, Review- und Maßnahmenkontext",
      "Menschliche Freigabe bleibt maßgeblich",
    ],
  },
] as const;

export function TrustAssuranceExplorer() {
  const [active, setActive] = useState(0);
  const view = assuranceViews[active];

  return (
    <section
      className="mk-stage overflow-hidden rounded-[12px] border border-[var(--mk-bd)]"
      aria-labelledby="assurance-explorer-title"
    >
      <div className="grid lg:grid-cols-[0.78fr_1.22fr]">
        <div className="border-b border-[var(--mk-bd)] p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <p className="mk-eyebrow">
            Assurance Explorer
          </p>
          <h2
            id="assurance-explorer-title"
            className="mt-3 text-2xl font-semibold tracking-[-0.035em] text-white"
          >
            Status statt Marketing-Behauptung.
          </h2>
          <p className="mt-3 text-sm leading-6 text-[var(--mk-fg-muted)]">
            Wählen Sie eine Ebene und sehen Sie, was produktiv aktiv, modelliert oder noch
            evidenzpflichtig ist.
          </p>
          <div className="mt-6 grid gap-2" role="group" aria-label="Assurance-Ebenen">
            {assuranceViews.map((item, index) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={index === active}
                onClick={() => setActive(index)}
                className={`flex items-center justify-between rounded-xl px-4 py-3 text-left text-sm font-semibold transition ${
                  index === active
                    ? "bg-[var(--mk-cta)] text-[var(--mk-cta-ink)]"
                    : "border border-[var(--mk-bd)] bg-[var(--mk-panel)] text-[var(--mk-fg-muted)] hover:border-[var(--mk-bd-strong)] hover:text-white"
                }`}
              >
                {item.label}
                <span className="font-mono text-xs opacity-55">0{index + 1}</span>
              </button>
            ))}
          </div>
        </div>

        <article
          aria-live="polite"
          className="flex min-h-[24rem] flex-col justify-center p-6 sm:p-10 lg:p-12"
        >
          <div className="mk-chip mk-chip--ok w-fit">
            <span className="mk-chip__dot" aria-hidden />
            {view.status}
          </div>
          <h3 className="mt-5 max-w-2xl text-2xl font-semibold tracking-[-0.035em] text-white sm:text-3xl">
            {view.title}
          </h3>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--mk-fg-muted)] sm:text-base">
            {view.description}
          </p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-3">
            {view.controls.map((control) => (
              <li
                key={control}
                className="rounded-[8px] border border-[var(--mk-bd)] bg-[var(--mk-panel)] p-4 text-sm leading-6 text-[var(--mk-fg-soft)]"
              >
                <span className="mb-3 block h-px w-8 bg-[var(--mk-brass)]" aria-hidden />
                {control}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}

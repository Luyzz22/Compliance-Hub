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
      className="overflow-hidden rounded-[2rem] border border-slate-200/80 bg-[#07111f] text-white shadow-2xl shadow-slate-950/15"
      aria-labelledby="assurance-explorer-title"
    >
      <div className="grid lg:grid-cols-[0.78fr_1.22fr]">
        <div className="border-b border-white/10 p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-cyan-300">
            Assurance Explorer
          </p>
          <h2
            id="assurance-explorer-title"
            className="mt-3 text-2xl font-semibold tracking-[-0.035em] text-white"
          >
            Status statt Marketing-Behauptung.
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">
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
                    ? "bg-white text-slate-950 shadow-lg"
                    : "bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white"
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
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-300" aria-hidden />
            {view.status}
          </div>
          <h3 className="mt-5 max-w-2xl text-2xl font-semibold tracking-[-0.035em] text-white sm:text-3xl">
            {view.title}
          </h3>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {view.description}
          </p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-3">
            {view.controls.map((control) => (
              <li
                key={control}
                className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-slate-200"
              >
                <span className="mb-3 block h-1.5 w-8 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" aria-hidden />
                {control}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}

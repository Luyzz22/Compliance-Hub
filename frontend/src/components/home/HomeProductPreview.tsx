"use client";

import React, { useState } from "react";

const views = [
  {
    id: "controls",
    label: "Control Graph",
    title: "Pflicht und Verantwortlichkeit im selben Kontext",
    body: "Ein Control bleibt mit System, Regelwerk, Status und Owner verbunden.",
    fields: [
      ["System", "Registrierter AI Use Case"],
      ["Pflicht", "Anwendbarer Kontrollpunkt"],
      ["Owner", "Verantwortliche Rolle"],
      ["Status", "Offen bis zur Prüfung"],
    ],
    outcome: "Offene Controls bleiben sichtbar und zuweisbar.",
  },
  {
    id: "evidence",
    label: "Evidence Review",
    title: "Nachweis mit Herkunft und Review-Kontext",
    body: "Evidence wird nicht nur abgelegt, sondern mit Quelle und Prüfung verbunden.",
    fields: [
      ["Quelle", "Referenzierter Nachweispfad"],
      ["Owner", "Zuständige Fachrolle"],
      ["Reviewer", "Getrennte Prüferrolle"],
      ["Review", "Datum und nächste Fälligkeit"],
    ],
    outcome: "Fehlende Evidence kann nicht als verifiziert erscheinen.",
  },
  {
    id: "decision",
    label: "Board Context",
    title: "Risiko, Maßnahme und Entscheidung zusammenführen",
    body: "Das Board erhält verdichteten Kontext, ohne dass die Plattform die Freigabe übernimmt.",
    fields: [
      ["Risiko", "Nachvollziehbare Einordnung"],
      ["Abhängigkeit", "Betroffene Controls und Systeme"],
      ["Maßnahme", "Owner, Frist und Status"],
      ["Entscheidung", "Menschlich freigegeben"],
    ],
    outcome: "Automatische Rechts- und Freigabeentscheidungen bleiben ausgeschlossen.",
  },
] as const;

export function HomeProductPreview() {
  const [active, setActive] = useState(0);
  const view = views[active];

  return (
    <div
      className="overflow-hidden rounded-2xl border border-[var(--ch-border-strong)] bg-[var(--ch-ink)] text-white shadow-[0_30px_90px_rgba(31,35,40,0.16)]"
      role="region"
      aria-label="Illustrative Produktlogik"
    >
      <div className="flex items-center justify-between border-b border-white/[0.12] px-5 py-4 sm:px-7">
        <p className="text-sm font-semibold tracking-[-0.01em]">Compliance Hub</p>
        <p className="text-xs text-slate-400">Illustrative Produktlogik</p>
      </div>

      <div className="grid sm:grid-cols-[0.36fr_0.64fr]">
        <div
          className="grid border-b border-white/[0.12] sm:border-b-0 sm:border-r"
          role="tablist"
          aria-label="Governance-Perspektiven"
        >
          {views.map((item, index) => (
            <button
              key={item.id}
              id={`product-tab-${item.id}`}
              type="button"
              role="tab"
              aria-selected={index === active}
              aria-controls="product-view"
              onClick={() => setActive(index)}
              className={`min-h-14 border-b border-white/[0.12] px-5 text-left text-xs font-semibold transition-colors last:border-b-0 sm:min-h-20 sm:px-7 ${
                index === active
                  ? "bg-white text-[var(--ch-ink)]"
                  : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div
          id="product-view"
          role="tabpanel"
          aria-labelledby={`product-tab-${view.id}`}
          className="min-w-0 px-5 py-7 sm:px-8 sm:py-9"
        >
          <h3 className="max-w-lg text-2xl font-semibold leading-tight tracking-[-0.03em] sm:text-3xl">
            {view.title}
          </h3>
          <p className="mt-3 max-w-lg text-sm leading-6 text-slate-300">{view.body}</p>

          <dl className="mt-7 border-t border-white/[0.16]">
            {view.fields.map(([term, description]) => (
              <div
                key={term}
                className="grid gap-1 border-b border-white/[0.12] py-3.5 sm:grid-cols-[6rem_1fr] sm:gap-5"
              >
                <dt className="font-mono text-xs font-semibold text-blue-300">{term}</dt>
                <dd className="text-xs leading-5 text-slate-300">{description}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-6 border-l border-blue-400 pl-4 text-sm font-medium leading-6 text-white">
            {view.outcome}
          </p>
        </div>
      </div>
    </div>
  );
}

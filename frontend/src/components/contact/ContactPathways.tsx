"use client";

import React, { useState } from "react";

import { PUBLIC_CONTACT_EMAIL } from "@/lib/publicContact";

const pathways = [
  {
    id: "executive",
    label: "Executive Briefing",
    title: "Board- und Governance-Perspektive",
    description:
      "Für Zielbild, Entscheidungsfelder, Reporting und eine belastbare Governance-Roadmap.",
    subject: "Compliance Hub – Executive Briefing",
    prompt:
      "Ich interessiere mich für ein Executive Briefing zu AI Governance und Board Readiness.",
  },
  {
    id: "security",
    label: "Security Review",
    title: "Architektur- und Kontrollprüfung",
    description:
      "Für Identity, Datenebene, Tenant-Isolation, Betriebsnachweise und Trust-Fragen.",
    subject: "Compliance Hub – Security Review",
    prompt:
      "Ich interessiere mich für einen Security Review der Compliance-Hub-Architektur.",
  },
  {
    id: "integration",
    label: "Integration Workshop",
    title: "Einbettung in Ihre Tool-Landschaft",
    description:
      "Für Azure, GRC, DMS, Ticketing, SIEM und kontrollierte AI-Integrationen.",
    subject: "Compliance Hub – Integration Workshop",
    prompt:
      "Ich interessiere mich für einen Workshop zur Integration von Compliance Hub.",
  },
] as const;

function mailtoHref(subject: string, prompt: string): string {
  const body = `${prompt}\n\nUnternehmen:\nAnsprechpartner:\nBevorzugter Gesprächstermin:\n\nBitte keine vertraulichen Mandanten- oder besonderen personenbezogenen Daten per E-Mail senden.`;
  return `mailto:${PUBLIC_CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function ContactPathways() {
  const [active, setActive] = useState(0);
  const pathway = pathways[active];

  return (
    <section className="max-w-5xl overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white shadow-[0_32px_100px_rgba(7,17,31,0.11)]">
      <div className="grid lg:grid-cols-[1fr_0.9fr]">
        <div className="p-6 sm:p-8 lg:p-10">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Gespräch auswählen
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-3xl">
            Welcher Einstieg passt zu Ihrem Ziel?
          </h2>
          <div className="mt-7 grid gap-3" role="group" aria-label="Gesprächsformat">
            {pathways.map((item, index) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={index === active}
                onClick={() => setActive(index)}
                className={`rounded-2xl border p-4 text-left transition ${
                  index === active
                    ? "border-slate-950 bg-slate-950 text-white shadow-lg"
                    : "border-slate-200 bg-slate-50/70 text-slate-700 hover:border-slate-300 hover:bg-white"
                }`}
              >
                <span className="text-sm font-semibold">{item.label}</span>
                <span className={`mt-1 block text-xs leading-5 ${index === active ? "text-slate-300" : "text-slate-500"}`}>
                  {item.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col justify-center border-t border-slate-200/80 bg-gradient-to-br from-slate-50 to-cyan-50/50 p-6 sm:p-8 lg:border-l lg:border-t-0 lg:p-10">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#07111f] font-mono text-xs font-semibold text-white shadow-lg" aria-hidden>
            0{active + 1}
          </div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
            {pathway.label}
          </p>
          <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
            {pathway.title}
          </h3>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            Der Public Release speichert keine Formulardaten. Die vorbereitete Nachricht wird
            ausschließlich in Ihrem E-Mail-Programm geöffnet.
          </p>
          <a
            href={mailtoHref(pathway.subject, pathway.prompt)}
            className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-[#07111f] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
          >
            Nachricht vorbereiten
          </a>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Direkter Kontakt: {PUBLIC_CONTACT_EMAIL}
          </p>
        </div>
      </div>
    </section>
  );
}

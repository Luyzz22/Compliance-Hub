"use client";

import React, { useState } from "react";

import { PUBLIC_CONTACT_EMAIL } from "@/lib/publicContact";

import { IconArrowRight } from "./ui/Icons";
import { StatusChip } from "./ui/Primitives";

const PATHWAYS = [
  {
    id: "governance",
    label: "Governance-Demo",
    audience: "Compliance, AI Owner, ISMS",
    title: "Der Ablauf an Ihrem Geltungsbereich",
    description:
      "Register, Klassifizierung, Control Mapping und Evidenz an einem System aus Ihrem Haus.",
    agenda: [
      "Geltungsbereich und anwendbare Regelwerke einordnen",
      "Ein KI-System oder ein NIS2-Risiko gemeinsam durchspielen",
      "Control Mapping und Nachweisführung ansehen",
      "Nächste Schritte und Aufwand realistisch abschätzen",
    ],
    subject: "Compliance Hub – Governance-Demo",
    prompt:
      "Ich interessiere mich für eine Governance-Demo zu EU AI Act, NIS2 und ISO-Anforderungen.",
  },
  {
    id: "board",
    label: "Executive Briefing",
    audience: "Geschäftsführung, Beirat",
    title: "Entscheidungssicht statt Werkzeugführung",
    description:
      "Board-Report, Readiness-Kennzahlen und Entscheidungsbedarf aus Sicht der Leitungsebene.",
    agenda: [
      "Welche Kennzahlen tragen eine Board-Entscheidung",
      "Verantwortung der Leitungsebene nach NIS2 Art. 20",
      "Berichtsformat und Turnus festlegen",
      "Zielbild und Umsetzungsschritte skizzieren",
    ],
    subject: "Compliance Hub – Executive Briefing",
    prompt:
      "Ich interessiere mich für ein Executive Briefing zu Governance-Reporting und Board Readiness.",
  },
  {
    id: "advisor",
    label: "Partner-Demo",
    audience: "Kanzleien, Beratungen",
    title: "Mandantenbetrieb und Portfoliosicht",
    description:
      "Mandantenräume, Templates, White-Label-Reports und Exportwege für die Mandantenübergabe.",
    agenda: [
      "Portfoliosicht über mehrere Mandate",
      "Rollen- und Trennungsmodell zwischen Kanzlei und Mandant",
      "Assessment-Templates und Reportlayout",
      "Exportwege und Partnermodell",
    ],
    subject: "Compliance Hub – Partner-Demo",
    prompt:
      "Ich interessiere mich für eine Partner-Demo zur mandantenfähigen Betreuung.",
  },
  {
    id: "security",
    label: "Security & Architektur",
    audience: "IT-Sicherheit, Datenschutz",
    title: "Isolation, Zugriffe, Protokollierung",
    description:
      "Architektur, Mandantenisolation, Identitätsanbindung, Aufbewahrung und Betriebsnachweise.",
    agenda: [
      "Mandantenisolation und Datenbankkontrollen",
      "SSO-Anbindung und Rollenübernahme",
      "Protokollierung, Aufbewahrung und Löschung",
      "Hosting-Region und Betriebsmodell",
    ],
    subject: "Compliance Hub – Security Review",
    prompt:
      "Ich interessiere mich für eine Architektur- und Sicherheitsprüfung von Compliance Hub.",
  },
] as const;

function mailtoHref(subject: string, prompt: string): string {
  const body = [
    prompt,
    "",
    "Unternehmen:",
    "Rolle / Ansprechpartner:",
    "Betroffene Regelwerke:",
    "Bevorzugter Termin:",
    "",
    "Bitte keine vertraulichen Mandanten- oder besonderen personenbezogenen Daten per E-Mail senden.",
  ].join("\n");
  return `mailto:${PUBLIC_CONTACT_EMAIL}?subject=${encodeURIComponent(
    subject,
  )}&body=${encodeURIComponent(body)}`;
}

/**
 * Auswahl des Gesprächsformats. Im rein öffentlichen Release werden keine
 * Formulardaten verarbeitet — die Nachricht wird im E-Mail-Programm vorbereitet.
 */
export function DemoRequestPathways() {
  const [active, setActive] = useState(0);
  const pathway = PATHWAYS[active];

  return (
    <div className="mk-card overflow-hidden">
      <div className="grid lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="border-b border-[var(--mk-bd)] p-5 lg:border-b-0 lg:border-r">
          <p className="mk-label">Gesprächsformat wählen</p>
          <ul className="mt-3 grid gap-2" role="group" aria-label="Gesprächsformat">
            {PATHWAYS.map((item, index) => {
              const selected = index === active;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setActive(index)}
                    className={`w-full rounded-[10px] border px-3.5 py-3 text-left transition-colors ${
                      selected
                        ? "border-[var(--mk-accent-400)] bg-[var(--mk-accent-50)]"
                        : "border-[var(--mk-bd)] bg-white hover:border-[var(--mk-bd-strong)]"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="text-[0.875rem] font-semibold text-[var(--mk-fg)]">
                        {item.label}
                      </span>
                      <IconArrowRight
                        className={`h-3.5 w-3.5 shrink-0 ${
                          selected
                            ? "text-[var(--mk-accent-600)]"
                            : "text-[var(--mk-fg-faint)]"
                        }`}
                      />
                    </span>
                    <span className="mt-1 block text-[0.75rem] leading-relaxed text-[var(--mk-fg-muted)]">
                      {item.description}
                    </span>
                    <span className="mt-1.5 block text-[0.6875rem] text-[var(--mk-fg-faint)]">
                      Für: {item.audience}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="mk-fade-swap flex flex-col justify-between bg-[var(--mk-slate-50)] p-5">
          <div>
            <StatusChip tone="info" dot={false}>
              {pathway.label}
            </StatusChip>
            <h3 className="mk-h3 mt-3">{pathway.title}</h3>
            <p className="mk-label mt-4">Ablauf · 45 Minuten</p>
            <ol className="mt-2.5 space-y-2">
              {pathway.agenda.map((item, index) => (
                <li
                  key={item}
                  className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-soft)]"
                >
                  <span className="mk-num text-[0.6875rem] font-bold text-[var(--mk-accent-600)]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-6">
            <a href={mailtoHref(pathway.subject, pathway.prompt)} className="mk-btn mk-btn--primary">
              Nachricht vorbereiten
            </a>
            <p className="mt-3 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
              Diese Website verarbeitet keine Formulardaten. Die vorbereitete Nachricht
              wird ausschließlich in Ihrem E-Mail-Programm geöffnet. Direkter Kontakt:{" "}
              {PUBLIC_CONTACT_EMAIL}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

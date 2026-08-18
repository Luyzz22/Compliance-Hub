import type { Metadata } from "next";
import React from "react";

import { CTASection, OutcomeStrip } from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { IntegrationArchitecture } from "@/components/marketing/visuals/IntegrationArchitecture";
import { INTEGRATION_GROUPS } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "Integrationen",
  description:
    "SAP S/4HANA, SAP BTP, Microsoft Dynamics, DATEV-nahe Exporte, Entra ID, SAML 2.0, SAP IAS, SIEM, Jira, ServiceNow, Webhooks, n8n sowie Azure OpenAI, Anthropic, OpenAI, Vertex AI, Snowflake und Databricks.",
  alternates: { canonical: MARKETING_ROUTES.integrations },
};

const OUTCOMES = [
  {
    title: "Keine zweite Datenhaltung",
    detail:
      "Stammdaten bleiben im führenden System. Compliance Hub referenziert sie, statt sie zu duplizieren.",
  },
  {
    title: "Maßnahmen im gewohnten Werkzeug",
    detail:
      "Aufgaben landen in Jira oder ServiceNow und behalten dabei ihren Regelwerks- und Nachweisbezug.",
  },
  {
    title: "Anbindung bleibt dokumentiert",
    detail:
      "Richtung, Umfang und Zweck jeder Verbindung werden je Installation festgelegt und im Audit Trail geführt.",
  },
];

const PATTERNS: [string, string, string][] = [
  [
    "Lesender Abgleich",
    "Stammdaten, Organisationsstruktur, Assets",
    "Regelmäßiger Import aus ERP, CMDB oder Verzeichnisdienst. Compliance Hub schreibt nicht zurück.",
  ],
  [
    "Beidseitige Synchronisation",
    "Maßnahmen und Vorgänge",
    "Maßnahmen werden als Vorgang angelegt; Statusänderungen fließen zurück in den Governance-Stand.",
  ],
  [
    "Ereignisgesteuert",
    "Vorfälle, Freigaben, Fristen",
    "Webhooks und n8n-Abläufe reagieren auf Ereignisse, ohne dass jemand ein Portal beobachten muss.",
  ],
  [
    "Strukturierter Export",
    "Berichte, Dossiers, Kanzleiübergabe",
    "PDF, CSV und JSON mit Inhaltsverzeichnis, Zeitstempel und Prüfsumme.",
  ],
];

export default function IntegrationsPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">Integrationen</p>
            <h1 className="mk-h1 mt-4">
              Governance dort, wo Ihre Prozesse bereits laufen.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Compliance Hub ersetzt kein ERP, kein Ticketsystem und kein Verzeichnis. Es
              verbindet, was dort ohnehin entsteht, mit den Nachweisen, die verlangt
              werden — lesend, schreibend oder ereignisgesteuert.
            </p>
          </div>
        </div>
      </section>

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Architektur */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="architektur"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Architektur"
              title="Datenquellen, Governance Layer, Outputs."
              lead="Die Frage ist nicht, welche Logos an einer Wand hängen, sondern an welcher Stelle die Plattform in Ihre Landschaft eingreift."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9">
              <IntegrationArchitecture />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Gruppen */}
      <section className="mk-section" id="systeme">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Systemlandschaft"
              title="Vier Bereiche, an denen Governance andockt."
              lead="Jede Anbindung hat einen fachlichen Zweck. Was nicht gebraucht wird, wird auch nicht verbunden."
            />
          </Reveal>
          <div className="mt-9 grid gap-4 md:grid-cols-2">
            {INTEGRATION_GROUPS.map((group, index) => (
              <Reveal key={group.id} delay={(index % 2) as 0 | 1}>
                <section
                  id={group.id}
                  className="mk-card h-full scroll-mt-28 p-5"
                  aria-labelledby={`${group.id}-title`}
                >
                  <h3 id={`${group.id}-title`} className="mk-h3">
                    {group.title}
                  </h3>
                  <p className="mt-2.5 text-[0.875rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {group.purpose}
                  </p>
                  <ul className="mt-4 divide-y divide-[var(--mk-bd)] border-y border-[var(--mk-bd)]">
                    {group.items.map((item) => (
                      <li
                        key={item.name}
                        className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 py-2.5"
                      >
                        <span className="text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                          {item.name}
                        </span>
                        <span className="text-[0.75rem] text-[var(--mk-fg-muted)]">
                          {item.note}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Anbindungsmuster */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="anbindungsmuster"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Anbindungsmuster"
              title="Vier Wege, mehr braucht es selten."
              lead="Ob mit Standardkonnektor oder ohne: Der Weg in die Plattform ist in jedem Fall beschrieben und nachvollziehbar."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 overflow-hidden rounded-[14px] border border-[var(--mk-bd)] bg-white">
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">Muster</th>
                      <th scope="col">Typischer Gegenstand</th>
                      <th scope="col">Funktionsweise</th>
                    </tr>
                  </thead>
                  <tbody>
                    {PATTERNS.map(([pattern, subject, detail]) => (
                      <tr key={pattern}>
                        <td className="whitespace-nowrap font-semibold text-[var(--mk-fg)]">
                          {pattern}
                        </td>
                        <td className="whitespace-nowrap text-[var(--mk-fg-soft)]">
                          {subject}
                        </td>
                        <td className="text-[var(--mk-fg-muted)]">{detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>
          <div className="mt-6 flex flex-wrap gap-2">
            <StatusChip tone="info" dot={false}>
              REST-API
            </StatusChip>
            <StatusChip tone="info" dot={false}>
              Webhooks
            </StatusChip>
            <StatusChip tone="info" dot={false}>
              CSV-Import
            </StatusChip>
            <StatusChip tone="info" dot={false}>
              SCIM-nahe Rollenübernahme
            </StatusChip>
            <StatusChip tone="info" dot={false}>
              SIEM-Weiterleitung
            </StatusChip>
          </div>
          <p className="mt-5 max-w-3xl text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Verfügbarkeit und Umfang einzelner Anbindungen werden je Installation
            festgelegt. Wir sagen keine Konnektoren zu, die im konkreten Projekt nicht
            geprüft und freigegeben sind.
          </p>
        </div>
      </section>

      <CTASection
        title="Prüfen wir Ihre Systemlandschaft konkret."
        lead="Bringen Sie Ihre ERP-, Identity- und Workflow-Landschaft mit. Wir ordnen ein, welche Anbindung sinnvoll ist und welche nicht gebraucht wird."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.security}
        secondaryLabel="Sicherheit & Architektur"
      />
    </>
  );
}

import React from "react";

import {
  IconBoard,
  IconDocument,
  IconEvidence,
  IconFlow,
  IconMapping,
  IconPlug,
  IconRegistry,
  IconShield,
  IconTenants,
} from "../ui/Icons";

const SOURCES = [
  { name: "SAP S/4HANA · SAP BTP", note: "Organisation, Prozesse, Stammdaten" },
  { name: "Jira · ServiceNow", note: "Maßnahmen und Changes" },
  { name: "Microsoft Entra ID", note: "Identitäten, Gruppen, SSO" },
  { name: "DMS & Dateiablagen", note: "Bestehende Nachweise" },
  { name: "LLM-Dienste", note: "Registrierte Modellnutzung" },
  { name: "CSV · REST-API · Webhooks", note: "Alles ohne Standardkonnektor" },
];

const LAYER = [
  { name: "Inventory", note: "KI-Systeme, Assets, Anbieter", Icon: IconRegistry },
  { name: "Controls", note: "Ein Kontrollmodell, mehrere Regime", Icon: IconMapping },
  { name: "Evidence", note: "Version, Herkunft, Review-Zyklus", Icon: IconEvidence },
  { name: "Risk", note: "Bewertung, Priorität, Maßnahme", Icon: IconShield },
  { name: "Audit Trail", note: "Nachvollziehbare Änderungshistorie", Icon: IconFlow },
];

const OUTPUTS = [
  { name: "Board Report", note: "Lage und Entscheidungsbedarf", Icon: IconBoard },
  { name: "Audit-Dossier", note: "Nachweise für die Prüfung", Icon: IconDocument },
  { name: "Action Plan", note: "Maßnahmen mit Owner und Frist", Icon: IconFlow },
  { name: "Kanzlei-Export", note: "Strukturierte Mandantenübergabe", Icon: IconTenants },
];

function Arrow({ label }: { label: string }) {
  return (
    <div
      aria-hidden
      className="flex items-center justify-center py-2 lg:h-full lg:py-0"
    >
      <svg
        viewBox="0 0 32 12"
        width="32"
        height="12"
        className="rotate-90 text-[var(--mk-accent-400)] lg:rotate-0"
      >
        <title>{label}</title>
        <path
          d="M1 6h24"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
        <path
          d="m23 2.5 5 3.5-5 3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function Column({
  title,
  caption,
  children,
  emphasis = false,
}: {
  title: string;
  caption: string;
  children: React.ReactNode;
  emphasis?: boolean;
}) {
  return (
    <section
      className={`min-w-0 rounded-[12px] border p-3.5 ${
        emphasis
          ? "border-[var(--mk-accent-400)] bg-[var(--mk-accent-50)]"
          : "border-[var(--mk-bd)] bg-[var(--mk-panel)]"
      }`}
    >
      <h3
        className={`text-[0.6875rem] font-bold uppercase tracking-[0.12em] ${
          emphasis ? "text-[var(--mk-accent-700)]" : "text-[var(--mk-fg-faint)]"
        }`}
      >
        {title}
      </h3>
      <p className="mt-1.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-muted)]">
        {caption}
      </p>
      <ul className="mt-3 space-y-2">{children}</ul>
    </section>
  );
}

function Item({
  name,
  note,
  Icon,
}: {
  name: string;
  note: string;
  Icon?: typeof IconPlug;
}) {
  return (
    <li className="rounded-[8px] border border-[var(--mk-bd)] bg-white px-2.5 py-2">
      <span className="flex items-center gap-2">
        {Icon ? (
          <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--mk-accent-600)]" />
        ) : null}
        <span className="truncate text-[0.75rem] font-semibold text-[var(--mk-fg)]">
          {name}
        </span>
      </span>
      <span className="mt-0.5 block text-[0.625rem] leading-snug text-[var(--mk-fg-faint)]">
        {note}
      </span>
    </li>
  );
}

/**
 * Architekturdiagramm statt Logowand: Datenquellen → Governance Layer → Outputs.
 * Zeigt, an welcher Stelle Compliance Hub in eine bestehende Landschaft eingreift.
 */
export function IntegrationArchitecture({ className = "" }: { className?: string }) {
  return (
    <div className={`mk-card overflow-hidden ${className}`.trim()}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
        <p className="mk-label">Integrationsarchitektur</p>
        <p className="mk-mono text-[var(--mk-fg-faint)]">
          lesend, schreibend oder ereignisgesteuert
        </p>
      </div>

      <div className="grid gap-1 p-3.5 lg:grid-cols-[minmax(0,1fr)_2rem_minmax(0,1.05fr)_2rem_minmax(0,1fr)] lg:items-stretch lg:gap-2">
        <Column
          title="Datenquellen"
          caption="Systeme, in denen die Informationen bereits entstehen."
        >
          {SOURCES.map((source) => (
            <Item key={source.name} name={source.name} note={source.note} />
          ))}
        </Column>

        <Arrow label="Datenzufluss" />

        <Column
          title="Compliance Hub · Governance Layer"
          caption="Der gemeinsame Stand, auf den sich alle Regelwerke beziehen."
          emphasis
        >
          {LAYER.map((item) => (
            <Item key={item.name} name={item.name} note={item.note} Icon={item.Icon} />
          ))}
        </Column>

        <Arrow label="Ergebnisse" />

        <Column
          title="Outputs"
          caption="Was Prüfung, Mandant und Geschäftsleitung tatsächlich brauchen."
        >
          {OUTPUTS.map((item) => (
            <Item key={item.name} name={item.name} note={item.note} Icon={item.Icon} />
          ))}
        </Column>
      </div>

      <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
        Umfang und Richtung jeder Anbindung werden je Installation festgelegt und
        dokumentiert. Ohne Standardkonnektor bleiben API, Webhook und strukturierter
        Import der Weg.
      </p>
    </div>
  );
}

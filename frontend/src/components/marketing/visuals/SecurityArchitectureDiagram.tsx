import React from "react";

import { StatusChip } from "../ui/Primitives";

type Node = {
  name: string;
  detail: string;
  chip?: string;
};

type Tier = {
  id: string;
  label: string;
  caption: string;
  nodes: Node[];
};

const TIERS: Tier[] = [
  {
    id: "client",
    label: "Präsentation",
    caption: "Auslieferung an den Browser mit restriktiven Sicherheitsvorgaben.",
    nodes: [
      {
        name: "Next.js Frontend",
        detail: "Server-gerenderte Ansichten, nonce-basierte Content Security Policy",
        chip: "Strict CSP",
      },
    ],
  },
  {
    id: "identity",
    label: "Identität",
    caption: "Anmeldung und Rollen kommen aus dem Verzeichnis des Kunden.",
    nodes: [
      {
        name: "SAML 2.0 · Microsoft Entra ID · SAP IAS",
        detail: "SSO, Gruppen-Mapping, rollenbasierte Zugriffe je Mandant",
        chip: "SSO",
      },
    ],
  },
  {
    id: "api",
    label: "Anwendung",
    caption: "Fachlogik, Autorisierung und Protokollierung an einer Stelle.",
    nodes: [
      {
        name: "FastAPI API Layer",
        detail: "Autorisierung je Anfrage, Mandantenkontext, Eingabevalidierung",
      },
      {
        name: "n8n · self-hosted in der EU",
        detail: "Automatisierte Routineschritte ohne Datenabfluss zu Dritten",
        chip: "EU",
      },
    ],
  },
  {
    id: "data",
    label: "Daten",
    caption: "Trennung der Mandanten wird auf Datenbankebene erzwungen.",
    nodes: [
      {
        name: "PostgreSQL",
        detail: "Verschlüsselung in Transit und at Rest, gesicherte Backups",
      },
      {
        name: "Row Level Security",
        detail: "Mandantenisolation als Datenbankregel, nicht als Anwendungslogik",
        chip: "RLS",
      },
      {
        name: "pgvector · RAG Knowledge Base",
        detail: "Recherche auf freigegebenen Inhalten des jeweiligen Mandanten",
      },
      {
        name: "Audit Hash Chain",
        detail: "Verkettete Prüfsummen über Änderungen und Freigaben",
      },
    ],
  },
];

const ENVIRONMENTS = [
  { name: "Development", detail: "Keine Produktionsdaten" },
  { name: "Staging", detail: "Abnahme und Migrationstests" },
  { name: "Production", detail: "Getrennte Zugänge und Schlüssel" },
];

function TierArrow() {
  return (
    <div aria-hidden className="flex justify-center py-1">
      <svg viewBox="0 0 12 20" width="12" height="20" className="text-[var(--mk-bd-strong)]">
        <path d="M6 1v14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <path
          d="M2.5 13 6 17l3.5-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

/**
 * Architekturbild statt Sicherheitsfloskeln: welche Ebene welche Kontrolle trägt.
 */
export function SecurityArchitectureDiagram({ className = "" }: { className?: string }) {
  return (
    <div className={`mk-card overflow-hidden ${className}`.trim()}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
        <p className="mk-label">Systemarchitektur</p>
        <StatusChip tone="ok">Hosting in der EU · Deutschland-Option</StatusChip>
      </div>

      <div className="p-4">
        {TIERS.map((tier, index) => (
          <React.Fragment key={tier.id}>
            <section className="rounded-[12px] border border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] p-3.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-[var(--mk-accent-700)]">
                  {tier.label}
                </h3>
                <p className="text-[0.6875rem] text-[var(--mk-fg-faint)]">{tier.caption}</p>
              </div>
              <ul
                className={`mt-2.5 grid gap-2 ${
                  tier.nodes.length > 1 ? "sm:grid-cols-2" : ""
                }`}
              >
                {tier.nodes.map((node) => (
                  <li
                    key={node.name}
                    className="rounded-[8px] border border-[var(--mk-bd)] bg-white px-3 py-2.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                        {node.name}
                      </span>
                      {node.chip ? (
                        <StatusChip tone="info" dot={false}>
                          {node.chip}
                        </StatusChip>
                      ) : null}
                    </div>
                    <p className="mt-1 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-muted)]">
                      {node.detail}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
            {index < TIERS.length - 1 ? <TierArrow /> : null}
          </React.Fragment>
        ))}

        <div className="mt-4 rounded-[12px] border border-dashed border-[var(--mk-bd-strong)] p-3.5">
          <p className="mk-label">Getrennte Umgebungen</p>
          <ul className="mt-2 grid gap-2 sm:grid-cols-3">
            {ENVIRONMENTS.map((environment) => (
              <li
                key={environment.name}
                className="rounded-[8px] border border-[var(--mk-bd)] bg-white px-3 py-2"
              >
                <span className="block text-[0.75rem] font-semibold text-[var(--mk-fg)]">
                  {environment.name}
                </span>
                <span className="block text-[0.625rem] text-[var(--mk-fg-faint)]">
                  {environment.detail}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

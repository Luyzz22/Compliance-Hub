import React from "react";

import {
  AI_SYSTEM_REGISTER,
  DEMO_ORG,
  RISK_CLASS_LABEL,
} from "@/lib/marketing/demoData";

import { StatusChip } from "../ui/Primitives";

/* ── Miniaturen ───────────────────────────────────────────────────── */

function Mini({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mk-card overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-3.5 py-2">
        <p className="mk-label truncate">{title}</p>
        <p className="mk-mono shrink-0 text-[var(--mk-fg-faint)]">{DEMO_ORG.name}</p>
      </div>
      <div className="p-3.5">{children}</div>
    </div>
  );
}

function ScopeMini() {
  const rows: [string, string][] = [
    ["Organisation", "Musterindustrie GmbH"],
    ["Standorte", "Werk Nord, Werk Süd, Zentrale"],
    ["Geltungsbereich", "Fertigung, IT, HR, Finanzen"],
    ["Rollenmodell", "AI Owner, CISO, DSB, Compliance"],
  ];
  const frameworks: [string, boolean][] = [
    ["EU AI Act", true],
    ["ISO/IEC 42001", true],
    ["NIS2", true],
    ["ISO/IEC 27001", true],
    ["ISO/IEC 27701", false],
    ["DSGVO", true],
  ];
  return (
    <Mini title="Geltungsbereich festlegen">
      <dl className="mk-spec">
        {rows.map(([term, value]) => (
          <div key={term} className="grid gap-1 py-2 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-3">
            <dt className="text-[0.6875rem] font-semibold text-[var(--mk-fg-faint)]">
              {term}
            </dt>
            <dd className="text-[0.75rem] text-[var(--mk-fg-soft)]">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mk-label mt-3">Anwendbare Regelwerke</p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {frameworks.map(([name, active]) => (
          <li key={name}>
            <StatusChip tone={active ? "ok" : "neutral"} dot={active}>
              {name}
            </StatusChip>
          </li>
        ))}
      </ul>
    </Mini>
  );
}

function InventoryMini() {
  const rows = AI_SYSTEM_REGISTER.slice(0, 4);
  return (
    <Mini title="KI-System- und Use-Case-Register">
      <div className="mk-table-scroll">
        <table className="mk-table">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">System</th>
              <th scope="col">Risikoklasse</th>
              <th scope="col">Owner</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="mk-mono whitespace-nowrap text-[var(--mk-fg-faint)]">
                  {row.id}
                </td>
                <td>
                  <span className="block font-medium text-[var(--mk-fg)]">{row.name}</span>
                  <span className="block text-[0.625rem] text-[var(--mk-fg-faint)]">
                    {row.domain}
                  </span>
                </td>
                <td className="whitespace-nowrap">
                  <StatusChip
                    tone={
                      row.riskClass === "hoch"
                        ? "crit"
                        : row.riskClass === "begrenzt"
                          ? "warn"
                          : "neutral"
                    }
                    dot={false}
                  >
                    {RISK_CLASS_LABEL[row.riskClass]}
                  </StatusChip>
                </td>
                <td className="whitespace-nowrap text-[var(--mk-fg-soft)]">{row.owner}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[0.6875rem] text-[var(--mk-fg-faint)]">
        27 erfasste Systeme · Import aus CSV, API oder bestehender Systemliste
      </p>
    </Mini>
  );
}

function RiskEngineMini() {
  const gaps: [string, string, "crit" | "warn" | "ok"][] = [
    ["Art. 11 Technische Dokumentation", "unvollständig", "crit"],
    ["Art. 14 Menschliche Aufsicht", "Verfahren in Review", "warn"],
    ["Art. 10 Daten-Governance", "Nachweis vorhanden", "ok"],
    ["Art. 12 Aufzeichnungen", "Nachweis vorhanden", "ok"],
  ];
  return (
    <Mini title="Klassifizierung und Gap-Analyse">
      <div className="flex flex-wrap items-center gap-2 rounded-[10px] border border-[var(--mk-crit-100)] bg-[var(--mk-crit-50)] px-3 py-2.5">
        <span className="mk-mono text-[var(--mk-fg-faint)]">AI-014</span>
        <span className="text-[0.75rem] font-semibold text-[var(--mk-fg)]">
          Bewerber-Vorauswahl
        </span>
        <StatusChip tone="crit">Hochrisiko · Anhang III Nr. 4</StatusChip>
      </div>
      <ul className="mt-3 divide-y divide-[var(--mk-bd)] border-y border-[var(--mk-bd)]">
        {gaps.map(([requirement, state, tone]) => (
          <li
            key={requirement}
            className="flex items-center justify-between gap-3 py-2"
          >
            <span className="min-w-0 truncate text-[0.75rem] text-[var(--mk-fg-soft)]">
              {requirement}
            </span>
            <StatusChip tone={tone} dot={false}>
              {state}
            </StatusChip>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <StatusChip tone="info" dot={false}>
          ISO/IEC 42001 A.5.2
        </StatusChip>
        <StatusChip tone="info" dot={false}>
          ISO/IEC 27001 6.1.2
        </StatusChip>
        <StatusChip tone="info" dot={false}>
          DSGVO Art. 35
        </StatusChip>
      </div>
    </Mini>
  );
}

function OutputMini() {
  const outputs: [string, string][] = [
    ["Board-Report Q3 2026", "PDF · 2 Seiten · Entscheidungsvorlage"],
    ["Evidenz-Dossier AI Act", "41 Nachweise · Prüfpfad signiert"],
    ["Maßnahmenplan", "7 Maßnahmen · Owner und Fristen"],
    ["Mandanten-Export", "Strukturierte Übergabe an die Kanzlei"],
  ];
  return (
    <Mini title="Evidenz und Board-Output">
      <ul className="divide-y divide-[var(--mk-bd)]">
        {outputs.map(([title, detail]) => (
          <li key={title} className="flex items-center justify-between gap-3 py-2.5">
            <span className="min-w-0">
              <span className="block truncate text-[0.75rem] font-medium text-[var(--mk-fg)]">
                {title}
              </span>
              <span className="block truncate text-[0.6875rem] text-[var(--mk-fg-faint)]">
                {detail}
              </span>
            </span>
            <span className="mk-btn mk-btn--secondary mk-btn--sm shrink-0">Export</span>
          </li>
        ))}
      </ul>
      <p className="mk-mono mt-3 text-[var(--mk-fg-faint)]">
        Audit Trail · Hash 8f3c…a10 · 02.09.2026 14:12 · A. Lindner
      </p>
    </Mini>
  );
}

/* ── Prozess ──────────────────────────────────────────────────────── */

const STEPS = [
  {
    id: "scope",
    title: "Scope",
    outcome:
      "Der Geltungsbereich steht fest — inklusive der Regelwerke, die wirklich greifen.",
    bullets: [
      "Organisation, Standorte und Geltungsbereich definieren",
      "Anwendbare Normen und Rechtsakte auswählen",
      "Rollen und Verantwortlichkeiten hinterlegen",
    ],
    Mini: ScopeMini,
  },
  {
    id: "inventory",
    title: "Inventory",
    outcome:
      "Alle KI-Systeme, Assets, Anbieter und Prozesse liegen mit Owner an einer Stelle.",
    bullets: [
      "KI-Systeme und Use Cases erfassen oder importieren",
      "Anbieter, Modelle und verarbeitete Datenarten dokumentieren",
      "Prozessbezug und betroffene Fachbereiche zuordnen",
    ],
    Mini: InventoryMini,
  },
  {
    id: "policy-risk",
    title: "Policy & Risk Engine",
    outcome:
      "Aus Anforderungen werden bewertete Lücken mit Priorität und Verantwortung.",
    bullets: [
      "Risikoklassifizierung nach EU AI Act und Risikobewertung nach NIS2",
      "Control Mapping über mehrere Regelwerke hinweg",
      "Gap-Analyse, Priorisierung und Maßnahmenzuweisung",
    ],
    Mini: RiskEngineMini,
  },
  {
    id: "evidence-board",
    title: "Evidence & Board Output",
    outcome:
      "Nachweise, Prüfpfad und Bericht sind auf Abruf verfügbar statt kurz vor dem Termin.",
    bullets: [
      "Nachweise mit Version, Herkunft und Review-Zyklus führen",
      "Audit Trail über Änderungen und Freigaben",
      "Export für Prüfung, Kanzlei, Kunde oder Geschäftsleitung",
    ],
    Mini: OutputMini,
  },
] as const;

export function GovernanceFlow() {
  return (
    <ol className="grid gap-8 lg:gap-10">
      {STEPS.map((step, index) => (
        <li
          key={step.id}
          id={step.id}
          className="grid scroll-mt-28 gap-6 border-t border-[var(--mk-bd)] pt-8 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-10"
        >
          <div>
            <div className="flex items-center gap-3">
              <span className="mk-num flex h-8 w-8 items-center justify-center rounded-[8px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[0.8125rem] font-bold text-[var(--mk-accent-700)]">
                {index + 1}
              </span>
              <h3 className="mk-h3">{step.title}</h3>
            </div>
            <p className="mt-3 max-w-md text-[0.9375rem] leading-relaxed text-[var(--mk-fg-soft)]">
              {step.outcome}
            </p>
            <ul className="mt-4 space-y-2">
              {step.bullets.map((bullet) => (
                <li
                  key={bullet}
                  className="grid grid-cols-[0.75rem_minmax(0,1fr)] gap-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]"
                >
                  <span
                    aria-hidden
                    className="mt-[0.6rem] h-px bg-[var(--mk-accent-400)]"
                  />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </div>
          <step.Mini />
        </li>
      ))}
    </ol>
  );
}

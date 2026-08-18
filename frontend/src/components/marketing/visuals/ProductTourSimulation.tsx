"use client";

import React, { useState } from "react";

import {
  ACTION_PLAN,
  AI_SYSTEM_REGISTER,
  BOARD_KPIS,
  DEMO_ORG,
  MAPPED_CONTROLS,
  RISK_CLASS_LABEL,
} from "@/lib/marketing/demoData";

import { Meter, StatusChip } from "../ui/Primitives";

type Step = {
  id: string;
  label: string;
  minutes: string;
  headline: string;
  description: string;
  render: () => React.ReactNode;
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mk-fade-swap">
      <div className="flex items-center justify-between gap-2 border-b border-[var(--mk-bd)] pb-2.5">
        <p className="mk-label">{title}</p>
        <p className="mk-mono text-[var(--mk-fg-faint)]">{DEMO_ORG.name}</p>
      </div>
      <div className="pt-3.5">{children}</div>
    </div>
  );
}

function Row({
  primary,
  secondary,
  trailing,
}: {
  primary: React.ReactNode;
  secondary?: React.ReactNode;
  trailing?: React.ReactNode;
}) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-[8px] border border-[var(--mk-bd)] bg-white px-3 py-2.5">
      <span className="min-w-0">
        <span className="block truncate text-[0.8125rem] font-medium text-[var(--mk-fg)]">
          {primary}
        </span>
        {secondary ? (
          <span className="mt-0.5 block truncate text-[0.6875rem] text-[var(--mk-fg-faint)]">
            {secondary}
          </span>
        ) : null}
      </span>
      {trailing ? <span className="shrink-0">{trailing}</span> : null}
    </li>
  );
}

const STEPS: Step[] = [
  {
    id: "scope",
    label: "Geltungsbereich",
    minutes: "0:00",
    headline: "Sie legen fest, worüber gesprochen wird.",
    description:
      "Organisation, Standorte und die tatsächlich anwendbaren Regelwerke. Damit steht der Rahmen, auf den sich später jede Kennzahl bezieht.",
    render: () => (
      <Panel title="Schritt 1 · Scope">
        <ul className="space-y-2">
          <Row primary="Musterindustrie GmbH" secondary="3 Standorte · 180 Mitarbeitende" />
          <Row
            primary="Anwendbare Regelwerke"
            secondary="EU AI Act, ISO/IEC 42001, ISO/IEC 27001, NIS2, DSGVO"
            trailing={<StatusChip tone="ok">5 aktiv</StatusChip>}
          />
          <Row
            primary="Rollen zugewiesen"
            secondary="AI Owner, CISO, Datenschutzbeauftragte, Compliance Officer"
            trailing={<StatusChip tone="ok">vollständig</StatusChip>}
          />
        </ul>
      </Panel>
    ),
  },
  {
    id: "inventory",
    label: "KI-Register",
    minutes: "1:00",
    headline: "Die Systeme kommen ins Register — mit Owner.",
    description:
      "Erfassen oder importieren, mit Fachbereich, Anbieter und verantwortlicher Person. Ohne Owner bleibt ein Eintrag unvollständig.",
    render: () => (
      <Panel title="Schritt 2 · Inventory">
        <ul className="space-y-2">
          {AI_SYSTEM_REGISTER.slice(0, 4).map((system) => (
            <Row
              key={system.id}
              primary={system.name}
              secondary={`${system.id} · ${system.domain} · Owner ${system.owner}`}
              trailing={
                <StatusChip
                  tone={system.riskClass === "hoch" ? "crit" : "neutral"}
                  dot={false}
                >
                  {RISK_CLASS_LABEL[system.riskClass]}
                </StatusChip>
              }
            />
          ))}
        </ul>
        <p className="mt-3 text-[0.6875rem] text-[var(--mk-fg-faint)]">
          27 Systeme erfasst · 4 davon als Hochrisiko eingestuft
        </p>
      </Panel>
    ),
  },
  {
    id: "classification",
    label: "Klassifizierung",
    minutes: "2:00",
    headline: "Die Einstufung wird begründet, nicht behauptet.",
    description:
      "Die Fragestrecke führt zur Risikoklasse und benennt die Anforderungen, die daraus folgen. Begründung und Prüfpfad bleiben am System.",
    render: () => (
      <Panel title="Schritt 3 · Risikoklassifizierung">
        <div className="rounded-[8px] border border-[var(--mk-crit-100)] bg-[var(--mk-crit-50)] px-3 py-2.5">
          <p className="mk-mono text-[var(--mk-fg-faint)]">AI-014 · Bewerber-Vorauswahl</p>
          <p className="mt-1 text-[0.875rem] font-semibold text-[var(--mk-crit-700)]">
            Hochrisiko · Anhang III Nr. 4 (Beschäftigung)
          </p>
          <p className="mt-1 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-muted)]">
            Begründung: Einsatz zur Vorauswahl von Bewerbungen. Einstufung durch R. Keller
            am 12.08.2026 bestätigt.
          </p>
        </div>
        <ul className="mt-2.5 space-y-2">
          <Row
            primary="Art. 9 Risikomanagementsystem"
            secondary="Control AI-RA-01 zugewiesen"
            trailing={<StatusChip tone="ok">erfüllt</StatusChip>}
          />
          <Row
            primary="Art. 11 Technische Dokumentation"
            secondary="Maßnahme M-118 · fällig 30.09.2026"
            trailing={<StatusChip tone="crit">offen</StatusChip>}
          />
          <Row
            primary="Art. 14 Menschliche Aufsicht"
            secondary="Control HO-03 · Verfahren in Review"
            trailing={<StatusChip tone="warn">in Review</StatusChip>}
          />
        </ul>
      </Panel>
    ),
  },
  {
    id: "controls",
    label: "Control & Evidenz",
    minutes: "3:00",
    headline: "Ein Control trägt mehrere Nachweispflichten.",
    description:
      "Die Risikobeurteilung ist zugleich Nachweis für ISO 42001, ISO 27001, NIS2 und die DSFA. Gepflegt wird sie an einer Stelle.",
    render: () => {
      const control = MAPPED_CONTROLS[0];
      return (
        <Panel title="Schritt 4 · Control Mapping">
          <div className="rounded-[8px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] px-3 py-2.5">
            <p className="mk-mono text-[var(--mk-accent-700)]">{control.id}</p>
            <p className="mt-1 text-[0.875rem] font-semibold text-[var(--mk-fg)]">
              {control.title}
            </p>
            <p className="mt-1 text-[0.6875rem] text-[var(--mk-fg-muted)]">
              Owner {control.owner} · Evidence {control.evidence} · Review{" "}
              {control.reviewCycle}
            </p>
          </div>
          <ul className="mt-2.5 grid gap-2 sm:grid-cols-2">
            {control.mappings.map((mapping) => (
              <li
                key={mapping.framework}
                className="rounded-[8px] border border-[var(--mk-bd)] bg-white px-3 py-2"
              >
                <span className="mk-mono block text-[var(--mk-accent-700)]">
                  {mapping.reference}
                </span>
                <span className="mt-0.5 block truncate text-[0.6875rem] text-[var(--mk-fg-muted)]">
                  {mapping.label}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      );
    },
  },
  {
    id: "board",
    label: "Board Report",
    minutes: "4:00",
    headline: "Der Bericht entsteht aus dem laufenden Stand.",
    description:
      "Kein Sammeln kurz vor dem Termin: Readiness, Entscheidungsbedarf und Fristen liegen jederzeit in Board-Sprache vor.",
    render: () => (
      <Panel title="Schritt 5 · Board Output">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ["Readiness", `${BOARD_KPIS.readinessScore}%`],
            ["Evidence", `${BOARD_KPIS.evidenceCoverage}%`],
            ["Findings", `${BOARD_KPIS.criticalFindings}`],
            ["Entscheidungen", `${BOARD_KPIS.openDecisions}`],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-[8px] border border-[var(--mk-bd)] bg-white px-3 py-2.5"
            >
              <p className="truncate text-[0.5625rem] font-semibold uppercase tracking-[0.09em] text-[var(--mk-fg-faint)]">
                {label}
              </p>
              <p className="mk-num mt-1 text-[1.125rem] font-semibold leading-none text-[var(--mk-fg)]">
                {value}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-2.5">
          <Meter
            value={BOARD_KPIS.readinessScore}
            tone="warn"
            label="Board Readiness"
            height={6}
          />
        </div>
        <ul className="mt-2.5 space-y-2">
          {ACTION_PLAN.slice(0, 3).map((action) => (
            <Row
              key={action.id}
              primary={action.title}
              secondary={`${action.owner} · ${action.framework} ${action.reference}`}
              trailing={
                <StatusChip tone={action.priority === "kritisch" ? "crit" : "warn"} dot={false}>
                  {action.due}
                </StatusChip>
              }
            />
          ))}
        </ul>
      </Panel>
    ),
  },
];

/**
 * Produkt-Tour-Simulation: fünf Schritte durch den Governance-Ablauf.
 * Der Wechsel ist bewusst nutzergesteuert, ohne automatischen Slide-Lauf.
 */
export function ProductTourSimulation() {
  const [index, setIndex] = useState(0);
  const step = STEPS[index];

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)] lg:gap-8">
      <div>
        <ol
          role="tablist"
          aria-label="Schritte der Produkt-Tour"
          aria-orientation="vertical"
          className="space-y-1.5"
        >
          {STEPS.map((item, itemIndex) => {
            const selected = itemIndex === index;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls={`tour-panel-${item.id}`}
                  id={`tour-tab-${item.id}`}
                  onClick={() => setIndex(itemIndex)}
                  className={`flex w-full items-center gap-3 rounded-[10px] border px-3 py-2.5 text-left transition-colors ${
                    selected
                      ? "border-[var(--mk-accent-400)] bg-[var(--mk-accent-50)]"
                      : "border-[var(--mk-bd)] bg-white hover:border-[var(--mk-bd-strong)]"
                  }`}
                >
                  <span
                    className={`mk-num flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] text-[0.75rem] font-bold ${
                      selected
                        ? "bg-[var(--mk-accent-600)] text-white"
                        : "bg-[var(--mk-slate-100)] text-[var(--mk-fg-muted)]"
                    }`}
                  >
                    {itemIndex + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                      {item.label}
                    </span>
                    <span className="mk-num block text-[0.625rem] text-[var(--mk-fg-faint)]">
                      Minute {item.minutes}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="mk-btn mk-btn--secondary mk-btn--sm"
            onClick={() => setIndex((current) => Math.max(0, current - 1))}
            disabled={index === 0}
          >
            Zurück
          </button>
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--sm"
            onClick={() => setIndex((current) => Math.min(STEPS.length - 1, current + 1))}
            disabled={index === STEPS.length - 1}
          >
            Weiter
          </button>
        </div>
      </div>

      <div
        role="tabpanel"
        id={`tour-panel-${step.id}`}
        aria-labelledby={`tour-tab-${step.id}`}
        className="min-w-0"
      >
        <h3 className="mk-h3">{step.headline}</h3>
        <p className="mt-2.5 max-w-2xl text-[0.9375rem] leading-relaxed text-[var(--mk-fg-muted)]">
          {step.description}
        </p>
        <div className="mk-card mt-4 p-4">{step.render()}</div>
        <p className="mt-3 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
          Illustrative Produktansicht mit Beispieldaten der Musterindustrie GmbH. Die
          Plattform unterstützt bei der strukturierten Umsetzung und ersetzt keine Prüfung
          oder Rechtsberatung.
        </p>
      </div>
    </div>
  );
}

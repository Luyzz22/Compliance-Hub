import React from "react";

import {
  ADVISOR_PORTFOLIO,
  AI_SYSTEM_REGISTER,
  BOARD_KPIS,
  RISK_CLASS_LABEL,
} from "@/lib/marketing/demoData";

import {
  IconBoard,
  IconClassify,
  IconEvidence,
  IconMapping,
  IconRegistry,
  IconTenants,
} from "../ui/Icons";
import { Meter, StatusChip, toneForCoverage } from "../ui/Primitives";
import { Reveal } from "../ui/Reveal";

/* ── Mini-Visualisierungen je Modul ───────────────────────────────── */

function MiniShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 rounded-[10px] border border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] p-2.5">
      {children}
    </div>
  );
}

function RegisterMini() {
  return (
    <MiniShell>
      <ul className="space-y-1.5">
        {AI_SYSTEM_REGISTER.slice(0, 3).map((system) => (
          <li
            key={system.id}
            className="flex items-center justify-between gap-2 rounded-[6px] border border-[var(--mk-bd)] bg-white px-2.5 py-1.5"
          >
            <span className="min-w-0">
              <span className="mk-mono block text-[var(--mk-fg-faint)]">{system.id}</span>
              <span className="block truncate text-[0.6875rem] font-medium text-[var(--mk-fg)]">
                {system.name}
              </span>
            </span>
            <StatusChip
              tone={system.riskClass === "hoch" ? "crit" : "neutral"}
              dot={false}
            >
              {RISK_CLASS_LABEL[system.riskClass]}
            </StatusChip>
          </li>
        ))}
      </ul>
    </MiniShell>
  );
}

function AssessmentMini() {
  const requirements: [string, "ok" | "warn" | "crit"][] = [
    ["Art. 9 Risikomanagement", "ok"],
    ["Art. 11 Technische Doku", "crit"],
    ["Art. 14 Menschliche Aufsicht", "warn"],
  ];
  return (
    <MiniShell>
      <div className="rounded-[6px] border border-[var(--mk-crit-100)] bg-[var(--mk-crit-50)] px-2.5 py-1.5">
        <span className="mk-mono text-[var(--mk-fg-faint)]">AI-014 · Ergebnis</span>
        <span className="mt-0.5 block text-[0.75rem] font-semibold text-[var(--mk-crit-700)]">
          Hochrisiko · Anhang III Nr. 4
        </span>
      </div>
      <ul className="mt-1.5 space-y-1">
        {requirements.map(([label, tone]) => (
          <li
            key={label}
            className="flex items-center justify-between gap-2 rounded-[6px] border border-[var(--mk-bd)] bg-white px-2.5 py-1.5"
          >
            <span className="truncate text-[0.6875rem] text-[var(--mk-fg-soft)]">{label}</span>
            <span
              aria-hidden
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                tone === "ok"
                  ? "bg-[var(--mk-ok-500)]"
                  : tone === "warn"
                    ? "bg-[var(--mk-warn-500)]"
                    : "bg-[var(--mk-crit-500)]"
              }`}
            />
          </li>
        ))}
      </ul>
    </MiniShell>
  );
}

function MappingMini() {
  return (
    <MiniShell>
      <div className="rounded-[6px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] px-2.5 py-1.5">
        <span className="mk-mono text-[var(--mk-accent-700)]">AI-RA-01</span>
        <span className="mt-0.5 block text-[0.75rem] font-semibold text-[var(--mk-fg)]">
          KI-Risikobeurteilung
        </span>
      </div>
      <p className="mt-2 mb-1.5 text-[0.5625rem] font-semibold uppercase tracking-[0.09em] text-[var(--mk-fg-faint)]">
        Nachweis in 5 Regelwerken
      </p>
      <ul className="flex flex-wrap gap-1">
        {["AI Act Art. 9", "42001 6.1.2", "27001 6.1.2", "NIS2 21(2)a", "DSGVO 35"].map(
          (tag) => (
            <li key={tag}>
              <StatusChip tone="info" dot={false}>
                {tag}
              </StatusChip>
            </li>
          ),
        )}
      </ul>
    </MiniShell>
  );
}

function EvidenceMini() {
  const rows: [string, string, "ok" | "warn" | "crit"][] = [
    ["Risikoanalyse v3", "Review 30.11.2026", "ok"],
    ["Logging-Konzept v2.1", "in Review", "warn"],
    ["Lieferantenbewertung", "Review überfällig", "crit"],
  ];
  return (
    <MiniShell>
      <ul className="space-y-1.5">
        {rows.map(([title, note, tone]) => (
          <li
            key={title}
            className="flex items-center justify-between gap-2 rounded-[6px] border border-[var(--mk-bd)] bg-white px-2.5 py-1.5"
          >
            <span className="min-w-0">
              <span className="block truncate text-[0.6875rem] font-medium text-[var(--mk-fg)]">
                {title}
              </span>
              <span className="block truncate text-[0.625rem] text-[var(--mk-fg-faint)]">
                {note}
              </span>
            </span>
            <StatusChip tone={tone} dot={false}>
              {tone === "ok" ? "gültig" : tone === "warn" ? "Review" : "fällig"}
            </StatusChip>
          </li>
        ))}
      </ul>
    </MiniShell>
  );
}

function BoardMini() {
  return (
    <MiniShell>
      <div className="grid grid-cols-3 gap-1.5">
        {[
          ["Readiness", `${BOARD_KPIS.readinessScore}%`],
          ["Evidence", `${BOARD_KPIS.evidenceCoverage}%`],
          ["Findings", `${BOARD_KPIS.criticalFindings}`],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-[6px] border border-[var(--mk-bd)] bg-white px-2 py-1.5 text-center"
          >
            <span className="block truncate text-[0.5625rem] font-semibold uppercase tracking-[0.08em] text-[var(--mk-fg-faint)]">
              {label}
            </span>
            <span className="mk-num mt-0.5 block text-[0.9375rem] font-semibold text-[var(--mk-fg)]">
              {value}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-1.5 rounded-[6px] border border-[var(--mk-crit-100)] bg-[var(--mk-crit-50)] px-2.5 py-1.5 text-[0.6875rem] font-medium text-[var(--mk-crit-700)]">
        {BOARD_KPIS.openDecisions} Entscheidungen erforderlich
      </p>
    </MiniShell>
  );
}

function TenantMini() {
  return (
    <MiniShell>
      <ul className="space-y-1.5">
        {ADVISOR_PORTFOLIO.slice(0, 3).map((mandant) => (
          <li
            key={mandant.mandant}
            className="rounded-[6px] border border-[var(--mk-bd)] bg-white px-2.5 py-1.5"
          >
            <span className="flex items-baseline justify-between gap-2">
              <span className="truncate text-[0.6875rem] font-medium text-[var(--mk-fg)]">
                {mandant.mandant}
              </span>
              <span className="mk-num shrink-0 text-[0.6875rem] font-semibold text-[var(--mk-fg-soft)]">
                {mandant.readiness}%
              </span>
            </span>
            <span className="mt-1 block">
              <Meter
                value={mandant.readiness}
                tone={toneForCoverage(mandant.readiness)}
                label={mandant.mandant}
                height={4}
              />
            </span>
          </li>
        ))}
      </ul>
    </MiniShell>
  );
}

/* ── Modul-Definitionen ───────────────────────────────────────────── */

const MODULES = [
  {
    id: "ai-register",
    letter: "A",
    Icon: IconRegistry,
    title: "AI System Register",
    lines: [
      "Alle KI-Systeme, Use Cases, Anbieter und Owner an einer Stelle.",
      "Import aus Listen, API oder bestehender Systemdokumentation.",
    ],
    Mini: RegisterMini,
  },
  {
    id: "ai-act-assessment",
    letter: "B",
    Icon: IconClassify,
    title: "EU AI Act Assessment",
    lines: [
      "Klassifizierung, Anforderungen, Maßnahmen und Technical-File-Readiness.",
      "Jede Einstufung bleibt mit Begründung und Prüfpfad hinterlegt.",
    ],
    Mini: AssessmentMini,
  },
  {
    id: "control-mapping",
    letter: "C",
    Icon: IconMapping,
    title: "Control Mapping",
    lines: [
      "Controls einmal pflegen und über EU AI Act, ISO 42001, ISO 27001, DSGVO und NIS2 wiederverwenden.",
      "Änderungen wirken auf alle verbundenen Regelwerke.",
    ],
    Mini: MappingMini,
  },
  {
    id: "evidence-engine",
    letter: "D",
    Icon: IconEvidence,
    title: "Evidence Engine",
    lines: [
      "Nachweise, Review-Zyklen und Audit Trail nachvollziehbar verwalten.",
      "Fällige Reviews werden sichtbar, bevor die Prüfung sie findet.",
    ],
    Mini: EvidenceMini,
  },
  {
    id: "board-reporting",
    letter: "E",
    Icon: IconBoard,
    title: "Board Reporting",
    lines: [
      "Risiken, Fortschritt und offene Entscheidungen in board-tauglicher Sprache.",
      "Aus dem laufenden Stand erzeugt, nicht aus einer Sonderauswertung.",
    ],
    Mini: BoardMini,
  },
  {
    id: "mandanten-workspace",
    letter: "F",
    Icon: IconTenants,
    title: "Mandanten-Workspace",
    lines: [
      "Mehrere Mandanten, Rollen, Templates und Reports in einer Plattform steuern.",
      "Getrennte Datenräume mit gemeinsamer Methodik.",
    ],
    Mini: TenantMini,
  },
] as const;

export function ModuleGrid() {
  return (
    <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {MODULES.map((module, index) => (
        <Reveal
          key={module.id}
          as="li"
          delay={(index % 3) as 0 | 1 | 2}
          className="min-w-0"
        >
          <article
            id={`modul-${module.id}`}
            className="mk-card mk-card-interactive flex h-full scroll-mt-28 flex-col p-4"
          >
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-[8px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[var(--mk-accent-700)]">
                <module.Icon className="h-4 w-4" />
              </span>
              <span className="mk-mono text-[var(--mk-fg-faint)]">{module.letter}</span>
            </div>
            <h3 className="mk-h4 mt-3">{module.title}</h3>
            <div className="mt-2 space-y-1.5">
              {module.lines.map((line) => (
                <p
                  key={line}
                  className="text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]"
                >
                  {line}
                </p>
              ))}
            </div>
            <div className="mt-auto">
              <module.Mini />
            </div>
          </article>
        </Reveal>
      ))}
    </ul>
  );
}

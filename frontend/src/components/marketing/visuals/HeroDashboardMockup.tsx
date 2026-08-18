import React from "react";

import {
  ACTION_PLAN,
  BOARD_KPIS,
  CONTROL_STATUS,
  DEADLINES,
  DEMO_ORG,
} from "@/lib/marketing/demoData";

import {
  IconBoard,
  IconClock,
  IconEvidence,
  IconMapping,
  IconRegistry,
  IconShield,
} from "../ui/Icons";
import { Meter, StatusChip } from "../ui/Primitives";

const RAIL_ITEMS = [
  { label: "Übersicht", Icon: IconBoard, active: true },
  { label: "KI-Register", Icon: IconRegistry, active: false },
  { label: "Controls", Icon: IconMapping, active: false },
  { label: "Evidenz", Icon: IconEvidence, active: false },
  { label: "Risiken", Icon: IconShield, active: false },
];

const STATUS_SEGMENTS = [
  {
    key: "compliant",
    label: "Compliant",
    count: CONTROL_STATUS.compliant,
    fill: "var(--mk-ok-500)",
  },
  {
    key: "at-risk",
    label: "At Risk",
    count: CONTROL_STATUS.atRisk,
    fill: "var(--mk-warn-500)",
  },
  {
    key: "action",
    label: "Action required",
    count: CONTROL_STATUS.actionRequired,
    fill: "var(--mk-crit-500)",
  },
] as const;

function StatusDistribution() {
  const total = CONTROL_STATUS.total;
  const segments = STATUS_SEGMENTS.map((segment, index) => {
    const precedingCount = STATUS_SEGMENTS.slice(0, index).reduce(
      (sum, previous) => sum + previous.count,
      0,
    );
    return {
      ...segment,
      x: (precedingCount / total) * 100,
      width: (segment.count / total) * 100,
    };
  });

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <p className="mk-label">Kontrollstatus</p>
        <p className="mk-num whitespace-nowrap text-[0.625rem] text-[#74869e]">
          {total} aktive Controls
        </p>
      </div>
      <svg
        viewBox="0 0 100 8"
        preserveAspectRatio="none"
        height={8}
        width="100%"
        className="mt-2.5 block w-full"
        role="img"
        aria-label={`Kontrollstatus: ${CONTROL_STATUS.compliant} compliant, ${CONTROL_STATUS.atRisk} at risk, ${CONTROL_STATUS.actionRequired} mit Handlungsbedarf`}
      >
        {segments.map((segment, index) => (
          <rect
            key={segment.key}
            x={segment.x}
            y="0"
            width={Math.max(segment.width - 0.6, 0)}
            height="8"
            rx={index === 0 || index === segments.length - 1 ? 2 : 0}
            fill={segment.fill}
          />
        ))}
      </svg>
      <ul className="mt-3 grid grid-cols-3 gap-2">
        {segments.map((segment) => (
          <li key={segment.key} className="min-w-0">
            <span className="flex items-center gap-1.5">
              <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden className="shrink-0">
                <circle cx="4" cy="4" r="4" fill={segment.fill} />
              </svg>
              <span className="mk-num text-[0.8125rem] font-semibold text-white">
                {segment.count}
              </span>
            </span>
            <span className="mt-0.5 block truncate text-[0.625rem] text-[#8798b0]">
              {segment.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function KpiTile({
  label,
  value,
  suffix,
  hint,
  meter,
  meterTone,
}: {
  label: string;
  value: number | string;
  suffix?: string;
  hint?: string;
  meter?: number;
  meterTone?: "ok" | "warn" | "crit" | "info";
}) {
  return (
    <div className="min-w-0 rounded-[10px] border border-white/10 bg-white/[0.04] px-3 py-3">
      <p className="text-[0.625rem] font-semibold uppercase leading-tight tracking-[0.08em] text-[#8798b0]">
        {label}
      </p>
      <p className="mk-num mt-2 text-[1.5rem] font-semibold leading-none text-white">
        {value}
        {suffix ? (
          <span className="ml-0.5 align-top text-[0.75rem] font-semibold text-[#8798b0]">
            {suffix}
          </span>
        ) : null}
      </p>
      {typeof meter === "number" ? (
        <div className="mt-2.5">
          <Meter value={meter} tone={meterTone ?? "info"} label={label} height={4} />
        </div>
      ) : null}
      {hint ? (
        <p className="mt-2 text-[0.625rem] leading-snug text-[#74869e]">{hint}</p>
      ) : null}
    </div>
  );
}

/**
 * Realistischer Board-Ausschnitt der Plattform: Kennzahlen, Kontrollstatus,
 * Frist und Maßnahmenliste in einer Ansicht — bewusst ohne Zierelemente.
 */
export function HeroDashboardMockup() {
  const deadline = DEADLINES[0];
  const actions = ACTION_PLAN.slice(0, 4);

  return (
    <div className="mk-dark overflow-hidden rounded-[16px] border border-white/10 bg-[#0b1727] shadow-[var(--mk-shadow-dark)]">
      {/* Fensterleiste */}
      <div className="flex items-center gap-2.5 border-b border-white/10 bg-white/[0.03] px-3.5 py-2.5">
        <span className="flex gap-1.5" aria-hidden>
          <span className="h-[7px] w-[7px] rounded-full bg-white/20" />
          <span className="h-[7px] w-[7px] rounded-full bg-white/20" />
          <span className="h-[7px] w-[7px] rounded-full bg-white/20" />
        </span>
        <span className="mk-mono min-w-0 flex-1 truncate text-[#74869e]">
          app.complywithai.de / board / uebersicht
        </span>
        <StatusChip tone="info" dot={false}>
          {DEMO_ORG.reportingPeriod}
        </StatusChip>
      </div>

      <div className="grid lg:grid-cols-[168px_minmax(0,1fr)]">
        {/* Navigationsleiste */}
        <nav
          aria-hidden
          className="hidden flex-col gap-1 border-r border-white/10 bg-white/[0.02] p-3 lg:flex"
        >
          <div className="mb-3 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-2">
            <p className="truncate text-[0.6875rem] font-semibold text-white">
              {DEMO_ORG.name}
            </p>
            <p className="truncate text-[0.5625rem] text-[#74869e]">{DEMO_ORG.workspace}</p>
          </div>
          {RAIL_ITEMS.map(({ label, Icon, active }) => (
            <span
              key={label}
              className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-[0.6875rem] font-medium ${
                active ? "bg-white/[0.09] text-white" : "text-[#8798b0]"
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{label}</span>
            </span>
          ))}
        </nav>

        <div className="min-w-0 p-4 sm:p-5">
          {/* Kopfzeile */}
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-[#74869e]">
                Board Readiness
              </p>
              <h3 className="mt-1 truncate text-[0.9375rem] font-semibold text-white">
                {DEMO_ORG.name}
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusChip tone="ok">EU-Hosting</StatusChip>
              <StatusChip tone="neutral">{DEMO_ORG.asOf}</StatusChip>
            </div>
          </div>

          {/* Kennzahlen */}
          <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-5">
            <KpiTile
              label="Readiness"
              value={BOARD_KPIS.readinessScore}
              suffix="%"
              meter={BOARD_KPIS.readinessScore}
              meterTone="warn"
              hint={`+${BOARD_KPIS.readinessDelta} ggü. Q2`}
            />
            <KpiTile
              label="KI-Systeme"
              value={BOARD_KPIS.aiSystems}
              hint={`${BOARD_KPIS.aiSystemsHighRisk} Hochrisiko`}
            />
            <KpiTile
              label="Kritisch offen"
              value={BOARD_KPIS.criticalFindings}
              hint="Owner belegt"
            />
            <KpiTile
              label="Evidence"
              value={BOARD_KPIS.evidenceCoverage}
              suffix="%"
              meter={BOARD_KPIS.evidenceCoverage}
              meterTone="ok"
              hint="gültiger Nachweis"
            />
            <KpiTile
              label="NIS2 High+"
              value={BOARD_KPIS.nis2HighRisks}
              hint="Art. 21 Register"
            />
          </div>

          {/* Status + Frist + Maßnahmen */}
          <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div className="flex flex-col gap-3">
              <div className="rounded-[10px] border border-white/10 bg-white/[0.04] p-3.5">
                <StatusDistribution />
              </div>

              <div className="rounded-[10px] border border-[rgba(217,130,7,0.34)] bg-[rgba(217,130,7,0.1)] p-3.5">
                <div className="flex items-start gap-2.5">
                  <IconClock className="mt-0.5 h-4 w-4 shrink-0 text-[#fbc35c]" />
                  <div className="min-w-0">
                    <p className="text-[0.75rem] font-semibold text-white">
                      {deadline.label}: Review in {deadline.inDays} Tagen
                    </p>
                    <p className="mt-1 text-[0.6875rem] leading-snug text-[#c3cede]">
                      {deadline.detail}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="min-w-0 overflow-hidden rounded-[10px] border border-white/10 bg-white/[0.04]">
              <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3.5 py-2.5">
                <p className="mk-label">Offene Maßnahmen</p>
                <p className="mk-num text-[0.625rem] text-[#74869e]">
                  {BOARD_KPIS.actionsDueBySeptember} fällig bis 30.09.
                </p>
              </div>
              <ul className="divide-y divide-white/10">
                {actions.map((action) => (
                  <li key={action.id} className="px-3.5 py-2.5">
                    <div className="flex items-start justify-between gap-3">
                      <p className="min-w-0 text-[0.75rem] font-medium leading-snug text-white">
                        {action.title}
                      </p>
                      <p className="mk-num shrink-0 text-[0.6875rem] text-[#d3dcea]">
                        {action.due}
                      </p>
                    </div>
                    <div className="mt-1.5 flex items-center justify-between gap-3">
                      <p className="mk-mono min-w-0 truncate text-[#74869e]">
                        {action.id} · {action.owner} · {action.ownerRole}
                      </p>
                      <StatusChip
                        tone={action.priority === "kritisch" ? "crit" : "neutral"}
                        dot={false}
                      >
                        {action.framework}
                      </StatusChip>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

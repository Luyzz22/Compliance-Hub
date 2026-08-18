import React from "react";

import {
  BOARD_KPIS,
  DEMO_ORG,
  FRAMEWORK_COVERAGE,
} from "@/lib/marketing/demoData";

import { Meter, StatusChip, toneForCoverage } from "../ui/Primitives";

/** Halbkreis-Gauge; Geometrie über SVG-Attribute (strict CSP erlaubt keine Inline-Styles). */
function ScoreGauge({ value }: { value: number }) {
  const radius = 52;
  const circumference = Math.PI * radius;
  const progress = (Math.min(100, Math.max(0, value)) / 100) * circumference;

  return (
    <svg
      viewBox="0 0 128 74"
      width="128"
      height="74"
      role="img"
      aria-label={`Board Readiness Score: ${value} von 100`}
      className="shrink-0"
    >
      <path
        d="M12 66 A52 52 0 0 1 116 66"
        fill="none"
        stroke="var(--mk-slate-200)"
        strokeWidth="9"
        strokeLinecap="round"
      />
      <path
        d="M12 66 A52 52 0 0 1 116 66"
        fill="none"
        stroke="var(--mk-accent-500)"
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={`${progress} ${circumference}`}
      />
      <text
        x="64"
        y="58"
        textAnchor="middle"
        fill="var(--mk-fg)"
        fontSize="27"
        fontWeight="650"
        letterSpacing="-1"
      >
        {value}
      </text>
      <text x="64" y="70" textAnchor="middle" fill="var(--mk-fg-faint)" fontSize="9">
        von 100
      </text>
    </svg>
  );
}

/**
 * Readiness-Score mit Regelwerk-Abdeckung — die Kennzahl beschreibt den
 * Bearbeitungsstand im System, nicht ein Prüfergebnis.
 */
export function ComplianceScoreCard({
  className = "",
}: {
  className?: string;
}) {
  return (
    <div className={`mk-card overflow-hidden ${className}`.trim()}>
      <div className="flex items-center justify-between gap-3 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
        <p className="mk-label">Board Readiness</p>
        <p className="mk-mono text-[var(--mk-fg-faint)]">{DEMO_ORG.reportingPeriod}</p>
      </div>

      <div className="flex flex-wrap items-center gap-5 p-4">
        <ScoreGauge value={BOARD_KPIS.readinessScore} />
        <div className="min-w-[12rem] flex-1">
          <p className="text-[0.9375rem] font-semibold text-[var(--mk-fg)]">
            {DEMO_ORG.name}
          </p>
          <p className="mt-1 text-[0.75rem] leading-relaxed text-[var(--mk-fg-muted)]">
            {DEMO_ORG.profile}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <StatusChip tone="ok">+{BOARD_KPIS.readinessDelta} ggü. Q2</StatusChip>
            <StatusChip tone="crit">
              {BOARD_KPIS.criticalFindings} kritische Findings
            </StatusChip>
          </div>
        </div>
      </div>

      <div className="border-t border-[var(--mk-bd)] px-4 py-3.5">
        <p className="mk-label">Abdeckung je Regelwerk</p>
        <ul className="mt-2.5 space-y-2.5">
          {FRAMEWORK_COVERAGE.map((framework) => (
            <li key={framework.id}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="truncate text-[0.75rem] font-medium text-[var(--mk-fg-soft)]">
                  {framework.label}
                </span>
                <span className="mk-num shrink-0 text-[0.75rem] font-semibold text-[var(--mk-fg)]">
                  {framework.coverage}%
                </span>
              </div>
              <div className="mt-1.5">
                <Meter
                  value={framework.coverage}
                  tone={toneForCoverage(framework.coverage)}
                  label={framework.label}
                  height={5}
                />
              </div>
              <p className="mt-1 text-[0.625rem] text-[var(--mk-fg-faint)]">
                {framework.controls} Controls · {framework.open} offen
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

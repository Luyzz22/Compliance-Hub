"use client";

import React, { useId, useState } from "react";

import {
  FRAMEWORKS,
  MAPPED_CONTROLS,
  type FrameworkId,
} from "@/lib/marketing/demoData";

import { IconEvidence, IconClock, IconMapping } from "../ui/Icons";
import { StatusChip, type StatusTone } from "../ui/Primitives";

const ROW_HEIGHT = 100;
const ROWS = FRAMEWORKS.length;
const VIEW_HEIGHT = ROW_HEIGHT * ROWS;

const EVIDENCE_TONE: Record<string, StatusTone> = {
  aktuell: "ok",
  "in Review": "warn",
  fällig: "crit",
};

export function FrameworkMappingGraph() {
  const [controlIndex, setControlIndex] = useState(0);
  const [activeFramework, setActiveFramework] = useState<FrameworkId | null>(null);
  const gradientId = useId();

  const control = MAPPED_CONTROLS[controlIndex];
  const mappingByFramework = new Map(
    control.mappings.map((mapping) => [mapping.framework, mapping]),
  );

  return (
    <div className="mk-card overflow-hidden">
      {/* Kopfzeile mit Control-Auswahl */}
      <div className="border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-3.5 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="mk-label">Control-Bibliothek · Musterindustrie GmbH</p>
          <p className="mk-mono text-[var(--mk-fg-faint)]">
            {control.mappings.length} Zuordnungen aktiv
          </p>
        </div>
        <div
          role="tablist"
          aria-label="Control auswählen"
          className="mt-2.5 flex flex-wrap gap-1.5"
        >
          {MAPPED_CONTROLS.map((item, index) => {
            const selected = index === controlIndex;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => {
                  setControlIndex(index);
                  setActiveFramework(null);
                }}
                className={`rounded-[6px] border px-2.5 py-1.5 text-[0.75rem] font-semibold transition-colors ${
                  selected
                    ? "border-[var(--mk-accent-600)] bg-[var(--mk-accent-600)] text-white"
                    : "border-[var(--mk-bd)] bg-white text-[var(--mk-fg-muted)] hover:border-[var(--mk-bd-strong)] hover:text-[var(--mk-fg)]"
                }`}
              >
                <span className="mk-mono mr-1.5 opacity-70">{item.id}</span>
                {item.title}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 p-3.5 lg:grid-cols-[minmax(0,1fr)_4.5rem_minmax(0,1fr)] lg:gap-0">
        {/* Control-Detail */}
        <div className="self-center">
          <div className="rounded-[10px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] p-3.5">
            <div className="flex items-center gap-2">
              <IconMapping className="h-4 w-4 shrink-0 text-[var(--mk-accent-700)]" />
              <span className="mk-mono text-[var(--mk-accent-700)]">{control.id}</span>
            </div>
            <p className="mt-2 text-[0.9375rem] font-semibold leading-snug text-[var(--mk-fg)]">
              Control: {control.title}
            </p>
            <dl className="mt-3 space-y-2.5">
              <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
                <dt className="text-[0.6875rem] font-semibold text-[var(--mk-fg-faint)]">
                  Owner
                </dt>
                <dd className="text-[0.75rem] text-[var(--mk-fg-soft)]">
                  {control.owner} · {control.ownerRole}
                </dd>
              </div>
              <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
                <dt className="text-[0.6875rem] font-semibold text-[var(--mk-fg-faint)]">
                  Evidence
                </dt>
                <dd className="flex flex-wrap items-center gap-1.5 text-[0.75rem] text-[var(--mk-fg-soft)]">
                  <IconEvidence className="h-3.5 w-3.5 text-[var(--mk-fg-faint)]" />
                  {control.evidence}
                  <StatusChip
                    tone={EVIDENCE_TONE[control.evidenceState] ?? "neutral"}
                    dot={false}
                  >
                    {control.evidenceState}
                  </StatusChip>
                </dd>
              </div>
              <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
                <dt className="text-[0.6875rem] font-semibold text-[var(--mk-fg-faint)]">
                  Review
                </dt>
                <dd className="flex items-center gap-1.5 text-[0.75rem] text-[var(--mk-fg-soft)]">
                  <IconClock className="h-3.5 w-3.5 text-[var(--mk-fg-faint)]" />
                  {control.reviewCycle}
                </dd>
              </div>
            </dl>
          </div>
          <p className="mt-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Einmal gepflegt. Änderungen an Owner, Nachweis oder Review-Zyklus wirken auf
            alle verbundenen Regelwerke.
          </p>
        </div>

        {/* Verbindungslinien */}
        <div aria-hidden className="hidden lg:block">
          <svg
            viewBox={`0 0 100 ${VIEW_HEIGHT}`}
            preserveAspectRatio="none"
            className="h-full w-full"
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="var(--mk-accent-300)" />
                <stop offset="100%" stopColor="var(--mk-accent-500)" />
              </linearGradient>
            </defs>
            {FRAMEWORKS.map((framework, index) => {
              const y = index * ROW_HEIGHT + ROW_HEIGHT / 2;
              const midY = VIEW_HEIGHT / 2;
              const dimmed = activeFramework !== null && activeFramework !== framework.id;
              return (
                <path
                  key={framework.id}
                  d={`M0 ${midY} C 45 ${midY}, 55 ${y}, 100 ${y}`}
                  fill="none"
                  stroke={
                    activeFramework === framework.id
                      ? "var(--mk-accent-600)"
                      : `url(#${gradientId})`
                  }
                  strokeWidth={activeFramework === framework.id ? 2.2 : 1.4}
                  strokeOpacity={dimmed ? 0.25 : 1}
                  vectorEffect="non-scaling-stroke"
                />
              );
            })}
            <circle
              cx="1.5"
              cy={VIEW_HEIGHT / 2}
              r="3"
              fill="var(--mk-accent-600)"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>

        {/* Regelwerke */}
        <ul className="grid gap-2 lg:h-full lg:grid-rows-6 lg:gap-0">
          {FRAMEWORKS.map((framework) => {
            const mapping = mappingByFramework.get(framework.id);
            const active = activeFramework === framework.id;
            return (
              <li key={framework.id} className="lg:flex lg:items-center lg:py-1">
                <button
                  type="button"
                  aria-pressed={active}
                  onMouseEnter={() => setActiveFramework(framework.id)}
                  onMouseLeave={() => setActiveFramework(null)}
                  onFocus={() => setActiveFramework(framework.id)}
                  onBlur={() => setActiveFramework(null)}
                  onClick={() =>
                    setActiveFramework((current) =>
                      current === framework.id ? null : framework.id,
                    )
                  }
                  className={`w-full rounded-[10px] border px-3 py-2.5 text-left transition-colors ${
                    active
                      ? "border-[var(--mk-accent-400)] bg-[var(--mk-accent-50)]"
                      : "border-[var(--mk-bd)] bg-white hover:border-[var(--mk-bd-strong)]"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                      {framework.short}
                    </span>
                    <StatusChip tone={mapping ? "ok" : "neutral"} dot={false}>
                      {mapping ? "gemappt" : "offen"}
                    </StatusChip>
                  </span>
                  <span className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="mk-mono text-[var(--mk-accent-700)]">
                      {mapping?.reference ?? "—"}
                    </span>
                    <span className="text-[0.6875rem] text-[var(--mk-fg-muted)]">
                      {mapping?.label ?? "keine Zuordnung hinterlegt"}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-3.5 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
        Zuordnungen sind fachliche Arbeitshilfen und ersetzen keine Prüfung im Einzelfall.
        Illustrative Darstellung mit Beispieldaten.
      </p>
    </div>
  );
}

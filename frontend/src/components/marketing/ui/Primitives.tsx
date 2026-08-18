import Link from "next/link";
import React from "react";

import { IconArrowRight } from "./Icons";

/* ── Status-Chip ──────────────────────────────────────────────────── */

export type StatusTone = "ok" | "warn" | "crit" | "info" | "neutral";

export function StatusChip({
  tone,
  children,
  dot = true,
  className = "",
}: {
  tone: StatusTone;
  children: React.ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span className={`mk-chip mk-chip--${tone} ${className}`.trim()}>
      {dot ? <span className="mk-chip__dot" aria-hidden /> : null}
      {children}
    </span>
  );
}

/* ── Meter ────────────────────────────────────────────────────────── */

const METER_FILL: Record<StatusTone, string> = {
  ok: "mk-meter-fill-ok",
  warn: "mk-meter-fill-warn",
  crit: "mk-meter-fill-crit",
  info: "mk-meter-fill-accent",
  neutral: "mk-meter-fill-accent",
};

/**
 * Fortschrittsanzeige als SVG — die strikte CSP verbietet Inline-Styles,
 * dynamische Breiten laufen daher über SVG-Attribute statt über CSS.
 */
export function Meter({
  value,
  tone = "info",
  label,
  height = 6,
  className = "",
}: {
  value: number;
  tone?: StatusTone;
  label: string;
  height?: number;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <svg
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      height={height}
      width="100%"
      className={`block w-full ${className}`.trim()}
      role="img"
      aria-label={`${label}: ${clamped} Prozent`}
    >
      <rect
        x="0"
        y="0"
        width="100"
        height={height}
        rx={height / 2}
        className="mk-meter-track"
      />
      <rect
        x="0"
        y="0"
        width={clamped}
        height={height}
        rx={height / 2}
        className={METER_FILL[tone]}
      />
    </svg>
  );
}

export function toneForCoverage(value: number): StatusTone {
  if (value >= 85) return "ok";
  if (value >= 70) return "warn";
  return "crit";
}

/* ── Section-Bausteine ────────────────────────────────────────────── */

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="mk-eyebrow">{children}</p>;
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  id,
  align = "left",
  as: Tag = "h2",
}: {
  eyebrow?: string;
  title: React.ReactNode;
  lead?: React.ReactNode;
  id?: string;
  align?: "left" | "center";
  as?: "h1" | "h2" | "h3";
}) {
  const titleClass = Tag === "h1" ? "mk-h1" : "mk-h2";
  return (
    <div
      className={
        align === "center"
          ? "mx-auto max-w-3xl text-center"
          : "max-w-3xl"
      }
    >
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Tag id={id} className={`${titleClass} ${eyebrow ? "mt-3" : ""}`.trim()}>
        {title}
      </Tag>
      {lead ? (
        <p className={`mk-lead mt-4 ${align === "center" ? "mx-auto" : ""}`.trim()}>
          {lead}
        </p>
      ) : null}
    </div>
  );
}

/* ── Links & Buttons ──────────────────────────────────────────────── */

export function ArrowLink({
  href,
  children,
  className = "",
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      prefetch={false}
      className={`group inline-flex items-center gap-1.5 text-[0.8125rem] font-semibold text-[var(--mk-link)] no-underline transition-colors hover:text-[var(--mk-link-hover)] ${className}`.trim()}
    >
      {children}
      <IconArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

/* ── Produkt-Rahmen ───────────────────────────────────────────────── */

export function ProductFrame({
  title,
  breadcrumb,
  meta,
  children,
  className = "",
}: {
  title: string;
  breadcrumb?: string;
  meta?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <figure className={`mk-app-frame ${className}`.trim()}>
      <div className="mk-app-chrome">
        <span className="flex gap-1.5" aria-hidden>
          <span className="mk-dot" />
          <span className="mk-dot" />
          <span className="mk-dot" />
        </span>
        <span className="min-w-0 flex-1 truncate text-[0.6875rem] font-medium text-[var(--mk-fg-faint)]">
          {breadcrumb ? `${breadcrumb} / ` : ""}
          <span className="text-[var(--mk-fg-soft)]">{title}</span>
        </span>
        {meta ? <span className="shrink-0">{meta}</span> : null}
      </div>
      {children}
    </figure>
  );
}

/* ── Kennzahl-Kachel ──────────────────────────────────────────────── */

export function StatTile({
  label,
  value,
  suffix,
  hint,
  tone,
  meter,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  hint?: React.ReactNode;
  tone?: StatusTone;
  meter?: number;
}) {
  return (
    <div className="flex flex-col justify-between gap-3 p-4">
      <p className="mk-label">{label}</p>
      <p className="mk-kpi-value">
        {value}
        {suffix ? (
          <span className="ml-0.5 text-[0.5em] font-semibold text-[var(--mk-fg-faint)]">
            {suffix}
          </span>
        ) : null}
      </p>
      {typeof meter === "number" ? (
        <Meter value={meter} tone={tone ?? "info"} label={label} />
      ) : null}
      {hint ? (
        <p className="text-[0.6875rem] leading-snug text-[var(--mk-fg-faint)]">{hint}</p>
      ) : null}
    </div>
  );
}

/* ── Illustrationshinweis ─────────────────────────────────────────── */

export function IllustrativeNote({ children }: { children?: React.ReactNode }) {
  return (
    <p className="mt-3 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
      {children ??
        "Illustrative Produktansicht mit Beispieldaten der Musterindustrie GmbH. Keine Kundendaten."}
    </p>
  );
}

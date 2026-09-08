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

/* ── Flächen & Trenner ────────────────────────────────────────────────
 *
 * Die Bühnengrammatik des Hauses. Öffentliche Autoritätsflächen (Hero,
 * Abschluss, Kopf- und Fußzeile) liegen auf dunklem Petrol-Navy; Diagramme,
 * Tabellen und Produktansichten sind *Unterlagen auf dieser Bühne* und
 * behalten ihren Weißgrund. Die Rollen dafür stehen in `marketing.css`
 * (`.mk-stage` / `.mk-paper`); die Bausteine hier setzen keine eigenen Farben.
 * ------------------------------------------------------------------- */

/**
 * Messing-Haarlinie als Trenner. Läuft zu beiden Seiten aus, damit sie als
 * Lichtkante liest und nicht als Tabellenrahmen. Rein dekorativ — die
 * Gliederung trägt im Markup die Überschriftsebene.
 */
export function BrassRule({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`mk-brass-rule ${className}`.trim()} />;
}

/**
 * Dekoratives Blueprint-Raster hinter einer Bühnensektion. Liegt hinter dem
 * Inhalt, fängt keine Klicks und trägt keine Aussage — fällt es aus, bleibt
 * die Sektion vollständig lesbar.
 */
export function StageBackdrop({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`mk-blueprint-inverse mk-blueprint-fade pointer-events-none absolute inset-0 ${className}`.trim()}
    />
  );
}

/**
 * Passepartout: helle Unterlage in einer schmalen Messingfassung auf der
 * dunklen Bühne.
 *
 * Der Grund, warum das System überhaupt zwei Polaritäten kennt. Die
 * Blueprint-Diagramme, die Evidenzmatrix und die Produktansichten sind
 * inhaltlich *Dokumente*. Sie auf Navy umzuzeichnen hätte ihre technische
 * Lesbarkeit gekostet — 1px-Linien, Statusfarben und Monospace-Locator sind
 * auf Weiß kalibriert — und die vorhandene Bildsprache zerstört.
 */
export function PaperInset({
  children,
  className = "",
  frame = true,
}: {
  children: React.ReactNode;
  className?: string;
  /** `false` zeigt die Unterlage ohne Fassung — für Panels im Panel. */
  frame?: boolean;
}) {
  if (!frame) {
    return <div className={`mk-paper min-w-0 ${className}`.trim()}>{children}</div>;
  }
  return (
    <div className={`mk-mat min-w-0 ${className}`.trim()}>
      <div className="mk-paper min-w-0">{children}</div>
    </div>
  );
}

/* ── Section-Bausteine ────────────────────────────────────────────── */

/**
 * Sektionsmarke. Der Messingstrich davor kommt aus `.mk-eyebrow::before`,
 * damit er an keiner Einbindung versehentlich fehlt.
 */
export function Eyebrow({
  children,
  center = false,
}: {
  children: React.ReactNode;
  center?: boolean;
}) {
  return (
    <p className={center ? "mk-eyebrow mk-eyebrow-center" : "mk-eyebrow"}>{children}</p>
  );
}

/**
 * Sektionskopf nach dem Prinzip der Kernaussage zuerst.
 *
 * `title` trägt die Aussage, nicht das Thema — „Ein Control trägt sechs
 * Nachweispflichten" statt „Control Mapping". `lead` begründet sie. Wer nur
 * die Titel der Seite liest, hat damit die vollständige Argumentation; das
 * ist die Prüfbedingung dieser Ebene.
 */
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
  const centered = align === "center";
  return (
    <div className={centered ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow ? <Eyebrow center={centered}>{eyebrow}</Eyebrow> : null}
      <Tag id={id} className={`${titleClass} ${eyebrow ? "mt-3.5" : ""}`.trim()}>
        {title}
      </Tag>
      {lead ? (
        <p className={`mk-lead mt-4 ${centered ? "mx-auto" : ""}`.trim()}>{lead}</p>
      ) : null}
    </div>
  );
}

/* ── Exhibit ──────────────────────────────────────────────────────────
 *
 * Die Beweisführungsebene. Eine Abbildung ohne Nummer, Kernaussage und
 * Lesart ist auf dieser Seite Dekoration; mit ihnen ist sie ein Beleg — und
 * zitierbar: „Exhibit 4" lässt sich in einer Sitzung benennen, „die Grafik
 * weiter unten" nicht.
 *
 * Die Lesart steht bewusst *unter* der Abbildung. Sie erklärt, was zu sehen
 * ist, und wird erst nach dem Bild gebraucht.
 */
export function Exhibit({
  index,
  claim,
  children,
  basis,
  source = "Compliance Hub, Musterindustrie GmbH (Beispieldaten)",
  reading,
  className = "",
  paper = false,
}: {
  /** Laufende Nummer innerhalb der Seite. Beginnt bei 1 und bleibt lückenlos. */
  index: number;
  /** Die Kernaussage der Abbildung — nicht ihr Thema. */
  claim: React.ReactNode;
  children: React.ReactNode;
  /** Fachliche Grundlage, z. B. „EU AI Act Art. 9, ISO/IEC 42001 Kap. 6". */
  basis?: React.ReactNode;
  /** Datenherkunft. Standard weist die Ansicht als Beispieldaten aus. */
  source?: React.ReactNode;
  /** Wie die Abbildung zu lesen ist, wenn das nicht selbsterklärend ist. */
  reading?: React.ReactNode;
  className?: string;
  /** `true` rahmt die Abbildung als helle Unterlage — für Bühnensektionen. */
  paper?: boolean;
}) {
  const figure = paper ? <PaperInset>{children}</PaperInset> : children;

  return (
    <figure className={`mk-exhibit ${className}`.trim()}>
      <div className="mk-exhibit__head">
        <span className="mk-exhibit__index">Exhibit&nbsp;{index}</span>
      </div>
      <figcaption className="mk-exhibit__claim">{claim}</figcaption>
      <div className="min-w-0">{figure}</div>
      <dl className="mk-exhibit__source">
        {reading ? (
          <div>
            <dt>Lesart</dt>
            <dd>{reading}</dd>
          </div>
        ) : null}
        {basis ? (
          <div>
            <dt>Grundlage</dt>
            <dd>{basis}</dd>
          </div>
        ) : null}
        <div>
          <dt>Quelle</dt>
          <dd>{source}</dd>
        </div>
      </dl>
    </figure>
  );
}

/* ── Signal-Leiste ────────────────────────────────────────────────────
 *
 * Mehrere kurze Aussagen in *einer* Fläche, getrennt durch Haarlinien.
 * Bewusst kein Kachelraster: eine Kachelreihe liest sich als Badge-Wand,
 * eine geteilte Fläche als Leiste eines Geräts — und genau das ist die
 * Wirkung, die eine Prüfoberfläche tragen soll.
 */
export function SignalRail({
  items,
  ariaLabel,
  columns = 4,
  className = "",
}: {
  items: ReadonlyArray<{
    label: string;
    detail?: string;
    Icon?: (props: { className?: string }) => React.ReactElement;
  }>;
  ariaLabel: string;
  columns?: 2 | 3 | 4 | 5;
  className?: string;
}) {
  const columnClass = {
    2: "sm:grid-cols-2",
    3: "sm:grid-cols-3",
    4: "sm:grid-cols-2 lg:grid-cols-4",
    5: "sm:grid-cols-2 lg:grid-cols-5",
  }[columns];

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`mk-rail ${columnClass} ${className}`.trim()}
    >
      {items.map((item) => (
        <div key={item.label} className="flex min-w-0 items-start gap-3 px-4 py-4">
          {item.Icon ? (
            <item.Icon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-brass)]" />
          ) : null}
          <span className="min-w-0">
            <span className="block text-[0.8125rem] font-semibold leading-snug text-[var(--mk-fg)]">
              {item.label}
            </span>
            {item.detail ? (
              <span className="mt-0.5 block text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                {item.detail}
              </span>
            ) : null}
          </span>
        </div>
      ))}
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

/**
 * Kennzahl mit Messingstrich links.
 *
 * Der Strich ersetzt die farbige Statusleiste der Arbeitsflächen: auf einer
 * Marketingfläche wird keine Statusbedeutung behauptet, es geht um Gliederung.
 * Die Fußnote ist Pflicht — eine Zahl ohne ihre Grundlage ist auf einer
 * Seite, deren ganzes Argument Nachvollziehbarkeit ist, die falsche Geste.
 */
export function KeyFigure({
  label,
  value,
  detail,
  basis,
  className = "",
}: {
  label: string;
  value: string;
  detail?: string;
  /** Woher die Zahl kommt. Ohne Grundlage keine Zahl. */
  basis: string;
  className?: string;
}) {
  return (
    <div
      className={`relative min-w-0 overflow-hidden rounded-[8px] border border-[var(--mk-bd)] bg-[var(--mk-panel)] px-4 py-4 ${className}`.trim()}
    >
      <span
        aria-hidden
        className="absolute inset-y-0 left-0 w-[2px] bg-[var(--mk-brass)] opacity-70"
      />
      <p className="mk-label">{label}</p>
      <p className="mk-kpi-value mt-2.5">{value}</p>
      {detail ? (
        <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
          {detail}
        </p>
      ) : null}
      <p className="mt-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
        {basis}
      </p>
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

import Link from "next/link";
import React from "react";

import {
  IconCheck,
  IconKey,
  IconLayers,
  IconServer,
  IconShield,
  IconTenants,
} from "../ui/Icons";
import { ArrowLink, SignalRail, StatusChip } from "../ui/Primitives";
import { Reveal } from "../ui/Reveal";

/* ── Trust-Leiste ─────────────────────────────────────────────────── */

const TRUST_ITEMS = [
  { label: "EU-Hosting", detail: "Deutschland-Option", Icon: IconServer },
  {
    label: "DSGVO-orientierte Architektur",
    detail: "Datenminimierung by design",
    Icon: IconShield,
  },
  { label: "Audit Trail", detail: "Änderungen nachvollziehbar", Icon: IconLayers },
  { label: "SSO & Rollenmodell", detail: "SAML 2.0, Entra ID", Icon: IconKey },
  { label: "Mandantenfähig", detail: "Isolation je Mandant", Icon: IconTenants },
];

/**
 * Technische Eigenschaften als *eine* Leiste, nicht als Badge-Reihe.
 *
 * Die Aussagen sind bewusst prüfbar formuliert: „EU-Hosting mit
 * Deutschland-Option" ist eine Architekturangabe, „zertifiziert" wäre eine
 * Behauptung. Auf einer Fläche, deren Argument Nachweisbarkeit ist, darf
 * genau dieser Unterschied nicht verwischen.
 */
export function TrustBar() {
  return (
    <section
      aria-label="Technische Eigenschaften der Plattform"
      className="border-b border-[var(--mk-bd)] bg-[var(--mk-bg-subtle)]"
    >
      <div className="mk-container py-6 lg:py-7">
        <SignalRail
          items={TRUST_ITEMS}
          columns={5}
          ariaLabel="Technische Eigenschaften der Plattform"
        />
      </div>
    </section>
  );
}

/* ── Outcome-Streifen ─────────────────────────────────────────────── */

/**
 * Drei gleichrangige Ergebnisaussagen in einer geteilten Fläche.
 *
 * Die Trennlinien entstehen über `gap-px` auf der Linienfarbe statt über
 * `divide-x`: bei mehrzeiligem Raster setzt `divide-x` die Linie auch an den
 * Zeilenanfang und zeichnet Trenner, wo keine Trennung ist.
 */
export function OutcomeStrip({
  items,
}: {
  items: { title: string; detail: string }[];
}) {
  return (
    <ul className="mk-rail md:grid-cols-3">
      {items.map((item, index) => (
        <Reveal key={item.title} as="li" delay={(index % 3) as 0 | 1 | 2}>
          <div className="h-full p-5">
            <IconCheck className="h-4.5 w-4.5 text-[var(--mk-state-ok)]" />
            <p className="mt-3 text-[1rem] font-semibold leading-snug tracking-[-0.015em] text-[var(--mk-fg)]">
              {item.title}
            </p>
            <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
              {item.detail}
            </p>
          </div>
        </Reveal>
      ))}
    </ul>
  );
}

/* ── Persona-Karte ────────────────────────────────────────────────── */

export function PersonaSolutionCard({
  eyebrow,
  title,
  lead,
  bullets,
  ctaLabel,
  ctaHref,
  visual,
}: {
  eyebrow: string;
  title: string;
  lead: string;
  bullets: string[];
  ctaLabel: string;
  ctaHref: string;
  visual: React.ReactNode;
}) {
  return (
    <article className="mk-card flex h-full min-w-0 flex-col overflow-hidden">
      <div className="border-b border-[var(--mk-bd)] p-5 sm:p-6">
        <p className="mk-eyebrow">{eyebrow}</p>
        <h3 className="mk-h3 mt-3">{title}</h3>
        <p className="mt-3 text-[0.9375rem] leading-relaxed text-[var(--mk-fg-muted)]">
          {lead}
        </p>
        <ul className="mt-5 space-y-2.5">
          {bullets.map((bullet) => (
            <li
              key={bullet}
              className="grid grid-cols-[1rem_minmax(0,1fr)] gap-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-soft)]"
            >
              <IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-state-ok)]" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
        <Link href={ctaHref} prefetch={false} className="mk-btn mk-btn--secondary mt-6">
          {ctaLabel}
        </Link>
      </div>
      <div className="mt-auto min-w-0 bg-[var(--mk-panel-subtle)] p-4">{visual}</div>
    </article>
  );
}

/* ── Ressourcen-Karte ─────────────────────────────────────────────── */

export function ResourceCard({
  slug,
  kind,
  title,
  summary,
  readingTime,
  audience,
  href,
}: {
  slug: string;
  kind: string;
  title: string;
  summary: string;
  readingTime: string;
  audience: string;
  href: string;
}) {
  return (
    <article
      id={slug}
      className="mk-card mk-card-interactive flex h-full scroll-mt-28 flex-col p-5"
    >
      <div className="flex items-center justify-between gap-2">
        <StatusChip tone="neutral" dot={false}>
          {kind}
        </StatusChip>
        <span className="mk-mono text-[var(--mk-fg-faint)]">{readingTime}</span>
      </div>
      <h3 className="mk-h4 mt-3.5">{title}</h3>
      <p className="mt-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
        {summary}
      </p>
      <p className="mt-3 text-[0.6875rem] text-[var(--mk-fg-faint)]">Für: {audience}</p>
      <div className="mt-auto pt-4">
        <ArrowLink href={href}>Im Briefing anfordern</ArrowLink>
      </div>
    </article>
  );
}

/* ── Abschluss-CTA ────────────────────────────────────────────────── */

/**
 * Letzte Autoritätsfläche der Seite: dunkle Bühne, Messingkante nach oben,
 * genau eine Primäraktion. Die Fußnote sagt, was das Gespräch *nicht* ist —
 * Ehrlichkeit über die Grenze gehört bei diesem Produkt zur Zusage.
 */
export function CTASection({
  title = "Machen Sie Compliance steuerbar.",
  lead = "Sehen Sie in einer persönlichen Produkt-Tour, wie Sie KI-Governance, NIS2, ISO und Evidenzen in einem mandantenfähigen System zusammenführen.",
  primaryLabel = "Demo anfragen",
  primaryHref,
  secondaryLabel = "5-Minuten Produkt-Tour",
  secondaryHref,
  note = "Kein Verkaufsgespräch ohne Substanz: Wir arbeiten an Ihrem Geltungsbereich und Ihren Systemen. Keine Rechtsberatung.",
}: {
  title?: string;
  lead?: string;
  primaryLabel?: string;
  primaryHref: string;
  secondaryLabel?: string;
  secondaryHref: string;
  note?: string;
}) {
  return (
    <section className="mk-stage relative isolate overflow-hidden border-t border-[rgba(185,143,66,0.3)]">
      <div className="mk-container mk-section-tight relative">
        <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <div>
            <h2 className="mk-h2">{title}</h2>
            <p className="mk-lead mt-4">{lead}</p>
          </div>
          <div className="lg:justify-self-end">
            <div className="flex flex-wrap gap-3">
              <Link
                href={primaryHref}
                prefetch={false}
                className="mk-btn mk-btn--primary mk-btn--lg"
              >
                {primaryLabel}
              </Link>
              <Link
                href={secondaryHref}
                prefetch={false}
                className="mk-btn mk-btn--secondary mk-btn--lg"
              >
                {secondaryLabel}
              </Link>
            </div>
            <p className="mt-4 max-w-sm text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
              {note}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import React, { Suspense } from "react";

import { ContactLeadForm } from "@/components/contact/ContactLeadForm";
import { DemoRequestPathways } from "@/components/marketing/DemoRequestPathways";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { ComplianceScoreCard } from "@/components/marketing/visuals/ComplianceScoreCard";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";
import { isPublicSiteRelease } from "@/lib/releaseProfile";

export const metadata: Metadata = {
  title: "Demo anfragen",
  description:
    "Persönliche Produkt-Tour zu KI-Governance, EU AI Act, NIS2, ISO 42001 und Evidenzführung — an Ihrem Geltungsbereich, Ihren Systemen und Ihren offenen Nachweisen.",
  alternates: { canonical: MARKETING_ROUTES.demo },
};

const PREPARATION = [
  [
    "Bringen Sie einen echten Fall mit",
    "Ein KI-System, ein NIS2-Risiko oder ein offener Prüfpunkt sagt mehr als jede Folie.",
  ],
  [
    "Nennen Sie Ihre Regelwerke",
    "Welche Rechtsakte und Normen für Sie gelten, entscheidet über den Zuschnitt des Kontrollmodells.",
  ],
  [
    "Sagen Sie, wer beteiligt ist",
    "Compliance, IT-Sicherheit, Datenschutz und Fachbereich haben unterschiedliche Fragen — wir bereiten uns darauf vor.",
  ],
] as const;

function LeadFormFallback() {
  return (
    <p className="mk-card p-5 text-[0.875rem] text-[var(--mk-fg-muted)]">
      Formular wird geladen …
    </p>
  );
}

export default function DemoPage() {
  const publicSite = isPublicSiteRelease();

  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-12 lg:py-16">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:items-center">
            <div className="max-w-2xl">
              <p className="mk-eyebrow">Demo anfragen</p>
              <h1 className="mk-h1 mt-4">Machen Sie Compliance steuerbar.</h1>
              <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
                Sehen Sie in einer persönlichen Produkt-Tour, wie Sie KI-Governance, NIS2,
                ISO und Evidenzen in einem mandantenfähigen System zusammenführen — an
                Ihrem Geltungsbereich, nicht an einem Musterfall.
              </p>
              <ul className="mt-7 flex flex-wrap gap-2">
                <li>
                  <StatusChip tone="ok">45 Minuten</StatusChip>
                </li>
                <li>
                  <StatusChip tone="ok">Ohne Vorbereitungsaufwand</StatusChip>
                </li>
                <li>
                  <StatusChip tone="ok">Deutsch oder Englisch</StatusChip>
                </li>
              </ul>
              <p className="mt-6 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Wir beraten nicht rechtlich. Wir zeigen, wie Anforderungen strukturiert
                umgesetzt, belegt und berichtet werden.
              </p>
            </div>
            <div className="min-w-0">
              <ComplianceScoreCard />
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section" id="anfrage">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Anfrage"
              title="Welcher Einstieg passt zu Ihrem Ziel?"
              lead="Vier Formate mit unterschiedlichem Schwerpunkt. Sie wählen aus, wir bereiten das Gespräch entsprechend vor."
            />
          </Reveal>
          <div className="mt-8">
            {publicSite ? (
              <DemoRequestPathways />
            ) : (
              <div className="grid gap-6 lg:grid-cols-2">
                <DemoRequestPathways />
                <Suspense fallback={<LeadFormFallback />}>
                  <ContactLeadForm />
                </Suspense>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="mk-surface-subtle border-y border-[var(--mk-bd)]">
        <div className="mk-container mk-section-tight">
          <Reveal>
            <SectionHeading
              eyebrow="Vorbereitung"
              title="Drei Dinge machen das Gespräch nützlich."
              lead="Je konkreter der Ausgangspunkt, desto belastbarer ist das Ergebnis."
            />
          </Reveal>
          <ol className="mt-8 grid gap-4 md:grid-cols-3">
            {PREPARATION.map(([title, detail], index) => (
              <Reveal key={title} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <div className="mk-card h-full p-5">
                  <span className="mk-num flex h-7 w-7 items-center justify-center rounded-[7px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[0.75rem] font-bold text-[var(--mk-accent-700)]">
                    {index + 1}
                  </span>
                  <h3 className="mk-h4 mt-3">{title}</h3>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {detail}
                  </p>
                </div>
              </Reveal>
            ))}
          </ol>
          <p className="mt-8 text-[0.8125rem] text-[var(--mk-fg-muted)]">
            Lieber erst allein ansehen?{" "}
            <Link href={MARKETING_ROUTES.productTour} prefetch={false} className="mk-link">
              5-Minuten Produkt-Tour
            </Link>
          </p>
        </div>
      </section>
    </>
  );
}

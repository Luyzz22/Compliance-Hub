import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import { CTASection, ResourceCard } from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { RESOURCES } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";
import { contactPageHref } from "@/lib/publicContact";

export const metadata: Metadata = {
  title: "Ressourcen & Compliance Briefing",
  description:
    "EU AI Act Readiness Guide, ISO 42001 × EU AI Act Mapping, NIS2 Management-Checkliste, Board-Report-Vorlage und das DACH AI Governance Briefing.",
  alternates: { canonical: MARKETING_ROUTES.resources },
};

const briefingHref = contactPageHref({
  quelle: "ressourcen",
  ctaId: "ressourcen-briefing",
  ctaLabel: "Compliance Briefing",
});

const PERSPECTIVES: { title: string; lead: string; body: string[] }[] = [
  {
    title: "Warum Mapping vor Werkzeugauswahl kommt",
    lead: "Wer zuerst ein Tool wählt und danach das Kontrollmodell, baut die Doppelarbeit ein, die er abschaffen wollte.",
    body: [
      "In den meisten Häusern existieren bereits ein ISMS, ein Verarbeitungsverzeichnis und eine Liste offener Maßnahmen. Was fehlt, ist die Verbindung zwischen ihnen — nicht ein weiteres System daneben.",
      "Der praktikable Einstieg ist deshalb ein kleines, sauber gemapptes Kontrollset: Risikobeurteilung, Protokollierung, Lieferantenprüfung und menschliche Aufsicht decken einen erheblichen Teil dessen ab, was EU AI Act, ISO 42001, ISO 27001, NIS2 und DSGVO gemeinsam verlangen.",
    ],
  },
  {
    title: "Was ein Board wirklich entscheiden muss",
    lead: "Ein Gremium braucht keine Control-Liste, sondern drei Antworten: Wo stehen wir, was ist kritisch, was liegt bei uns.",
    body: [
      "Governance-Berichte scheitern selten an fehlenden Daten, sondern an fehlender Zuspitzung. Ein Board-Report, der 140 Controls auflistet, erzeugt Nachfragen statt Entscheidungen.",
      "Tragfähig ist die umgekehrte Reihenfolge: erst der Entscheidungsbedarf mit Frist und Konsequenz, dann die Lage, dann der Anhang für alle, die tiefer einsteigen wollen.",
    ],
  },
  {
    title: "AI Governance ist kein eigenes Managementsystem",
    lead: "Ein AIMS neben ISMS und Datenschutzorganisation zu betreiben, verdoppelt Aufwand ohne Erkenntnisgewinn.",
    body: [
      "ISO/IEC 42001 ist bewusst so aufgebaut, dass es sich in eine bestehende Managementsystemlandschaft einfügt. Rollen, Risikoprozess, Lieferantensteuerung und interne Prüfung existieren meist schon.",
      "Die Aufgabe besteht darin, die KI-spezifischen Ergänzungen sichtbar zu machen — Daten-Governance, menschliche Aufsicht, Transparenz gegenüber Betroffenen — und den Rest an das anzuschließen, was ohnehin läuft.",
    ],
  },
];

export default function ResourcesPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">Compliance Briefing</p>
            <h1 className="mk-h1 mt-4">
              Material, das Ihre Arbeit weiterbringt — nicht Ihren Posteingang füllt.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Leitfäden, Mappings und Vorlagen aus der Praxis von Industrie, Kanzleien und
              Beratungen im DACH-Raum. Fachlich belegt, ohne Verkaufstext und ohne
              Angstrhetorik.
            </p>
            <div className="mt-7">
              <Link
                href={briefingHref}
                prefetch={false}
                className="mk-btn mk-btn--primary mk-btn--lg"
              >
                Compliance Briefing anfordern
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Bibliothek */}
      <section className="mk-section" id="bibliothek">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Bibliothek"
              title="Fünf Arbeitsmittel, die wir regelmäßig aktualisieren."
              lead="Jedes Stück ist für eine konkrete Situation gemacht — und benennt, für wen es gedacht ist."
            />
          </Reveal>
          <ul className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {RESOURCES.map((resource, index) => (
              <Reveal key={resource.slug} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <ResourceCard {...resource} href={briefingHref} />
              </Reveal>
            ))}
          </ul>
          <p className="mt-6 max-w-3xl text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Alle Materialien sind fachliche Arbeitshilfen und stellen keine Rechtsberatung
            dar. Sie ersetzen keine Prüfung im Einzelfall und sichern keine Konformität zu.
          </p>
        </div>
      </section>

      {/* Standpunkte */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="standpunkte"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Standpunkte"
              title="Drei Thesen, die unsere Produktarbeit prägen."
              lead="Wir schreiben nur über das, was wir in Projekten tatsächlich beobachten."
            />
          </Reveal>
          <div className="mt-10 grid gap-8 lg:gap-10">
            {PERSPECTIVES.map((perspective, index) => (
              <Reveal key={perspective.title} delay={(index % 3) as 0 | 1 | 2}>
                <article className="grid gap-5 border-t border-[var(--mk-bd)] pt-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-10">
                  <div>
                    <StatusChip tone="neutral" dot={false}>
                      These {String(index + 1).padStart(2, "0")}
                    </StatusChip>
                    <h3 className="mk-h3 mt-3">{perspective.title}</h3>
                    <p className="mt-3 text-[0.9375rem] leading-relaxed text-[var(--mk-fg-soft)]">
                      {perspective.lead}
                    </p>
                  </div>
                  <div className="space-y-4">
                    {perspective.body.map((paragraph) => (
                      <p
                        key={paragraph.slice(0, 40)}
                        className="text-[0.9375rem] leading-[1.75] text-[var(--mk-fg-muted)]"
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Briefing */}
      <section className="mk-section" id="briefing">
        <div className="mk-container">
          <div className="mk-card grid gap-6 p-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-center lg:p-8">
            <div>
              <SectionHeading
                eyebrow="Quartalsformat"
                title="DACH AI Governance Briefing"
                lead="Einmal im Quartal: Umsetzungsstand, nationale Konkretisierungen und Praxisfragen, die uns aus Mittelstand und Beratung erreichen. Kein Newsletter-Rauschen."
              />
            </div>
            <div>
              <ul className="space-y-2.5">
                {[
                  "Was sich im Umsetzungsstand tatsächlich geändert hat",
                  "Welche Fragen aus Mandaten und Projekten wiederkehren",
                  "Welche Nachweise Prüfende zuerst sehen wollen",
                ].map((item) => (
                  <li
                    key={item}
                    className="grid grid-cols-[0.75rem_minmax(0,1fr)] gap-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]"
                  >
                    <span aria-hidden className="mt-[0.6rem] h-px bg-[var(--mk-accent-400)]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={briefingHref}
                prefetch={false}
                className="mk-btn mk-btn--primary mt-5"
              >
                Briefing anfordern
              </Link>
            </div>
          </div>
        </div>
      </section>

      <CTASection
        title="Lieber gleich am eigenen Fall arbeiten?"
        lead="In einer Produkt-Tour gehen wir Ihren Geltungsbereich, Ihre Systeme und Ihre offenen Nachweise durch — statt allgemeiner Folien."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
      />
    </>
  );
}

import type { Metadata } from "next";
import React from "react";

import { CTASection } from "@/components/marketing/sections/Sections";
import { SectionHeading } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { ProductTourSimulation } from "@/components/marketing/visuals/ProductTourSimulation";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "5-Minuten Produkt-Tour",
  description:
    "In fünf Schritten durch den Governance-Ablauf: Geltungsbereich, KI-Register, Risikoklassifizierung, Control Mapping und Board-Report — mit Beispieldaten der Musterindustrie GmbH.",
  alternates: { canonical: MARKETING_ROUTES.productTour },
};

export default function ProductTourPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-12 lg:py-16">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">Produkt-Tour · 5 Minuten</p>
            <h1 className="mk-h1 mt-4">
              Einmal durch den Ablauf — vom Geltungsbereich bis zum Board-Report.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Fünf Schritte am Beispiel der Musterindustrie GmbH. Sie steuern das Tempo
              selbst; nichts läuft automatisch weiter.
            </p>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <ProductTourSimulation />
        </div>
      </section>

      <section className="mk-surface-subtle border-y border-[var(--mk-bd)]">
        <div className="mk-container mk-section-tight">
          <Reveal>
            <SectionHeading
              eyebrow="Was die Tour nicht zeigt"
              title="Der Teil, der von Ihrer Organisation abhängt."
              lead="Eine Tour mit Beispieldaten kann den Ablauf zeigen, nicht die Passung. Das klären wir in einem Gespräch an Ihrem Fall."
            />
          </Reveal>
          <ul className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              [
                "Ihr Geltungsbereich",
                "Welche Standorte, Prozesse und Regelwerke tatsächlich einzubeziehen sind.",
              ],
              [
                "Ihre Systemlandschaft",
                "Welche Anbindung an ERP, Verzeichnis und Ticketsystem sinnvoll ist — und welche nicht.",
              ],
              [
                "Ihre Rollen",
                "Wer klassifiziert, wer prüft, wer freigibt und wie Vertretung geregelt wird.",
              ],
            ].map(([title, detail], index) => (
              <Reveal key={title} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <div className="mk-card h-full p-5">
                  <h3 className="mk-h4">{title}</h3>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {detail}
                  </p>
                </div>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      <CTASection
        title="Jetzt am eigenen Fall weitermachen."
        lead="In der persönlichen Demo arbeiten wir mit Ihrem Geltungsbereich, Ihren Systemen und Ihren offenen Nachweisen."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.platform}
        secondaryLabel="Plattform ansehen"
      />
    </>
  );
}

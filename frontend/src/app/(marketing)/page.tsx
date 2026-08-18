import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import {
  CTASection,
  OutcomeStrip,
  PersonaSolutionCard,
  ResourceCard,
  TrustBar,
} from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { BeforeAfterFlow } from "@/components/marketing/visuals/BeforeAfterFlow";
import { BoardReportPreview } from "@/components/marketing/visuals/BoardReportPreview";
import { ComplianceScoreCard } from "@/components/marketing/visuals/ComplianceScoreCard";
import { EvidenceTimeline } from "@/components/marketing/visuals/EvidenceTimeline";
import { FrameworkMappingGraph } from "@/components/marketing/visuals/FrameworkMappingGraph";
import { GovernanceFlow } from "@/components/marketing/visuals/GovernanceFlow";
import { HeroDashboardMockup } from "@/components/marketing/visuals/HeroDashboardMockup";
import { IntegrationArchitecture } from "@/components/marketing/visuals/IntegrationArchitecture";
import { ModuleGrid } from "@/components/marketing/visuals/ModuleGrid";
import { RiskHeatmap } from "@/components/marketing/visuals/RiskHeatmap";
import { SecurityArchitectureDiagram } from "@/components/marketing/visuals/SecurityArchitectureDiagram";
import { RESOURCES } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "Governance für AI, Security und Compliance",
  description:
    "Compliance Hub verbindet KI-Register, Controls, Evidenzen und Board-Reporting in einer mandantenfähigen Plattform für EU AI Act, NIS2, ISO 42001, ISO 27001 und DSGVO — für Industrie, Mittelstand und Beratungen im DACH-Raum.",
  alternates: { canonical: "/" },
};

const OUTCOMES = [
  {
    title: "Ein Kontrollmodell für mehrere Normen",
    detail:
      "Controls, Verantwortlichkeiten und Nachweise werden einmal gepflegt und über EU AI Act, ISO 42001, ISO 27001, NIS2 und DSGVO wiederverwendet.",
  },
  {
    title: "Auditfähige Evidenz statt Dokumentensuche",
    detail:
      "Jeder Nachweis trägt Herkunft, Version, Owner und Review-Zyklus. Der Prüfpfad entsteht im laufenden Betrieb, nicht kurz vor dem Termin.",
  },
  {
    title: "Board-Status in Minuten statt Projekt-Status-Meetings",
    detail:
      "Readiness, kritische Findings, Fristen und Entscheidungsbedarf liegen jederzeit in board-tauglicher Sprache vor.",
  },
];

export default function HomePage() {
  return (
    <>
      {/* 1 — Hero */}
      <section className="mk-dark relative overflow-hidden bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-20">
          <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-12">
            <div className="max-w-xl">
              <p className="mk-eyebrow">Governance-Layer für den DACH-Mittelstand</p>
              <h1 className="mk-display mt-4">
                Governance für AI, Security und Compliance — ohne Excel-Chaos.
              </h1>
              <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
                Compliance Hub verbindet KI-Register, Controls, Evidenzen und
                Board-Reporting in einer mandantenfähigen Plattform für Industrie,
                Mittelstand und Beratungen im DACH-Raum.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  href={MARKETING_ROUTES.demo}
                  prefetch={false}
                  className="mk-btn mk-btn--primary mk-btn--lg"
                >
                  Demo anfragen
                </Link>
                <Link
                  href={MARKETING_ROUTES.productTour}
                  prefetch={false}
                  className="mk-btn mk-btn--secondary mk-btn--lg"
                >
                  Produkt-Tour ansehen
                </Link>
              </div>
              <p className="mt-5 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Map once, comply many: ein Control, mehrere Nachweise — über EU AI Act,
                ISO 42001, ISO 27001/27701, NIS2 und DSGVO.
              </p>
            </div>

            <div className="min-w-0">
              <HeroDashboardMockup />
              <p className="mt-3 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Illustrative Produktansicht mit Beispieldaten der Musterindustrie GmbH.
                Keine Kundendaten.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 1b — Trust-Leiste */}
      <TrustBar />

      {/* 3 — Outcomes */}
      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* 4 — Problem */}
      <section className="mk-surface-subtle border-y border-[var(--mk-bd)]" id="problem">
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Ausgangslage"
              id="problem-heading"
              title="Compliance scheitert selten an Anforderungen. Sondern an fehlender Verbindung."
              lead="Die Pflichten sind bekannt. Was fehlt, ist der durchgehende Weg von der Erhebung über den Nachweis bis zur Entscheidung — und der Beleg, dass er eingehalten wurde."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-10">
              <BeforeAfterFlow />
            </div>
          </Reveal>
        </div>
      </section>

      {/* 5 — Produktablauf */}
      <section className="mk-section" id="ablauf">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Produktablauf"
              id="ablauf-heading"
              title="Von Scope zu Board-Readiness."
              lead="Vier Schritte, die aufeinander aufbauen. Jeder Schritt erzeugt Daten, die der nächste weiterverwendet — statt sie neu zu erheben."
            />
          </Reveal>
          <div className="mt-10">
            <GovernanceFlow />
          </div>
        </div>
      </section>

      {/* 6 — Module */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="module"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Module"
              id="module-heading"
              title="Sechs Bausteine, ein gemeinsamer Datenstand."
              lead="Jedes Modul arbeitet auf demselben Inventar und derselben Control-Bibliothek. Was Sie an einer Stelle pflegen, wirkt an allen anderen."
            />
          </Reveal>
          <div className="mt-10">
            <ModuleGrid />
          </div>
        </div>
      </section>

      {/* 7 — Framework Mapping */}
      <section className="mk-section" id="control-mapping">
        <div className="mk-container">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-12">
            <Reveal>
              <div className="lg:sticky lg:top-28">
                <SectionHeading
                  eyebrow="Control Mapping"
                  id="mapping-heading"
                  title="Ein Control. Mehrere Nachweise."
                  lead="Die Risikobeurteilung ist nicht sechs Mal zu führen, sondern einmal — und in sechs Regelwerken referenzierbar. Owner, Evidenz und Review-Zyklus bleiben dabei an einer Stelle."
                />
                <ul className="mt-6 space-y-3">
                  {[
                    "Referenzen auf Artikel- und Abschnittsebene statt pauschaler Zuordnung",
                    "Änderungen am Control werden in allen verbundenen Regimen sichtbar",
                    "Offene Zuordnungen bleiben offen, statt rechnerisch zu verschwinden",
                  ].map((item) => (
                    <li
                      key={item}
                      className="grid grid-cols-[0.75rem_minmax(0,1fr)] gap-2.5 text-[0.875rem] leading-relaxed text-[var(--mk-fg-muted)]"
                    >
                      <span
                        aria-hidden
                        className="mt-[0.65rem] h-px bg-[var(--mk-accent-400)]"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
            <Reveal delay={1}>
              <FrameworkMappingGraph />
            </Reveal>
          </div>
        </div>
      </section>

      {/* 8 — Zielgruppen */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="zielgruppen"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Lösungen"
              id="zielgruppen-heading"
              title="Zwei Ausgangslagen, dieselbe Methodik."
              lead="Ob eigenes Governance-Team im Industriebetrieb oder Mandantenbetreuung in der Kanzlei — das Kontrollmodell bleibt gleich, der Zuschnitt unterscheidet sich."
            />
          </Reveal>
          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            <Reveal>
              <PersonaSolutionCard
                eyebrow="Für Industrie & Mittelstand"
                title="Governance nahe an den Prozessen, die ohnehin laufen."
                lead="Fertigung, IT und Verwaltung nutzen KI und stehen zugleich unter NIS2- und ISO-Druck. Compliance Hub bringt beides in ein Modell."
                bullets={[
                  "AI Governance in produktionsnahen Prozessen, inklusive Sicherheitsbauteilen",
                  "NIS2- und ISO-Readiness mit einem gemeinsamen Risikoregister",
                  "ERP- und SAP-nahe Governance über Prozess- und Stammdatenbezug",
                  "Board-Reporting für Geschäftsleitung und Beirat",
                  "Integrationen mit Jira, Entra ID, SAP BTP und APIs",
                ]}
                ctaLabel="Plattform ansehen"
                ctaHref={MARKETING_ROUTES.platform}
                visual={<RiskHeatmap />}
              />
            </Reveal>
            <Reveal delay={1}>
              <PersonaSolutionCard
                eyebrow="Für Kanzleien & Beratungen"
                title="Mandantenbetreuung, die sich wiederholen lässt."
                lead="Standardisierte Assessments, getrennte Datenräume und Reports, die Ihren Namen tragen — statt jedes Mandat neu aufzusetzen."
                bullets={[
                  "Mandantenfähigkeit mit getrennten Datenräumen und Rollen",
                  "Standardisierte Assessment-Templates je Regelwerk",
                  "White-Label-fähige Reports für die Mandantenkommunikation",
                  "Wiederholbare Beratungs-Workflows statt Einzelprojekte",
                  "DATEV-nahe Exporte und strukturierte Evidenzdossiers",
                ]}
                ctaLabel="Für Beratungen ansehen"
                ctaHref={MARKETING_ROUTES.advisors}
                visual={<EvidenceTimeline />}
              />
            </Reveal>
          </div>
        </div>
      </section>

      {/* 9 — Board Level */}
      <section className="mk-section" id="board-reporting">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Board Level"
              id="board-heading"
              title="Vom Compliance-Projekt zur steuerbaren Management-Entscheidung."
              lead="Die Geschäftsführung braucht keine Control-Liste, sondern die Antwort auf drei Fragen: Wo stehen wir, was ist kritisch, was muss entschieden werden."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
              <BoardReportPreview />
              <ComplianceScoreCard />
            </div>
          </Reveal>
          <p className="mt-4 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Der Readiness-Score beschreibt den Bearbeitungsstand im System. Er ist kein
            Prüfergebnis und keine Konformitätsaussage.
          </p>
        </div>
      </section>

      {/* 10 — Integrationen */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="integrationen"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Integrationen"
              id="integrationen-heading"
              title="Governance dort, wo Ihre Prozesse bereits laufen."
              lead="Compliance Hub ersetzt kein ERP und kein Ticketsystem. Es verbindet, was dort entsteht, mit den Nachweisen, die verlangt werden."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-10">
              <IntegrationArchitecture />
            </div>
          </Reveal>
          <div className="mt-5">
            <Link href={MARKETING_ROUTES.integrations} prefetch={false} className="mk-link">
              Alle Integrationen und Anbindungswege
            </Link>
          </div>
        </div>
      </section>

      {/* 11 — Sicherheit */}
      <section className="mk-section" id="sicherheit">
        <div className="mk-container">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Sicherheit & Architektur"
                  id="sicherheit-heading"
                  title="Enterprise-Sicherheit, die zur Governance passt."
                  lead="Eine Plattform, die Nachweise führt, muss selbst nachweisbar sein. Deshalb sind die Kontrollen benannt und nicht als Versprechen formuliert."
                />
                <ul className="mt-6 space-y-3.5">
                  {[
                    ["Mandantenisolation auf Datenbankebene", "Row Level Security erzwingt die Trennung, nicht die Anwendungslogik."],
                    ["Rollenbasierte Zugriffe", "Rechte kommen aus dem Verzeichnis des Kunden, nicht aus lokalen Listen."],
                    ["Audit-Logs", "Änderungen und Freigaben sind verkettet und nachvollziehbar."],
                    ["Verschlüsselung", "In Transit und at Rest, mit getrennten Schlüsseln je Umgebung."],
                    ["SSO für das Enterprise-Onboarding", "SAML 2.0, Microsoft Entra ID und SAP IAS."],
                    ["EU-zentrierte Hosting-Architektur", "Betrieb in der EU mit Deutschland-Option."],
                  ].map(([title, detail]) => (
                    <li key={title} className="grid gap-1">
                      <span className="text-[0.875rem] font-semibold text-[var(--mk-fg)]">
                        {title}
                      </span>
                      <span className="text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                        {detail}
                      </span>
                    </li>
                  ))}
                </ul>
                <div className="mt-6 flex flex-wrap gap-2">
                  <StatusChip tone="ok">EU-Hosting</StatusChip>
                  <StatusChip tone="ok">SAML 2.0</StatusChip>
                  <StatusChip tone="ok">Audit Hash Chain</StatusChip>
                  <StatusChip tone="ok">PostgreSQL RLS</StatusChip>
                </div>
              </div>
            </Reveal>
            <Reveal delay={1}>
              <SecurityArchitectureDiagram />
            </Reveal>
          </div>
        </div>
      </section>

      {/* 12 — Ressourcen */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="ressourcen"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Compliance Briefing"
              id="ressourcen-heading"
              title="Material, das Ihre Arbeit weiterbringt."
              lead="Leitfäden, Mappings und Vorlagen aus der Praxis von Industrie, Kanzleien und Beratungen im DACH-Raum."
            />
          </Reveal>
          <ul className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {RESOURCES.slice(0, 3).map((resource, index) => (
              <Reveal key={resource.slug} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <ResourceCard
                  {...resource}
                  href={`${MARKETING_ROUTES.resources}#${resource.slug}`}
                />
              </Reveal>
            ))}
          </ul>
          <div className="mt-6">
            <Link href={MARKETING_ROUTES.resources} prefetch={false} className="mk-link">
              Alle Ressourcen im Compliance Briefing
            </Link>
          </div>
        </div>
      </section>

      {/* 13 — Abschluss-CTA */}
      <CTASection
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
      />
    </>
  );
}

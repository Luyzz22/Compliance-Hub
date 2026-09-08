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
import {
  BrassRule,
  Exhibit,
  KeyFigure,
  SectionHeading,
  StageBackdrop,
  StatusChip,
} from "@/components/marketing/ui/Primitives";
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

/**
 * Die Ergebniszusagen der Plattform.
 *
 * Jede beschreibt eine Zustandsänderung, keine Eigenschaft: „wird einmal
 * gepflegt und mehrfach verwendet" statt „umfassendes Control-Framework". Was
 * sich nicht als Zustandsänderung formulieren lässt, ist keine Zusage, sondern
 * eine Aufzählung — und gehört nicht an diese Stelle.
 */
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

/**
 * Die Ausgangslage in drei prüfbaren Größen.
 *
 * Jede Kennzahl nennt ihre Grundlage; `KeyFigure` erzwingt das über ein
 * Pflichtfeld. Regulatorische Fristen und Normstände sind belegbar — sie
 * stehen hier, weil sie nachschlagbar sind. Marktzahlen ohne benennbare
 * Quelle stehen nicht hier.
 */
const SITUATION_FIGURES = [
  {
    label: "Anwendbar ab",
    value: "08/2026",
    detail:
      "Die Pflichten für Hochrisiko-KI-Systeme nach EU AI Act greifen gestaffelt; der breite Anwendungszeitpunkt liegt im August 2026.",
    basis: "Verordnung (EU) 2024/1689, Art. 113",
  },
  {
    label: "Regelwerke im Zugriff",
    value: "5",
    detail:
      "EU AI Act, ISO/IEC 42001, ISO/IEC 27001, NIS2 und DSGVO greifen auf dieselben Controls und Nachweise zu.",
    basis: "Abgedeckte Regelwerke im Kontrollmodell der Plattform",
  },
  {
    label: "Leitungspflicht",
    value: "persönlich",
    detail:
      "NIS2 nimmt Leitungsorgane in die Billigungs- und Überwachungspflicht für Risikomanagementmaßnahmen.",
    basis: "Richtlinie (EU) 2022/2555, Art. 20",
  },
];

export default function HomePage() {
  return (
    <>
      {/* 1 — Hero: Bühne, Kernaussage, genau eine Primäraktion */}
      <section className="mk-stage relative isolate overflow-hidden">
        <StageBackdrop />
        <div className="mk-container relative py-14 lg:py-20">
          <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)] lg:gap-12">
            <div className="max-w-xl">
              <p className="mk-eyebrow">Governance-Layer für den DACH-Mittelstand</p>
              <h1 className="mk-display mt-4">
                Governance für AI, Security und Compliance — ohne Excel-Chaos.
              </h1>
              <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
                Compliance Hub verbindet KI-Register, Controls, Evidenzen und
                Board-Reporting in einer mandantenfähigen Plattform für
                Industrie, Mittelstand und Beratungen im DACH-Raum.
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
              <BrassRule className="mt-8 max-w-xs" />
              <p className="mt-4 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Map once, comply many: ein Control, mehrere Nachweise — über
                EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO.
              </p>
            </div>

            {/* Die Produktansicht ist eine Unterlage auf der Bühne: sie behält
                ihren Weißgrund, weil ihre 1px-Linien, Statusfarben und
                Monospace-Locator darauf kalibriert sind. */}
            <div className="min-w-0">
              <Exhibit
                index={1}
                paper
                claim="Der Governance-Stand einer Organisation auf einem Bildschirm."
                reading="Readiness je Regelwerk, offene Findings und fällige Reviews in einer Ansicht."
                source="Illustrative Produktansicht, Musterindustrie GmbH — keine Kundendaten"
              >
                <HeroDashboardMockup />
              </Exhibit>
            </div>
          </div>
        </div>
      </section>

      {/* 1b — Trust-Leiste */}
      <TrustBar />

      {/* 2 — Ausgangslage in prüfbaren Größen */}
      <section className="mk-section-tight" aria-labelledby="lage-heading">
        <div className="mk-container">
          <h2 id="lage-heading" className="sr-only">
            Ausgangslage in Zahlen
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {SITUATION_FIGURES.map((figure, index) => (
              <Reveal key={figure.label} delay={(index % 3) as 0 | 1 | 2}>
                <KeyFigure {...figure} className="h-full" />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 3 — Outcomes */}
      <section className="mk-section-tight pt-0">
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
              <Exhibit
                index={2}
                claim="Der Bruch liegt zwischen den Werkzeugen, nicht in den Anforderungen."
                reading="Links der heutige Ablauf über getrennte Ablagen, rechts derselbe Ablauf auf einem gemeinsamen Datenstand."
                basis="Typischer Ist-Ablauf in Organisationen ohne Governance-System"
                source="Compliance Hub, Ablaufmodell der Plattform"
              >
                <BeforeAfterFlow />
              </Exhibit>
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
            <Exhibit
              index={3}
              claim="Jeder Schritt übergibt Daten an den nächsten — erhoben wird einmal."
              reading="Von links nach rechts: Geltungsbereich, Kontrollmodell, Evidenz, Board-Output."
              source="Compliance Hub, Ablaufmodell der Plattform"
            >
              <GovernanceFlow />
            </Exhibit>
          </div>
        </div>
      </section>

      {/* 6 — Module */}
      <section className="mk-surface-subtle border-y border-[var(--mk-bd)]" id="module">
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
            <Exhibit
              index={4}
              claim="Sechs Module, aber nur ein Inventar und eine Control-Bibliothek."
              reading="Jede Kachel ist ein Modul; die gemeinsame Datenbasis liegt darunter, nicht daneben."
              source="Compliance Hub, Funktionsumfang der Plattform"
            >
              <ModuleGrid />
            </Exhibit>
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
                        className="mt-[0.65rem] h-px bg-[var(--mk-brass)]"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
            <Reveal delay={1}>
              <Exhibit
                index={5}
                claim="Eine gepflegte Risikobeurteilung bedient sechs Nachweispflichten."
                reading="Links das Control, rechts die Regelwerke; jede Linie ist eine Referenz auf Artikel- oder Abschnittsebene."
                basis="EU AI Act, ISO/IEC 42001, ISO/IEC 27001, ISO/IEC 27701, NIS2, DSGVO"
                source="Compliance Hub, Kontrollmodell der Plattform"
              >
                <FrameworkMappingGraph />
              </Exhibit>
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
            <div className="mt-9">
              <Exhibit
                index={6}
                claim="Drei Führungsfragen, beantwortet aus dem laufenden Betrieb."
                reading="Links der Board-Report mit Lage und Entscheidungsbedarf, rechts der Readiness-Stand je Regelwerk."
                source="Illustrative Produktansicht, Musterindustrie GmbH — keine Kundendaten"
              >
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
                  <BoardReportPreview />
                  <ComplianceScoreCard />
                </div>
              </Exhibit>
            </div>
          </Reveal>
          <p className="mt-4 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Der Readiness-Score beschreibt den Bearbeitungsstand im System. Er ist
            kein Prüfergebnis und keine Konformitätsaussage.
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
              <Exhibit
                index={7}
                claim="Die Plattform liest aus den führenden Systemen — sie ersetzt keines davon."
                reading="Quellsysteme links, Governance-Ebene in der Mitte, Nachweise und Reports rechts."
                source="Compliance Hub, Integrationsarchitektur"
              >
                <IntegrationArchitecture />
              </Exhibit>
            </div>
          </Reveal>
          <div className="mt-6">
            <Link
              href={MARKETING_ROUTES.integrations}
              prefetch={false}
              className="mk-link"
            >
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
                    [
                      "Mandantenisolation auf Datenbankebene",
                      "Row Level Security erzwingt die Trennung, nicht die Anwendungslogik.",
                    ],
                    [
                      "Rollenbasierte Zugriffe",
                      "Rechte kommen aus dem Verzeichnis des Kunden, nicht aus lokalen Listen.",
                    ],
                    [
                      "Audit-Logs",
                      "Änderungen und Freigaben sind verkettet und nachvollziehbar.",
                    ],
                    [
                      "Verschlüsselung",
                      "In Transit und at Rest, mit getrennten Schlüsseln je Umgebung.",
                    ],
                    [
                      "SSO für das Enterprise-Onboarding",
                      "SAML 2.0, Microsoft Entra ID und SAP IAS.",
                    ],
                    [
                      "EU-zentrierte Hosting-Architektur",
                      "Betrieb in der EU mit Deutschland-Option.",
                    ],
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
              <Exhibit
                index={8}
                claim="Die Mandantentrennung liegt in der Datenbank, nicht in der Anwendung."
                reading="Von außen nach innen: Zugang, Anwendungsebene, Datenhaltung mit Row Level Security je Mandant."
                source="Compliance Hub, Sicherheitsarchitektur"
              >
                <SecurityArchitectureDiagram />
              </Exhibit>
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

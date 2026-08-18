import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import {
  CTASection,
  OutcomeStrip,
  TrustBar,
} from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { BoardReportPreview } from "@/components/marketing/visuals/BoardReportPreview";
import { ComplianceScoreCard } from "@/components/marketing/visuals/ComplianceScoreCard";
import { EvidenceTimeline } from "@/components/marketing/visuals/EvidenceTimeline";
import { FrameworkMappingGraph } from "@/components/marketing/visuals/FrameworkMappingGraph";
import { GovernanceFlow } from "@/components/marketing/visuals/GovernanceFlow";
import { HeroDashboardMockup } from "@/components/marketing/visuals/HeroDashboardMockup";
import { ModuleGrid } from "@/components/marketing/visuals/ModuleGrid";
import { RiskHeatmap } from "@/components/marketing/visuals/RiskHeatmap";
import { FRAMEWORKS } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "Plattform",
  description:
    "Inventar, Control Mapping, Evidence Engine, Risikomanagement und Board-Reporting in einem Governance-Layer für EU AI Act, ISO 42001, ISO 27001/27701, NIS2 und DSGVO.",
  alternates: { canonical: MARKETING_ROUTES.platform },
};

const OUTCOMES = [
  {
    title: "Ein Datenstand für alle Regelwerke",
    detail:
      "Inventar, Controls und Evidenz liegen einmal vor. Jedes Regime greift darauf zu, statt eine eigene Erhebung zu starten.",
    },
  {
    title: "Verantwortung bleibt sichtbar",
    detail:
      "Jedes Control, jede Maßnahme und jeder Nachweis trägt eine benannte Person, eine Frist und einen Status.",
  },
  {
    title: "Nachweise sind vorlagefähig",
    detail:
      "Versionierte Evidenz mit Review-Zyklus und Prüfpfad — vorbereitet für Audit, Kanzlei oder Kunde.",
  },
];

export default function PlatformPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div className="max-w-xl">
              <p className="mk-eyebrow">Plattform</p>
              <h1 className="mk-h1 mt-4">
                Der Governance-Layer zwischen Ihren Systemen und Ihren Nachweispflichten.
              </h1>
              <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
                Compliance Hub führt KI-Systeme, Controls, Risiken und Evidenzen in einem
                Modell zusammen — mandantenfähig, auditierbar und anschlussfähig an
                bestehende ERP-, Identity- und Workflow-Landschaften.
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
                  5-Minuten Produkt-Tour
                </Link>
              </div>
            </div>
            <div className="min-w-0">
              <HeroDashboardMockup />
            </div>
          </div>
        </div>
      </section>

      <TrustBar />

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Regelwerke */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="regelwerke"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Abgedeckte Regelwerke"
              title="Sechs Regime, ein Kontrollmodell."
              lead="Die Plattform bildet die Anforderungen auf Artikel- und Abschnittsebene ab. Was mehrfach verlangt wird, wird einmal gepflegt."
            />
          </Reveal>
          <ul className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {FRAMEWORKS.map((framework, index) => (
              <Reveal key={framework.id} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <div className="mk-card h-full p-4">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="mk-h4">{framework.short}</h3>
                    <StatusChip tone="info" dot={false}>
                      im Kontrollmodell
                    </StatusChip>
                  </div>
                  <p className="mk-mono mt-2 text-[var(--mk-fg-faint)]">{framework.name}</p>
                  <p className="mt-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {framework.scope}
                  </p>
                </div>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      {/* Ablauf */}
      <section className="mk-section" id="ablauf">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Produktablauf"
              title="Von Scope zu Board-Readiness."
              lead="Vier Schritte, die aufeinander aufbauen — jeder erzeugt die Daten, mit denen der nächste arbeitet."
            />
          </Reveal>
          <div className="mt-10">
            <GovernanceFlow />
          </div>
        </div>
      </section>

      {/* Module */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="module"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Module"
              title="Sechs Bausteine auf einem gemeinsamen Datenstand."
              lead="Die Module sind keine getrennten Werkzeuge, sondern Sichten auf dasselbe Inventar und dieselbe Control-Bibliothek."
            />
          </Reveal>
          <div className="mt-10">
            <ModuleGrid />
          </div>
        </div>
      </section>

      {/* Control Mapping */}
      <section className="mk-section" id="control-mapping">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Control Mapping"
              title="Ein Control. Mehrere Nachweise."
              lead="Wählen Sie ein Control und sehen Sie, welche Anforderungen es in welchem Regelwerk bedient."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9">
              <FrameworkMappingGraph />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Evidence */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="evidence"
      >
        <div className="mk-container mk-section">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Evidence Engine"
                  title="Nachweise, die den Prüfpfad mitbringen."
                  lead="Ein Dokument in einem Ordner ist kein Nachweis. Erst Herkunft, Version, Owner und Review-Zyklus machen daraus Evidenz."
                />
                <ul className="mt-6 space-y-3.5">
                  {[
                    ["Versionierung statt Überschreiben", "Vorversionen bleiben referenzierbar, Verweise brechen nicht."],
                    ["Review-Zyklen mit Vorlauf", "Fällige Reviews werden sichtbar, bevor die Prüfung sie findet."],
                    ["Append-only Audit Trail", "Änderungen und Freigaben werden ergänzt, nicht ersetzt."],
                    ["Export für Prüfung und Mandant", "Dossiers mit Inhaltsverzeichnis, Zeitstempel und Prüfsumme."],
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
              </div>
            </Reveal>
            <Reveal delay={1}>
              <EvidenceTimeline />
            </Reveal>
          </div>
        </div>
      </section>

      {/* Risiko */}
      <section className="mk-section" id="risiko">
        <div className="mk-container">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-12">
            <Reveal>
              <RiskHeatmap />
            </Reveal>
            <Reveal delay={1}>
              <div>
                <SectionHeading
                  eyebrow="Risiko & Maßnahmen"
                  title="Risiken, die zu Entscheidungen führen."
                  lead="Bewertung, Priorisierung und Maßnahme hängen zusammen. Ein Risiko ohne Owner und Frist bleibt im System als offen sichtbar."
                />
                <ul className="mt-6 space-y-3">
                  {[
                    "Bewertung nach Auswirkung und Eintrittswahrscheinlichkeit, mit Begründung",
                    "Maßnahmen mit Owner, Frist, Priorität und Regelwerksbezug",
                    "Verknüpfung von Risiko, Control und Nachweis in einer Kette",
                    "Übergabe an Jira oder ServiceNow, ohne den Governance-Bezug zu verlieren",
                  ].map((item) => (
                    <li
                      key={item}
                      className="grid grid-cols-[0.75rem_minmax(0,1fr)] gap-2.5 text-[0.875rem] leading-relaxed text-[var(--mk-fg-muted)]"
                    >
                      <span aria-hidden className="mt-[0.65rem] h-px bg-[var(--mk-accent-400)]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Board Reporting */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="board-reporting"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Board Reporting"
              title="Der Stand, den die Geschäftsleitung wirklich braucht."
              lead="Lage, kritische Findings, Fristen und Entscheidungsbedarf — aus dem laufenden Betrieb erzeugt, nicht aus einer Sonderauswertung."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
              <BoardReportPreview />
              <ComplianceScoreCard />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Industrie-Anker */}
      <section className="mk-section" id="industrie">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Für Industrie & Mittelstand"
              title="Governance, die den Betrieb nicht ausbremst."
              lead="Zwischen 50 und 200 Mitarbeitenden gibt es selten ein eigenes AI-Governance-Team. Die Plattform arbeitet deshalb mit den Rollen, die tatsächlich vorhanden sind."
            />
          </Reveal>
          <ul className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["Produktionsnahe KI", "Sicherheitsbauteile, Qualitätsprüfung und Instandhaltung werden mit ihrem regulatorischen Bezug erfasst."],
              ["NIS2 im Betrieb", "OT-Themen, Lieferkette und Meldeketten liegen im selben Risikoregister wie die IT."],
              ["ERP-Nähe", "Organisations- und Prozessdaten aus S/4HANA oder Dynamics geben dem Inventar seinen Kontext."],
              ["Leitungsebene", "Der Board-Report übersetzt den Stand in Entscheidungen, ohne Fachjargon zu verlieren."],
            ].map(([title, detail], index) => (
              <Reveal key={title} as="li" delay={(index % 4) as 0 | 1 | 2 | 3}>
                <div className="mk-card h-full p-4">
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
        title="Sehen Sie die Plattform an Ihrem Geltungsbereich."
        lead="Wir gehen Ihren Scope, Ihre Systeme und Ihre Regelwerke durch und zeigen, wie das Kontrollmodell dafür aussieht."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
      />
    </>
  );
}

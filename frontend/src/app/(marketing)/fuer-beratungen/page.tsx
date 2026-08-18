import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import { CTASection, OutcomeStrip } from "@/components/marketing/sections/Sections";
import {
  Meter,
  SectionHeading,
  StatusChip,
  toneForCoverage,
} from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { EvidenceTimeline } from "@/components/marketing/visuals/EvidenceTimeline";
import { ADVISOR_PORTFOLIO } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "Für Kanzleien & Beratungen",
  description:
    "Mandantenfähige Governance-Plattform für Steuerberater, Wirtschaftsprüfer, GRC-Beratungen und AI-Governance-Boutiquen: getrennte Datenräume, Templates, White-Label-Reports und DATEV-nahe Exporte.",
  alternates: { canonical: MARKETING_ROUTES.advisors },
};

const OUTCOMES = [
  {
    title: "Ein Mandat aufsetzen statt neu erfinden",
    detail:
      "Assessment-Templates, Control-Bibliothek und Reportstruktur sind vorhanden. Neue Mandate starten mit dem, was sich bewährt hat.",
  },
  {
    title: "Getrennte Datenräume, gemeinsame Methodik",
    detail:
      "Jeder Mandant arbeitet in seinem eigenen Raum. Ihre Systematik bleibt über alle Mandate hinweg dieselbe.",
  },
  {
    title: "Berichte, die Ihren Namen tragen",
    detail:
      "White-Label-fähige Reports und Evidenzdossiers gehen als Ihre Arbeit an den Mandanten — nicht als Werkzeugausdruck.",
  },
];

const WORKFLOW = [
  {
    step: "Aufnahme",
    detail:
      "Mandant anlegen, Geltungsbereich und Regelwerke wählen, Template zuweisen. Rollen für Mandant und Kanzlei werden getrennt vergeben.",
  },
  {
    step: "Assessment",
    detail:
      "Standardisierte Fragestrecken je Regelwerk. Antworten, Belege und offene Punkte bleiben am Mandanten dokumentiert.",
  },
  {
    step: "Befund & Maßnahmen",
    detail:
      "Lücken werden zu terminierten Maßnahmen mit Owner beim Mandanten — nachverfolgbar ohne Rückfrage per E-Mail.",
  },
  {
    step: "Bericht & Übergabe",
    detail:
      "Report, Evidenzdossier und Exportpaket in Ihrem Layout. Der Mandant behält den Zugang zu seinem Datenraum.",
  },
];

const ROLES: [string, string][] = [
  ["Partner / Verantwortliche:r", "Portfoliosicht über alle Mandate, Freigabe von Berichten"],
  ["Projektleitung", "Führt ein oder mehrere Mandate, weist Maßnahmen zu"],
  ["Bearbeitung", "Arbeitet im zugewiesenen Mandantenraum, ohne Sicht auf andere Mandate"],
  ["Mandant · Fachrolle", "Pflegt eigene Systeme und Nachweise, sieht nur den eigenen Raum"],
  ["Mandant · Leitung", "Sieht Board-Report und Entscheidungsbedarf, ohne Bearbeitungsrechte"],
];

export default function AdvisorsPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">Für Kanzleien & Beratungen</p>
            <h1 className="mk-h1 mt-4">
              Mandantenbetreuung, die sich skalieren lässt.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Steuerberatung, Wirtschaftsprüfung, GRC- und ISMS-Beratung sowie
              AI-Governance-Boutiquen führen ihre Mandate in getrennten Datenräumen — mit
              einer gemeinsamen Methodik, wiederverwendbaren Templates und Berichten im
              eigenen Layout.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href={MARKETING_ROUTES.demo}
                prefetch={false}
                className="mk-btn mk-btn--primary mk-btn--lg"
              >
                Partner-Demo anfragen
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
        </div>
      </section>

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Portfolio-Cockpit */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="portfolio"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Portfolio-Cockpit"
              title="Alle Mandate auf einem Blatt."
              lead="Wo steht welches Mandat, wo läuft eine Frist, wo droht die Eskalation — bevor der Mandant anruft."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mk-card mt-9 overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
                <p className="mk-label">Mandantenportfolio · Kanzlei-Workspace</p>
                <p className="mk-mono text-[var(--mk-fg-faint)]">
                  {ADVISOR_PORTFOLIO.length} aktive Mandate
                </p>
              </div>
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">Mandant</th>
                      <th scope="col">Branche</th>
                      <th scope="col">Regelwerke</th>
                      <th scope="col" className="min-w-[9rem]">
                        Readiness
                      </th>
                      <th scope="col" className="mk-th-num">
                        Offen
                      </th>
                      <th scope="col">Nächste Frist</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ADVISOR_PORTFOLIO.map((mandant) => (
                      <tr key={mandant.mandant}>
                        <td className="font-medium text-[var(--mk-fg)]">
                          {mandant.mandant}
                        </td>
                        <td className="whitespace-nowrap">{mandant.branche}</td>
                        <td className="whitespace-nowrap text-[var(--mk-fg-muted)]">
                          {mandant.regime}
                        </td>
                        <td>
                          <span className="flex items-center gap-2">
                            <span className="min-w-[4rem] flex-1">
                              <Meter
                                value={mandant.readiness}
                                tone={toneForCoverage(mandant.readiness)}
                                label={`Readiness ${mandant.mandant}`}
                                height={5}
                              />
                            </span>
                            <span className="mk-num shrink-0 font-semibold text-[var(--mk-fg)]">
                              {mandant.readiness}%
                            </span>
                          </span>
                        </td>
                        <td className="mk-td-num">
                          <StatusChip
                            tone={
                              mandant.open >= 8 ? "crit" : mandant.open >= 4 ? "warn" : "ok"
                            }
                            dot={false}
                          >
                            {mandant.open}
                          </StatusChip>
                        </td>
                        <td className="mk-num whitespace-nowrap">{mandant.next}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Illustrative Ansicht mit Beispieldaten. Mandanten sehen ausschließlich den
                eigenen Datenraum.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Workflow */}
      <section className="mk-section" id="workflow">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Beratungs-Workflow"
              title="Vier Schritte, die sich in jedem Mandat wiederholen."
              lead="Der Ablauf ist derselbe, die Inhalte sind mandantenspezifisch. Das macht Aufwand kalkulierbar und Ergebnisse vergleichbar."
            />
          </Reveal>
          <ol className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {WORKFLOW.map((item, index) => (
              <Reveal key={item.step} as="li" delay={(index % 4) as 0 | 1 | 2 | 3}>
                <div className="mk-card h-full p-4">
                  <span className="mk-num flex h-7 w-7 items-center justify-center rounded-[7px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[0.75rem] font-bold text-[var(--mk-accent-700)]">
                    {index + 1}
                  </span>
                  <h3 className="mk-h4 mt-3">{item.step}</h3>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {item.detail}
                  </p>
                </div>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* Rollen & Exporte */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="rollen"
      >
        <div className="mk-container mk-section">
          <div className="grid gap-10 lg:grid-cols-2 lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Rollen & Trennung"
                  title="Wer was sieht, ist eine Einstellung — keine Absprache."
                  lead="Mandantenisolation wird auf Datenbankebene erzwungen. Rollen regeln darüber hinaus, welche Sicht und welche Rechte gelten."
                />
                <div className="mk-card mt-6 overflow-hidden">
                  <div className="mk-table-scroll">
                    <table className="mk-table">
                      <thead>
                        <tr>
                          <th scope="col">Rolle</th>
                          <th scope="col">Sicht und Rechte</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ROLES.map(([role, scope]) => (
                          <tr key={role}>
                            <td className="whitespace-nowrap font-medium text-[var(--mk-fg)]">
                              {role}
                            </td>
                            <td className="text-[var(--mk-fg-muted)]">{scope}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </Reveal>

            <Reveal delay={1}>
              <div>
                <SectionHeading
                  eyebrow="Übergabe"
                  title="Exporte, die beim Mandanten ankommen."
                  lead="Das Ergebnis Ihrer Arbeit verlässt die Plattform in einer Form, die weiterverwendet werden kann."
                />
                <ul className="mt-6 grid gap-3">
                  {[
                    ["White-Label-Report", "Ihr Layout, Ihre Struktur, Ihre Freigabe."],
                    ["Evidenzdossier", "Nachweise mit Inhaltsverzeichnis, Zeitstempel und Prüfsumme."],
                    ["Maßnahmenplan", "Offene Punkte mit Owner und Frist beim Mandanten."],
                    ["DATEV-naher Export", "Strukturierte Übergabe in kanzleiübliche Ablagen."],
                  ].map(([title, detail]) => (
                    <li key={title} className="mk-card p-4">
                      <h3 className="mk-h4">{title}</h3>
                      <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                        {detail}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Evidenz */}
      <section className="mk-section" id="nachweisfuehrung">
        <div className="mk-container">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Nachweisführung"
                  title="Ihre Arbeit bleibt belegbar — auch Jahre später."
                  lead="Wer wann was geprüft und freigegeben hat, steht im Prüfpfad. Das schützt das Mandat und Ihre eigene Dokumentation."
                />
                <ul className="mt-6 space-y-3">
                  {[
                    "Append-only Änderungshistorie je Mandant",
                    "Freigaben mit Person, Zeitpunkt und Bezugsobjekt",
                    "Versionierte Nachweise ohne Überschreiben",
                    "Aufbewahrung und Löschung nach vereinbarten Fristen",
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
            <Reveal delay={1}>
              <EvidenceTimeline />
            </Reveal>
          </div>
        </div>
      </section>

      <CTASection
        title="Sprechen wir über Ihr Mandatsportfolio."
        lead="Wir zeigen den Kanzlei-Workspace an einem Beispielmandat und klären Rollen, Templates, Reportlayout und Exportwege."
        primaryLabel="Partner-Demo anfragen"
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
        note="Wir arbeiten mit Kanzleien und Beratungen als Partner, nicht in Konkurrenz zum Mandatsgeschäft. Keine Rechtsberatung."
      />
    </>
  );
}

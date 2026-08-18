import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import { CTASection, OutcomeStrip } from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { RiskHeatmap } from "@/components/marketing/visuals/RiskHeatmap";
import { ACTION_PLAN, NIS2_RISKS } from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "NIS2 & KRITIS",
  description:
    "Risikomanagementmaßnahmen nach Art. 21 NIS2, Meldeprozesse nach Art. 23, Lieferkettenrisiken und Nachweise für die Leitungsebene — in einem gemeinsamen Register mit ISO 27001.",
  alternates: { canonical: MARKETING_ROUTES.nis2 },
};

const OUTCOMES = [
  {
    title: "Ein Risikoregister für IT und OT",
    detail:
      "Fertigung, Fernwartung und Verwaltung werden nach denselben Kriterien bewertet — mit Owner, Behandlung und Frist.",
  },
  {
    title: "Meldeketten, die geprobt sind",
    detail:
      "Die Fristen aus Art. 23 sind hinterlegt, die Verantwortlichkeiten benannt und der Ablauf dokumentiert.",
  },
  {
    title: "Nachweise für die Leitungsebene",
    detail:
      "Art. 20 nimmt die Geschäftsleitung in die Pflicht. Schulungsnachweis, Freigaben und Kenntnisnahme bleiben belegbar.",
  },
];

const MEASURES: [string, string, string][] = [
  ["Art. 21 Abs. 2 a", "Risikoanalyse und Sicherheitskonzepte", "Gemeinsames Register mit ISO 27001 6.1.2"],
  ["Art. 21 Abs. 2 b", "Bewältigung von Sicherheitsvorfällen", "Incident-Prozess, Protokollierung, Nachbereitung"],
  ["Art. 21 Abs. 2 c", "Betriebskontinuität und Krisenmanagement", "Backup, Wiederanlauf, getestete Verfahren"],
  ["Art. 21 Abs. 2 d", "Sicherheit der Lieferkette", "Lieferantenbewertung, Vertragsklauseln, Abhängigkeiten"],
  ["Art. 21 Abs. 2 e", "Sicherheit bei Beschaffung und Entwicklung", "Schwachstellenmanagement, Änderungsprozesse"],
  ["Art. 21 Abs. 2 f", "Bewertung der Wirksamkeit", "Kennzahlen, interne Prüfungen, Korrekturmaßnahmen"],
  ["Art. 21 Abs. 2 g", "Cyberhygiene und Schulungen", "Awareness, Nachweise, Wiederholungszyklen"],
  ["Art. 21 Abs. 2 h", "Kryptografie und Verschlüsselung", "Richtlinie, Geltungsbereich, Ausnahmen"],
  ["Art. 21 Abs. 2 i", "Personalsicherheit und Zugriffskontrolle", "Rezertifizierung, Rollen, Berechtigungskonzept"],
  ["Art. 21 Abs. 2 j", "Multi-Faktor-Authentifizierung", "Abdeckung je Zugang, inklusive Fernwartung"],
];

const REPORTING: [string, string, string][] = [
  ["unverzüglich, spätestens 24 h", "Frühwarnung", "Erste Meldung an die zuständige Stelle mit ersten Anhaltspunkten"],
  ["spätestens 72 h", "Meldung des Vorfalls", "Bewertung, Schweregrad, Auswirkungen und bekannte Indikatoren"],
  ["auf Anforderung", "Zwischenbericht", "Aktualisierter Stand während der Bearbeitung"],
  ["spätestens 1 Monat", "Abschlussbericht", "Ursache, ergriffene Maßnahmen, grenzüberschreitende Auswirkungen"],
];

export default function Nis2Page() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">NIS2 · KRITIS</p>
            <h1 className="mk-h1 mt-4">
              Risiken, Maßnahmen und Meldewege — in einem Register statt in vier Tabellen.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Compliance Hub führt die Risikomanagementmaßnahmen nach Art. 21, die
              Meldepflichten nach Art. 23 und die Verantwortung der Leitungsebene nach
              Art. 20 mit Ihrem bestehenden ISMS zusammen.
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
                href={`${MARKETING_ROUTES.resources}#nis2-management-checkliste`}
                prefetch={false}
                className="mk-btn mk-btn--secondary mk-btn--lg"
              >
                Management-Checkliste
              </Link>
            </div>
            <p className="mt-6 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
              Ob und in welchem Umfang Ihre Organisation in den Anwendungsbereich fällt,
              ist rechtlich zu prüfen. Die Plattform unterstützt die Umsetzung, nicht die
              rechtliche Bewertung.
            </p>
          </div>
        </div>
      </section>

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Maßnahmen */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="massnahmen"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Art. 21"
              title="Zehn Maßnahmenbereiche, geführt wie Controls."
              lead="Jeder Bereich wird als Control geführt: mit Status, Owner, Nachweis und Bezug zu ISO 27001, damit ein bestehendes ISMS nicht doppelt gepflegt wird."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 overflow-hidden rounded-[14px] border border-[var(--mk-bd)] bg-white">
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">Referenz</th>
                      <th scope="col">Maßnahmenbereich</th>
                      <th scope="col">Was dafür geführt wird</th>
                    </tr>
                  </thead>
                  <tbody>
                    {MEASURES.map(([reference, area, detail]) => (
                      <tr key={reference}>
                        <td className="mk-mono whitespace-nowrap font-semibold text-[var(--mk-accent-700)]">
                          {reference}
                        </td>
                        <td className="font-medium text-[var(--mk-fg)]">{area}</td>
                        <td className="text-[var(--mk-fg-muted)]">{detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Risikoregister */}
      <section className="mk-section" id="risikoregister">
        <div className="mk-container">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-12">
            <Reveal>
              <RiskHeatmap />
            </Reveal>
            <Reveal delay={1}>
              <div>
                <SectionHeading
                  eyebrow="Risikoregister"
                  title="Bewertet, priorisiert, mit Verantwortung versehen."
                  lead="Die Heatmap ist kein Selbstzweck: Jede Zelle führt zu Risiken, jedes Risiko zu einer Behandlung und einer benannten Person."
                />
                <div className="mk-card mt-6 overflow-hidden">
                  <div className="border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
                    <p className="mk-label">Register-Auszug</p>
                  </div>
                  <div className="mk-table-scroll">
                    <table className="mk-table">
                      <thead>
                        <tr>
                          <th scope="col">ID</th>
                          <th scope="col">Risiko</th>
                          <th scope="col">Owner</th>
                          <th scope="col">Behandlung</th>
                        </tr>
                      </thead>
                      <tbody>
                        {NIS2_RISKS.slice(0, 5).map((risk) => (
                          <tr key={risk.id}>
                            <td className="mk-mono whitespace-nowrap text-[var(--mk-fg-faint)]">
                              {risk.id}
                            </td>
                            <td>
                              <span className="block font-medium text-[var(--mk-fg)]">
                                {risk.title}
                              </span>
                              <span className="mk-mono block text-[var(--mk-fg-faint)]">
                                {risk.reference}
                              </span>
                            </td>
                            <td className="whitespace-nowrap">{risk.owner}</td>
                            <td className="whitespace-nowrap">
                              <StatusChip tone="neutral" dot={false}>
                                {risk.treatment}
                              </StatusChip>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Meldewege */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="meldewege"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Art. 23"
              title="Meldefristen, die im Ernstfall tragen."
              lead="Die Fristen sind bekannt. Entscheidend ist, dass Zuständigkeit, Inhalt und Weg vorher feststehen und mindestens einmal geprobt wurden."
            />
          </Reveal>
          <Reveal delay={1}>
            <ol className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {REPORTING.map(([deadline, title, detail], index) => (
                <li key={title} className="mk-card h-full p-4">
                  <div className="flex items-center gap-2.5">
                    <span className="mk-num flex h-7 w-7 items-center justify-center rounded-[7px] border border-[var(--mk-accent-100)] bg-[var(--mk-accent-50)] text-[0.75rem] font-bold text-[var(--mk-accent-700)]">
                      {index + 1}
                    </span>
                    <StatusChip tone={index === 0 ? "crit" : "neutral"} dot={false}>
                      {deadline}
                    </StatusChip>
                  </div>
                  <h3 className="mk-h4 mt-3">{title}</h3>
                  <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {detail}
                  </p>
                </li>
              ))}
            </ol>
          </Reveal>
          <p className="mt-4 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
            Fristen und Adressaten richten sich nach der nationalen Umsetzung. Die
            konkrete Ausgestaltung ist mit Ihrer Rechtsberatung abzustimmen.
          </p>
        </div>
      </section>

      {/* Maßnahmenplan */}
      <section className="mk-section" id="massnahmenplan">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Umsetzung"
              title="Vom Befund zur terminierten Maßnahme."
              lead="Jede Lücke wird zu einer Maßnahme mit Owner, Frist und Regelwerksbezug — und bleibt bis zum Abschluss im Board-Report sichtbar."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mk-card mt-9 overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
                <p className="mk-label">Maßnahmenplan · Musterindustrie GmbH</p>
                <p className="mk-mono text-[var(--mk-fg-faint)]">7 offene Maßnahmen</p>
              </div>
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">ID</th>
                      <th scope="col">Maßnahme</th>
                      <th scope="col">Owner</th>
                      <th scope="col">Fällig</th>
                      <th scope="col">Regelwerk</th>
                      <th scope="col">Priorität</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ACTION_PLAN.map((action) => (
                      <tr key={action.id}>
                        <td className="mk-mono whitespace-nowrap text-[var(--mk-fg-faint)]">
                          {action.id}
                        </td>
                        <td className="font-medium text-[var(--mk-fg)]">{action.title}</td>
                        <td className="whitespace-nowrap">
                          <span className="block">{action.owner}</span>
                          <span className="block text-[0.625rem] text-[var(--mk-fg-faint)]">
                            {action.ownerRole}
                          </span>
                        </td>
                        <td className="mk-num whitespace-nowrap">{action.due}</td>
                        <td className="whitespace-nowrap">
                          <span className="block">{action.framework}</span>
                          <span className="mk-mono block text-[var(--mk-fg-faint)]">
                            {action.reference}
                          </span>
                        </td>
                        <td className="whitespace-nowrap">
                          <StatusChip
                            tone={
                              action.priority === "kritisch"
                                ? "crit"
                                : action.priority === "hoch"
                                  ? "warn"
                                  : "neutral"
                            }
                          >
                            {action.priority}
                          </StatusChip>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <CTASection
        title="Bringen Sie Ihr NIS2-Register in einen prüfbaren Zustand."
        lead="Wir sehen uns Ihr bestehendes Risikoregister an und zeigen, wie Maßnahmen, Nachweise und Meldewege zusammengeführt werden."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
      />
    </>
  );
}

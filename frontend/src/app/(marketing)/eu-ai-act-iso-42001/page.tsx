import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import { CTASection, OutcomeStrip } from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { EvidenceTimeline } from "@/components/marketing/visuals/EvidenceTimeline";
import { FrameworkMappingGraph } from "@/components/marketing/visuals/FrameworkMappingGraph";
import {
  AI_SYSTEM_REGISTER,
  RISK_CLASS_LABEL,
  SYSTEM_STATUS_LABEL,
} from "@/lib/marketing/demoData";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "EU AI Act & ISO 42001",
  description:
    "KI-Systeme erfassen, nach EU AI Act klassifizieren, Anforderungen belegen und mit ISO/IEC 42001 verbinden — mit Prüfpfad, Verantwortlichkeit und Technical-File-Struktur.",
  alternates: { canonical: MARKETING_ROUTES.aiAct },
};

const OUTCOMES = [
  {
    title: "Klassifizierung mit Begründung",
    detail:
      "Jede Einstufung bleibt mit Fragestrecke, Begründung und bestätigender Person am System hinterlegt — auch nach einem Wechsel im Team.",
  },
  {
    title: "AIMS und Rechtsakt gemeinsam führen",
    detail:
      "ISO/IEC 42001 liefert das Managementsystem, der EU AI Act die Pflichten. Beide greifen auf dieselben Controls und Nachweise zu.",
  },
  {
    title: "Technical File als Nebenprodukt",
    detail:
      "Was für Anhang IV verlangt wird, entsteht aus dem laufenden Betrieb: Systembeschreibung, Daten, Aufsicht, Protokollierung.",
  },
];

const REQUIREMENTS: [string, string, string][] = [
  ["Art. 9", "Risikomanagementsystem", "Fortlaufender Prozess über den Lebenszyklus, dokumentiert und überprüft"],
  ["Art. 10", "Daten und Daten-Governance", "Herkunft, Eignung und Prüfung der Trainings-, Validierungs- und Testdaten"],
  ["Art. 11 · Anhang IV", "Technische Dokumentation", "Systembeschreibung, Entwicklung, Überwachung und Leistungsangaben"],
  ["Art. 12", "Aufzeichnungspflichten", "Protokollierung über die Lebensdauer des Systems"],
  ["Art. 13", "Transparenz gegenüber Betreibern", "Betriebsanleitung mit Zweck, Grenzen und erwarteter Leistung"],
  ["Art. 14", "Menschliche Aufsicht", "Verfahren, Befugnisse und Qualifikation der aufsichtführenden Personen"],
  ["Art. 15", "Genauigkeit, Robustheit, Cybersicherheit", "Angemessenes Niveau und Nachweis über den Lebenszyklus"],
  ["Art. 26", "Pflichten der Betreiber", "Einsatz gemäß Anleitung, Aufsicht, Protokollaufbewahrung, Information"],
  ["Art. 50", "Transparenzpflichten", "Kennzeichnung bei Interaktion mit KI und bei synthetischen Inhalten"],
];

const AIMS_MAPPING: [string, string, string][] = [
  ["4.1 – 4.4", "Kontext und Anwendungsbereich des AIMS", "Scope, Standorte, betroffene Prozesse"],
  ["5.2 · 5.3", "Politik, Rollen und Verantwortlichkeiten", "AI Owner, AI Risk Officer, Freigabewege"],
  ["6.1.2 · A.5.2", "AI-Risikobeurteilung", "Deckt zugleich Art. 9 und die DSFA-Vorbereitung ab"],
  ["A.6.2", "Lebenszyklus von KI-Systemen", "Entwicklung, Test, Freigabe, Betrieb, Ausserbetriebnahme"],
  ["A.7.4", "Daten für KI-Systeme", "Verbindet sich mit Art. 10 Daten-Governance"],
  ["A.9.2", "Nutzung und Aufsicht", "Verbindet sich mit Art. 14 menschliche Aufsicht"],
  ["A.10.3", "Lieferantenbeziehungen", "Verbindet sich mit Art. 25 und ISO 27001 A.5.19"],
];

export default function AiActPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">EU AI Act · ISO/IEC 42001</p>
            <h1 className="mk-h1 mt-4">
              KI-Governance, die die Einstufung belegen kann.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Compliance Hub führt Ihr KI-Register, die Risikoklassifizierung nach der
              KI-Verordnung und das Managementsystem nach ISO/IEC 42001 in einem
              Arbeitsstand zusammen — mit Verantwortlichkeit, Nachweis und Prüfpfad.
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
                href={MARKETING_ROUTES.resources}
                prefetch={false}
                className="mk-btn mk-btn--secondary mk-btn--lg"
              >
                Readiness Guide ansehen
              </Link>
            </div>
            <p className="mt-6 text-[0.75rem] leading-relaxed text-[var(--mk-fg-faint)]">
              Die Plattform unterstützt bei der strukturierten Umsetzung und erbringt keine
              Rechtsberatung. Einstufung und Freigabe bleiben bei den verantwortlichen
              Personen Ihrer Organisation.
            </p>
          </div>
        </div>
      </section>

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Register */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="register"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Schritt 1 · Register"
              title="Erst das Inventar, dann die Einstufung."
              lead="Ohne vollständiges Register bleibt jede Aussage zur KI-Verordnung eine Schätzung. Das Register erfasst Systeme, Use Cases, Anbieter, Rolle und verantwortliche Person."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mk-card mt-9 overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5">
                <p className="mk-label">KI-System-Register · Musterindustrie GmbH</p>
                <p className="mk-mono text-[var(--mk-fg-faint)]">27 Systeme erfasst</p>
              </div>
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">ID</th>
                      <th scope="col">System</th>
                      <th scope="col">Bereich</th>
                      <th scope="col">Risikoklasse</th>
                      <th scope="col">Grundlage</th>
                      <th scope="col">Owner</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {AI_SYSTEM_REGISTER.map((system) => (
                      <tr key={system.id}>
                        <td className="mk-mono whitespace-nowrap text-[var(--mk-fg-faint)]">
                          {system.id}
                        </td>
                        <td className="font-medium text-[var(--mk-fg)]">{system.name}</td>
                        <td className="whitespace-nowrap">{system.domain}</td>
                        <td className="whitespace-nowrap">
                          <StatusChip
                            tone={
                              system.riskClass === "hoch"
                                ? "crit"
                                : system.riskClass === "begrenzt"
                                  ? "warn"
                                  : "neutral"
                            }
                            dot={false}
                          >
                            {RISK_CLASS_LABEL[system.riskClass]}
                          </StatusChip>
                        </td>
                        <td className="mk-mono whitespace-nowrap text-[var(--mk-fg-faint)]">
                          {system.riskBasis}
                        </td>
                        <td className="whitespace-nowrap">{system.owner}</td>
                        <td className="whitespace-nowrap">
                          <StatusChip
                            tone={
                              system.status === "compliant"
                                ? "ok"
                                : system.status === "at-risk"
                                  ? "warn"
                                  : "crit"
                            }
                          >
                            {SYSTEM_STATUS_LABEL[system.status]}
                          </StatusChip>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Illustrativer Auszug mit Beispieldaten. Die Zuordnung zur Risikoklasse ist
                im Einzelfall zu prüfen.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Anforderungen */}
      <section className="mk-section" id="anforderungen">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Schritt 2 · Anforderungen"
              title="Aus der Einstufung folgen konkrete Pflichten."
              lead="Für Hochrisiko-Systeme führt die Plattform die Anforderungen der Verordnung als Arbeitsliste — mit Control, Nachweis und Zuständigkeit je Punkt."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 overflow-hidden rounded-[14px] border border-[var(--mk-bd)]">
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">Referenz</th>
                      <th scope="col">Anforderung</th>
                      <th scope="col">Was dafür geführt wird</th>
                    </tr>
                  </thead>
                  <tbody>
                    {REQUIREMENTS.map(([reference, requirement, detail]) => (
                      <tr key={reference}>
                        <td className="mk-mono whitespace-nowrap font-semibold text-[var(--mk-accent-700)]">
                          {reference}
                        </td>
                        <td className="font-medium text-[var(--mk-fg)]">{requirement}</td>
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

      {/* ISO 42001 Mapping */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="iso-42001"
      >
        <div className="mk-container mk-section">
          <Reveal>
            <SectionHeading
              eyebrow="Schritt 3 · Cross-Mapping"
              title="ISO/IEC 42001 trägt den Rechtsakt mit."
              lead="Wer ein AIMS aufbaut, arbeitet ohnehin an vielen Pflichten der Verordnung. Die Plattform macht die Überschneidung sichtbar und nutzbar."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9 overflow-hidden rounded-[14px] border border-[var(--mk-bd)] bg-white">
              <div className="mk-table-scroll">
                <table className="mk-table">
                  <thead>
                    <tr>
                      <th scope="col">ISO/IEC 42001</th>
                      <th scope="col">Gegenstand</th>
                      <th scope="col">Verbindung im Kontrollmodell</th>
                    </tr>
                  </thead>
                  <tbody>
                    {AIMS_MAPPING.map(([clause, subject, link]) => (
                      <tr key={clause}>
                        <td className="mk-mono whitespace-nowrap font-semibold text-[var(--mk-accent-700)]">
                          {clause}
                        </td>
                        <td className="font-medium text-[var(--mk-fg)]">{subject}</td>
                        <td className="text-[var(--mk-fg-muted)]">{link}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-[var(--mk-bd)] bg-[var(--mk-panel-subtle)] px-4 py-2.5 text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                Die Zuordnung ist eine fachliche Arbeitshilfe. Eine Zertifizierung nach
                ISO/IEC 42001 ersetzt nicht die Erfüllung der Verordnung und umgekehrt.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Mapping-Grafik */}
      <section className="mk-section" id="mapping">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Wiederverwendung"
              title="Ein Control, sechs Nachweise."
              lead="Die KI-Risikobeurteilung bedient Art. 9 der Verordnung, 6.1.2 im AIMS, 6.1.2 im ISMS, Art. 21 NIS2 und die DSFA nach Art. 35 DSGVO."
            />
          </Reveal>
          <Reveal delay={1}>
            <div className="mt-9">
              <FrameworkMappingGraph />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Evidenz */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="technical-file"
      >
        <div className="mk-container mk-section">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Schritt 4 · Technical File"
                  title="Die Dokumentation entsteht im Betrieb."
                  lead="Statt vor dem Prüftermin zu sammeln, wächst das Dossier mit der Arbeit: jede Freigabe, jede Version und jede Zuordnung landet im Prüfpfad."
                />
                <ul className="mt-6 space-y-3">
                  {[
                    "Systembeschreibung, Zweckbestimmung und Grenzen am Registereintrag",
                    "Daten-Governance mit Herkunft und Prüfung der verwendeten Datensätze",
                    "Aufsichtsverfahren mit benannten Personen und Befugnissen",
                    "Protokollierungskonzept und Aufbewahrung nach Art. 12 und Art. 26",
                    "Änderungshistorie mit Zeitstempel, Person und Prüfsumme",
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
        title="Prüfen Sie Ihre AI-Act-Readiness an einem echten System."
        lead="Bringen Sie ein KI-System aus Ihrem Haus mit. Wir gehen Register, Einstufung, Anforderungen und Nachweise gemeinsam durch."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.productTour}
      />
    </>
  );
}

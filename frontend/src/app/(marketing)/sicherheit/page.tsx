import type { Metadata } from "next";
import Link from "next/link";
import React from "react";

import { CTASection, OutcomeStrip } from "@/components/marketing/sections/Sections";
import { SectionHeading, StatusChip } from "@/components/marketing/ui/Primitives";
import { Reveal } from "@/components/marketing/ui/Reveal";
import { SecurityArchitectureDiagram } from "@/components/marketing/visuals/SecurityArchitectureDiagram";
import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

export const metadata: Metadata = {
  title: "Sicherheit & Architektur",
  description:
    "Mandantenisolation auf Datenbankebene, rollenbasierte Zugriffe, Audit-Logs, Verschlüsselung in Transit und at Rest, SSO über SAML 2.0 und Entra ID sowie EU-zentriertes Hosting mit Deutschland-Option.",
  alternates: { canonical: MARKETING_ROUTES.security },
};

const OUTCOMES = [
  {
    title: "Isolation ist eine Datenbankregel",
    detail:
      "Row Level Security erzwingt die Trennung der Mandanten unterhalb der Anwendung. Ein Fehler im Anwendungscode hebt sie nicht auf.",
  },
  {
    title: "Zugriffe kommen aus Ihrem Verzeichnis",
    detail:
      "SSO über SAML 2.0, Microsoft Entra ID oder SAP IAS. Rollen und Gruppen werden übernommen, nicht parallel gepflegt.",
  },
  {
    title: "Änderungen sind belegbar",
    detail:
      "Audit-Logs und eine verkettete Prüfsummenhistorie halten fest, wer wann was geändert oder freigegeben hat.",
  },
];

const CONTROLS: { title: string; detail: string; chips: string[] }[] = [
  {
    title: "Mandantenisolation",
    detail:
      "Jeder Datensatz trägt seinen Mandantenbezug. PostgreSQL Row Level Security prüft ihn bei jedem Zugriff, unabhängig vom aufrufenden Code. Zugriffsversuche über Mandantengrenzen hinweg werden abgewiesen und protokolliert.",
    chips: ["PostgreSQL RLS", "Least Privilege", "Deny by default"],
  },
  {
    title: "Identität und Rollen",
    detail:
      "Anmeldung über SAML 2.0, Microsoft Entra ID oder SAP IAS. Berechtigungen folgen den Gruppen Ihres Verzeichnisses; Rollenänderungen wirken beim nächsten Anmeldevorgang.",
    chips: ["SAML 2.0", "Entra ID", "SAP IAS", "RBAC"],
  },
  {
    title: "Protokollierung und Prüfpfad",
    detail:
      "Fachliche Änderungen, Freigaben und Exporte werden ergänzend geschrieben, nicht überschrieben. Eine verkettete Prüfsumme macht nachträgliche Eingriffe erkennbar.",
    chips: ["Append-only", "Audit Hash Chain", "SIEM-Weiterleitung"],
  },
  {
    title: "Verschlüsselung",
    detail:
      "Transportverschlüsselung für alle Verbindungen, Verschlüsselung ruhender Daten in Datenbank und Objektspeicher, getrennte Schlüssel je Umgebung und dokumentierte Rotation.",
    chips: ["TLS", "At Rest", "Schlüsselrotation"],
  },
  {
    title: "Betrieb und Umgebungen",
    detail:
      "Getrennte Umgebungen für Entwicklung, Abnahme und Produktion mit eigenen Zugängen und Schlüsseln. Produktionsdaten werden nicht in Vorstufen kopiert.",
    chips: ["Dev", "Staging", "Production"],
  },
  {
    title: "Datenhaltung in Europa",
    detail:
      "Betrieb in der EU mit Option auf deutsche Rechenzentrumsstandorte. Automatisierungen laufen selbst gehostet innerhalb derselben Region.",
    chips: ["EU-Hosting", "Deutschland-Option", "n8n self-hosted"],
  },
];

const AI_HANDLING: [string, string][] = [
  [
    "Zweckbindung",
    "KI-Funktionen unterstützen Recherche, Entwurf und Einordnung. Freigaben und Bewertungen bleiben bei benannten Personen.",
  ],
  [
    "Datengrundlage",
    "Die Wissensbasis arbeitet auf freigegebenen Inhalten des jeweiligen Mandanten. Ein Übergriff auf andere Mandanten ist durch dieselbe Isolation ausgeschlossen.",
  ],
  [
    "Modellnutzung",
    "Eingesetzte Modelldienste werden im Register geführt. Welcher Dienst in welcher Region genutzt wird, ist je Installation festgelegt.",
  ],
  [
    "Nachvollziehbarkeit",
    "KI-gestützte Entwürfe sind als solche gekennzeichnet und im Prüfpfad von menschlichen Freigaben unterscheidbar.",
  ],
];

export default function SecurityPage() {
  return (
    <>
      <section className="mk-dark bg-[var(--mk-navy-900)]">
        <div className="mk-container py-14 lg:py-18">
          <div className="max-w-3xl">
            <p className="mk-eyebrow">Sicherheit & Architektur</p>
            <h1 className="mk-h1 mt-4">
              Enterprise-Sicherheit, die zur Governance passt.
            </h1>
            <p className="mk-lead mt-5 text-[var(--mk-fg-soft)]">
              Eine Plattform, die Nachweise führt, muss selbst nachweisbar sein. Die
              folgenden Kontrollen sind benannt und überprüfbar formuliert — nicht als
              Versprechen, sondern als Eigenschaft der Architektur.
            </p>
            <div className="mt-7 flex flex-wrap gap-2">
              <StatusChip tone="ok">EU-Hosting</StatusChip>
              <StatusChip tone="ok">PostgreSQL RLS</StatusChip>
              <StatusChip tone="ok">SAML 2.0</StatusChip>
              <StatusChip tone="ok">Audit Hash Chain</StatusChip>
              <StatusChip tone="ok">Getrennte Umgebungen</StatusChip>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section-tight">
        <div className="mk-container">
          <OutcomeStrip items={OUTCOMES} />
        </div>
      </section>

      {/* Architektur */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="architektur"
      >
        <div className="mk-container mk-section">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-12">
            <Reveal>
              <div className="lg:sticky lg:top-28">
                <SectionHeading
                  eyebrow="Systemarchitektur"
                  title="Welche Ebene welche Kontrolle trägt."
                  lead="Präsentation, Identität, Anwendung und Daten sind getrennt. Jede Ebene hat eine klar zugeordnete Aufgabe und eigene Kontrollen."
                />
                <p className="mt-5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                  Die Auslieferung an den Browser arbeitet mit einer nonce-basierten
                  Content Security Policy ohne pauschale Skript- oder Stilfreigaben. Damit
                  bleibt die Angriffsfläche auch dann klein, wenn Inhalte aus mehreren
                  Quellen zusammenkommen.
                </p>
                <Link
                  href={MARKETING_ROUTES.trustCenter}
                  prefetch={false}
                  className="mk-link mt-5 inline-flex"
                >
                  Angaben im Trust Center prüfen
                </Link>
              </div>
            </Reveal>
            <Reveal delay={1}>
              <SecurityArchitectureDiagram />
            </Reveal>
          </div>
        </div>
      </section>

      {/* Kontrollen */}
      <section className="mk-section" id="mandantenisolation">
        <div className="mk-container">
          <Reveal>
            <SectionHeading
              eyebrow="Kontrollen"
              title="Sechs Bereiche, konkret beschrieben."
              lead="Ohne Marketingfloskeln: Was die Plattform tut, wie sie es tut und woran Sie es prüfen können."
            />
          </Reveal>
          <ul className="mt-9 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {CONTROLS.map((control, index) => (
              <Reveal key={control.title} as="li" delay={(index % 3) as 0 | 1 | 2}>
                <article className="mk-card h-full p-5">
                  <h3 className="mk-h4">{control.title}</h3>
                  <p className="mt-2.5 text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                    {control.detail}
                  </p>
                  <ul className="mt-3.5 flex flex-wrap gap-1.5">
                    {control.chips.map((chip) => (
                      <li key={chip}>
                        <StatusChip tone="neutral" dot={false}>
                          {chip}
                        </StatusChip>
                      </li>
                    ))}
                  </ul>
                </article>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      {/* Hosting */}
      <section
        className="mk-surface-subtle border-y border-[var(--mk-bd)]"
        id="hosting"
      >
        <div className="mk-container mk-section">
          <div className="grid gap-10 lg:grid-cols-2 lg:gap-12">
            <Reveal>
              <div>
                <SectionHeading
                  eyebrow="Hosting"
                  title="Betrieb in Europa, mit deutscher Option."
                  lead="Datenhaltung und Verarbeitung finden in der EU statt. Automatisierungen laufen selbst gehostet in derselben Region, nicht bei einem Drittanbieter außerhalb."
                />
                <dl className="mk-spec mt-6">
                  {[
                    ["Region", "EU, Standortwahl je Installation, Deutschland-Option"],
                    ["Datenbank", "PostgreSQL mit erzwungener Row Level Security"],
                    ["Objektspeicher", "Verschlüsselt, privat, mit dokumentierter Rotation"],
                    ["Automatisierung", "n8n, self-hosted innerhalb derselben Region"],
                    ["Sicherung", "Regelmäßige Sicherung mit geprüftem Wiederherstellungsverfahren"],
                    ["Aufbewahrung", "Fristen je Datenart vereinbart und technisch durchgesetzt"],
                  ].map(([term, value]) => (
                    <div
                      key={term}
                      className="grid gap-1 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4"
                    >
                      <dt className="text-[0.8125rem] font-semibold text-[var(--mk-fg)]">
                        {term}
                      </dt>
                      <dd className="text-[0.8125rem] leading-relaxed text-[var(--mk-fg-muted)]">
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </Reveal>

            <Reveal delay={1}>
              <div>
                <SectionHeading
                  eyebrow="KI-Funktionen"
                  title="Was die KI im Produkt darf — und was nicht."
                  lead="KI unterstützt die Arbeit an Governance. Sie trifft keine Rechts- oder Freigabeentscheidung und ersetzt keine qualifizierte Prüfung."
                />
                <ul className="mt-6 grid gap-3">
                  {AI_HANDLING.map(([title, detail]) => (
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

      <CTASection
        title="Nehmen Sie die Architektur auseinander."
        lead="Wir gehen mit Ihrer IT-Sicherheit und Ihrem Datenschutz durch, wie Isolation, Zugriffe, Protokollierung und Aufbewahrung im konkreten Betrieb aussehen."
        primaryHref={MARKETING_ROUTES.demo}
        secondaryHref={MARKETING_ROUTES.trustCenter}
        secondaryLabel="Trust Center"
        note="Angaben beschreiben die Produktarchitektur. Der für Ihre Installation freigegebene Umfang wird vertraglich und im Betriebskonzept festgehalten."
      />
    </>
  );
}

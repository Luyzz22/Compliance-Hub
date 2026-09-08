import Link from "next/link";

import type { Metadata } from "next";

import { TrustAssuranceExplorer } from "@/components/trust/TrustAssuranceExplorer";

export const metadata: Metadata = {
  title: "Trust Center – ComplianceHub",
  description:
    "Sicherheits-, Compliance- und Datenschutz-Informationen für Enterprise-Kunden, Auditoren und Partner.",
};

const frameworks = [
  { key: "EU_AI_ACT", label: "EU AI Act", icon: "AI", status: "Im Kontrollmodell" },
  { key: "ISO_42001", label: "ISO 42001", icon: "42", status: "Im Kontrollmodell" },
  { key: "ISO_27001", label: "ISO 27001", icon: "27", status: "Im Kontrollmodell" },
  { key: "NIS2", label: "NIS2", icon: "N2", status: "Im Kontrollmodell" },
  { key: "DSGVO", label: "DSGVO", icon: "EU", status: "Im Kontrollmodell" },
  { key: "GoBD", label: "GoBD", icon: "GB", status: "Im Kontrollmodell" },
];

const securityCommitments = [
  "Nonce-basierte Content Security Policy ohne pauschale Skript- oder Stilfreigaben",
  "Öffentlicher Release ohne Anmeldung, Mandantendaten oder Zustands-APIs",
  "Kein Formular-Tracking, keine Drittanbieter-Analytics und keine Marketing-Cookies",
  "Rechtliche Pflichtangaben und Datenschutzprüfung als technisches Build-Gate",
  "Nicht freigegebene App-, Auth- und API-Routen werden vor der Anwendung abgewiesen",
  "Enterprise-Datenebene bleibt bis zur separaten Evidenzfreigabe deaktiviert",
];

const dataResidencyFeatures = [
  "Der Public-Site-Release verarbeitet keine Mandanten- oder Plattformdaten",
  "Kontakt erfolgt ohne lokale Lead-Speicherung direkt über den E-Mail-Client des Nutzers",
  "Web-Auslieferung und technisch erforderliche Protokolldaten sind in der Datenschutzerklärung beschrieben",
  "Datenregionen der Enterprise-Plattform werden erst vertraglich und evidenzbasiert freigegeben",
];

/**
 * Offene Punkte des heutigen Stands. Gepflegt gegen
 * docs/market-readiness/00-executive-readiness-verdict.md — jede Zeile, die dort
 * geschlossen wird, verschwindet hier.
 */
const currentLimitations = [
  { topic: "ISO-27001-Zertifizierung", status: "Nicht vorhanden, in Vorbereitung" },
  { topic: "SOC 2 Typ II", status: "Nicht vorhanden, nicht geplant (EU-Fokus)" },
  {
    topic: "Externer Penetrationstest",
    status: "Noch nicht durchgeführt; vor dem ersten Enterprise-Einsatz vorgesehen",
  },
  { topic: "SAML 2.0", status: "Nicht verfügbar; Entra ID (OIDC) vorhanden" },
  {
    topic: "Kundenverwaltete Schlüssel (BYOK)",
    status: "Nicht verfügbar; vorgesehen mit dem Modus „EU Sovereign“",
  },
  {
    topic: "Betrieb ohne US-Dienstleister",
    status: "Nicht im Standardmodus; Modus „EU Sovereign“ auf Anfrage",
  },
  {
    topic: "Automatische Behördenmeldung",
    status: "Nicht verfügbar; abhängig von Behördenschnittstellen",
  },
  {
    topic: "Rechtsberatung",
    status: "Erbringen wir nicht — wir sind keine Rechtsanwaltskanzlei",
  },
];

export default function TrustCenterPublicPage() {
  const securityContact =
    process.env.COMPLIANCEHUB_SECURITY_CONTACT?.trim() || "/kontakt";
  const securityContactLabel = securityContact.startsWith("mailto:")
    ? securityContact.slice("mailto:".length)
    : "Security-Kontakt öffnen";

  return (
    <div className="mk-container mk-section min-w-0 space-y-12 md:space-y-16">
      {/* Hero */}
      <header className="border-b border-[var(--mk-bd)] pb-10">
        <p className="mk-eyebrow">
          Trust Center
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--mk-fg)] sm:text-[2.25rem] sm:leading-tight">
          Vertrauen auf Enterprise-Niveau.
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-[var(--mk-fg-muted)]">
          Hier dokumentieren wir den tatsächlich freigegebenen Produktionsumfang,
          Sicherheitsgrenzen und den Evidenzstatus. Der öffentliche Release ist bewusst
          von der Enterprise-Datenebene getrennt.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/kontakt"
            className="mk-btn mk-btn--primary"
          >
            Security Review anfragen
          </Link>
        </div>
      </header>

      <TrustAssuranceExplorer />

      {/* Security Overview */}
      <section aria-labelledby="security-overview">
        <h2
          id="security-overview"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Sicherheitsarchitektur
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Verifizierbare Kontrollen des stateless Public-Site-Profils. Aussagen zur
          Enterprise-Plattform sind keine Produktzertifizierung und werden erst nach
          dokumentierter Betriebsfreigabe erweitert.
        </p>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {securityCommitments.map((c) => (
            <li
              key={c}
              className="flex items-start gap-3 rounded-xl border border-[var(--mk-bd)] bg-white p-4 shadow-sm"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--mk-ok-50)] text-[var(--mk-ok-600)]">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
              <span className="text-sm text-[var(--mk-fg-soft)]">{c}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Compliance Frameworks */}
      <section aria-labelledby="compliance-frameworks">
        <h2
          id="compliance-frameworks"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Unterstützte Frameworks & Standards
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Die Produktlogik bildet Anforderungen dieser Frameworks in einem gemeinsamen
          Kontrollmodell ab. Das ist weder eine Zertifizierung noch eine automatische
          Feststellung der Rechtskonformität eines Kunden.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((fw) => (
            <div
              key={fw.key}
              className="rounded-2xl border border-[var(--mk-bd)] bg-white p-5 shadow-sm"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mk-navy-700)] font-mono text-xs font-semibold text-white" aria-hidden>{fw.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-[var(--mk-fg)]">{fw.label}</p>
                  <p className="text-xs text-[var(--mk-state-ok)] font-medium">{fw.status}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Data Residency */}
      <section aria-labelledby="data-residency">
        <h2
          id="data-residency"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Datenumfang des Public Release
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Der öffentliche Webauftritt ist technisch und organisatorisch von der späteren
          Enterprise-Datenebene getrennt.
        </p>
        <div className="mt-5 rounded-2xl border border-[var(--mk-bd)] bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-medium text-[var(--mk-fg)]">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--mk-accent-50)] text-[var(--mk-accent-700)] text-xs">01</span>
            Freigegebener Umfang: öffentliche Produktinformation
          </div>
          <ul className="mt-4 space-y-2">
            {dataResidencyFeatures.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-[var(--mk-fg-muted)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--mk-brass)]" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Subprocessor Transparency */}
      <section aria-labelledby="subprocessors">
        <h2
          id="subprocessors"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Subprocessor-Transparenz
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Für die öffentliche Website wird Vercel zur Web-Auslieferung eingesetzt. Weitere
          Unterauftragsverarbeiter und Datenregionen werden für Enterprise-Leistungen
          vertrags- und instanzbezogen offengelegt, bevor Kundendaten verarbeitet werden.
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Wir weisen zu jedem Unterauftragsverarbeiter die <strong>kontrollierende
          Jurisdiktion</strong> getrennt vom Verarbeitungsstandort aus. Vercel Inc. ist ein
          US-Unternehmen und unterliegt US-Recht — auch bei Auslieferung aus einer
          EU-Region. Wir halten es für redlicher, das offen zu benennen, als es unter
          „EU-Hosting“ zusammenzufassen.
        </p>
        <p className="mt-3 text-xs text-[var(--mk-fg-faint)]">
          Letzte Aktualisierung: 15.07.2026
        </p>
      </section>

      {/* Bewusst prominent: Grenzen des heutigen Stands. Ein Prospect findet sie in der
          Sicherheitsprüfung ohnehin; sie vorher zu nennen kostet ein Feature, sie später
          entdecken zu lassen kostet den Abschluss. */}
      <section aria-labelledby="limitations">
        <h2
          id="limitations"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Was wir heute nicht können
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Diese Punkte werden in einer Sicherheitsprüfung ohnehin auffallen. Wir nennen sie
          lieber vorher, damit Sie früh entscheiden können, ob wir zu Ihren Anforderungen
          passen.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--mk-bd)]">
                <th scope="col" className="py-2 pr-4 font-semibold text-[var(--mk-fg-soft)]">
                  Thema
                </th>
                <th scope="col" className="py-2 font-semibold text-[var(--mk-fg-soft)]">
                  Stand
                </th>
              </tr>
            </thead>
            <tbody className="text-[var(--mk-fg-muted)]">
              {currentLimitations.map((item) => (
                <tr key={item.topic} className="border-b border-[var(--mk-bd)]">
                  <th scope="row" className="py-2 pr-4 font-medium text-[var(--mk-fg-soft)]">
                    {item.topic}
                  </th>
                  <td className="py-2">{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Fehlt Ihnen etwas Entscheidendes? Sprechen Sie uns an. Wenn wir es nicht liefern
          können, sagen wir das im ersten Gespräch.
        </p>
      </section>

      {/* Responsible Disclosure */}
      <section aria-labelledby="disclosure">
        <h2
          id="disclosure"
          className="text-xl font-semibold tracking-tight text-[var(--mk-fg)]"
        >
          Responsible Disclosure & Kontakt
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--mk-fg-muted)]">
          Sicherheitslücken verantwortungsvoll melden.
        </p>
        <div className="mt-4 rounded-2xl border border-[var(--mk-bd)] bg-white p-5 shadow-sm">
          <p className="text-sm text-[var(--mk-fg-soft)]">
            <span className="font-medium">Security-Kontakt:</span>{" "}
            <a
              href={securityContact}
              className="text-[var(--mk-accent-700)] underline decoration-brand-600/25 underline-offset-4 transition hover:text-[var(--mk-fg)]"
            >
              {securityContactLabel}
            </a>
          </p>
          <p className="mt-2 text-sm text-[var(--mk-fg-soft)]">
            <span className="font-medium">PGP-Schlüssel:</span>{" "}
            <span className="text-[var(--mk-fg-faint)]">Auf Anfrage verfügbar</span>
          </p>
          <div className="mt-4">
            <Link
              href="/kontakt"
              className="inline-flex items-center justify-center rounded-xl border border-[var(--mk-bd)] bg-white px-4 py-2 text-sm font-semibold text-[var(--mk-fg-soft)] shadow-sm transition hover:border-[var(--mk-bd-strong)] hover:bg-[var(--mk-panel-subtle)]"
            >
              NDA-geschützten Zugang anfragen
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

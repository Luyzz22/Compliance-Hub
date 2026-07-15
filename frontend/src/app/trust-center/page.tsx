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

export default function TrustCenterPublicPage() {
  const securityContact =
    process.env.COMPLIANCEHUB_SECURITY_CONTACT?.trim() || "/kontakt";
  const securityContactLabel = securityContact.startsWith("mailto:")
    ? securityContact.slice("mailto:".length)
    : "Security-Kontakt öffnen";

  return (
    <div className="min-w-0 space-y-12 md:space-y-16">
      {/* Hero */}
      <header className="border-b border-slate-200/80 pb-10">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700">
          Trust Center
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-[2.25rem] sm:leading-tight">
          Vertrauen auf Enterprise-Niveau.
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-600">
          Hier dokumentieren wir den tatsächlich freigegebenen Produktionsumfang,
          Sicherheitsgrenzen und den Evidenzstatus. Der öffentliche Release ist bewusst
          von der Enterprise-Datenebene getrennt.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/kontakt"
            className="inline-flex items-center justify-center rounded-xl bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-700"
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
          className="text-xl font-semibold tracking-tight text-slate-900"
        >
          Sicherheitsarchitektur
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Verifizierbare Kontrollen des stateless Public-Site-Profils. Aussagen zur
          Enterprise-Plattform sind keine Produktzertifizierung und werden erst nach
          dokumentierter Betriebsfreigabe erweitert.
        </p>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {securityCommitments.map((c) => (
            <li
              key={c}
              className="flex items-start gap-3 rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/40"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
              <span className="text-sm text-slate-700">{c}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Compliance Frameworks */}
      <section aria-labelledby="compliance-frameworks">
        <h2
          id="compliance-frameworks"
          className="text-xl font-semibold tracking-tight text-slate-900"
        >
          Unterstützte Frameworks & Standards
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Die Produktlogik bildet Anforderungen dieser Frameworks in einem gemeinsamen
          Kontrollmodell ab. Das ist weder eine Zertifizierung noch eine automatische
          Feststellung der Rechtskonformität eines Kunden.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((fw) => (
            <div
              key={fw.key}
              className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 font-mono text-xs font-semibold text-white" aria-hidden>{fw.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{fw.label}</p>
                  <p className="text-xs text-emerald-600 font-medium">{fw.status}</p>
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
          className="text-xl font-semibold tracking-tight text-slate-900"
        >
          Datenumfang des Public Release
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Der öffentliche Webauftritt ist technisch und organisatorisch von der späteren
          Enterprise-Datenebene getrennt.
        </p>
        <div className="mt-5 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-100 text-cyan-700 text-xs">01</span>
            Freigegebener Umfang: öffentliche Produktinformation
          </div>
          <ul className="mt-4 space-y-2">
            {dataResidencyFeatures.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-slate-600">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-500" aria-hidden />
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
          className="text-xl font-semibold tracking-tight text-slate-900"
        >
          Subprocessor-Transparenz
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Für die öffentliche Website wird Vercel zur Web-Auslieferung eingesetzt. Weitere
          Unterauftragsverarbeiter und Datenregionen werden für Enterprise-Leistungen
          vertrags- und instanzbezogen offengelegt, bevor Kundendaten verarbeitet werden.
        </p>
        <p className="mt-3 text-xs text-slate-500">
          Letzte Aktualisierung: 15.07.2026
        </p>
      </section>

      {/* Responsible Disclosure */}
      <section aria-labelledby="disclosure">
        <h2
          id="disclosure"
          className="text-xl font-semibold tracking-tight text-slate-900"
        >
          Responsible Disclosure & Kontakt
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Sicherheitslücken verantwortungsvoll melden.
        </p>
        <div className="mt-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
          <p className="text-sm text-slate-700">
            <span className="font-medium">Security-Kontakt:</span>{" "}
            <a
              href={securityContact}
              className="text-cyan-700 underline decoration-cyan-600/25 underline-offset-4 transition hover:text-cyan-900"
            >
              {securityContactLabel}
            </a>
          </p>
          <p className="mt-2 text-sm text-slate-700">
            <span className="font-medium">PGP-Schlüssel:</span>{" "}
            <span className="text-slate-500">Auf Anfrage verfügbar</span>
          </p>
          <div className="mt-4">
            <Link
              href="/kontakt"
              className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
            >
              NDA-geschützten Zugang anfragen
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

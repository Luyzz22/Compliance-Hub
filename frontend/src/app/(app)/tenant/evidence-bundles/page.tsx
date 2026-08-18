import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BADGE,
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

const bundleTypes = [
  {
    key: "iso_27001",
    title: "ISO 27001 Evidence Bundle",
    description: "ISMS-Policies, Kontroll-Mappings, Audit-Log-Exporte und Risikozusammenfassungen.",
    icon: "🔒",
    frameworks: ["ISO 27001"],
    audience: "ISO-Auditoren",
    signed: true,
    keyId: "v1",
    longTermValid: true,
  },
  {
    key: "nis2",
    title: "NIS2 Compliance Bundle",
    description: "NIS2-Pflicht-Mappings, Incident-Zusammenfassungen und Kontrollnachweise.",
    icon: "🛡️",
    frameworks: ["NIS2"],
    audience: "NIS2-Assessoren",
    signed: false,
    keyId: null,
    longTermValid: false,
  },
  {
    key: "dsgvo",
    title: "DSGVO / GDPR Evidence Bundle",
    description: "Verarbeitungsverzeichnis, TOM-Dokumentation und AVV-Nachweise.",
    icon: "🇪🇺",
    frameworks: ["DSGVO"],
    audience: "Datenschutzbeauftragte, Aufsichtsbehörden",
    signed: true,
    keyId: "v1",
    longTermValid: true,
  },
  {
    key: "eu_ai_act",
    title: "EU AI Act Evidence Bundle",
    description: "KI-Register, Risikoklassifikationen und Human-Oversight-Nachweise.",
    icon: "🤖",
    frameworks: ["EU AI Act", "ISO 42001"],
    audience: "AI-Act-Aufsichtsbehörden",
    signed: false,
    keyId: null,
    longTermValid: false,
  },
  {
    key: "gobd_revision",
    title: "GoBD / Revision Evidence Bundle",
    description: "GoBD-Compliance-Nachweise, DATEV-Exporte und Audit-Trails.",
    icon: "📊",
    frameworks: ["GoBD"],
    audience: "Steuerprüfer, Wirtschaftsprüfer",
    signed: true,
    keyId: "v2",
    longTermValid: true,
  },
  {
    key: "vendor_security_review",
    title: "Vendor Security Review Bundle",
    description: "Sicherheitsüberblick, Architektur und Kontrollzusammenfassung.",
    icon: "🏢",
    frameworks: ["ISO 27001", "NIS2"],
    audience: "Procurement-Teams",
    signed: false,
    keyId: null,
    longTermValid: false,
  },
  {
    key: "auditor_bundle",
    title: "Auditor Full Evidence Bundle",
    description: "Vollständiges Audit-Evidenzpaket über alle Frameworks hinweg.",
    icon: "📦",
    frameworks: ["Alle Frameworks"],
    audience: "Externe Auditoren",
    signed: false,
    keyId: null,
    longTermValid: false,
  },
];

export default function TenantEvidenceBundlesPage() {
  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Trust Center"
        title="Evidence Bundles"
        description="One-Click Evidence-Pakete für Due Diligence, Audits und Vendor Security Reviews. Bündel werden aus vorhandenen Artefakten zusammengestellt und mit sauberen Metadaten versehen."
        breadcrumbs={[
          { label: "Workspace", href: "/tenant/compliance-overview" },
          { label: "Trust Center", href: "/tenant/trust-center" },
          { label: "Evidence Bundles" },
        ]}
        actions={
          <Link
            href="/tenant/trust-center"
            className={`${CH_BTN_SECONDARY} text-sm`}
          >
            Zurück zum Assurance Portal
          </Link>
        }
      />

      {/* Bundle metadata info */}
      <section aria-label="Metadaten-Informationen" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Bundle-Metadaten</p>
        <p className="mt-2 text-sm text-slate-600">
          Jedes Evidence Bundle enthält strukturierte Metadaten: Erstellungszeitpunkt,
          Gültigkeitsstand, Tenant/Scope und Sensitivitätsstufe. Alle Bundle-Generierungen
          werden im Audit-Log protokolliert.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[0.65rem] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200/80">
            Erstellt am
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[0.65rem] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200/80">
            Gültigkeitsstand
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[0.65rem] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200/80">
            Tenant / Scope
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[0.65rem] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200/80">
            Sensitivitätsstufe
          </span>
        </div>
      </section>

      {/* Bundle Types Grid */}
      <section aria-label="Verfügbare Bundle-Typen">
        <p className={CH_SECTION_LABEL}>Verfügbare Evidence Bundles</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {bundleTypes.map((bundle) => (
            <article key={bundle.key} className={`${CH_CARD} flex flex-col`}>
              <div className="flex items-start gap-3">
                <span className="mt-0.5 text-2xl" aria-hidden>{bundle.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900">{bundle.title}</p>
                    {bundle.signed ? (
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[0.6rem] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200/70">
                        ✅ Signiert
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[0.6rem] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200/70">
                        ⏳ Unsigniert
                      </span>
                    )}
                  </div>
                  {bundle.signed && bundle.keyId && (
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className={`${CH_BADGE} bg-indigo-50 text-indigo-700 ring-indigo-200/70`}>
                        🔑 Key: {bundle.keyId}
                      </span>
                      {bundle.longTermValid ? (
                        <span className={`${CH_BADGE} bg-emerald-50 text-emerald-700 ring-emerald-200/70`}>
                          🛡️ Langzeit-gültig
                        </span>
                      ) : (
                        <span className={`${CH_BADGE} bg-red-50 text-red-700 ring-red-200/70`}>
                          ⚠️ Nicht langzeit-gültig
                        </span>
                      )}
                    </div>
                  )}
                  <div className="mt-1 flex flex-wrap gap-1">
                    {bundle.frameworks.map((fw) => (
                      <span
                        key={fw}
                        className="inline-flex items-center rounded-full bg-cyan-50 px-2 py-0.5 text-[0.6rem] font-medium text-cyan-700"
                      >
                        {fw}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <p className="mt-3 flex-1 text-sm text-slate-600">{bundle.description}</p>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Für: {bundle.audience}
                </span>
                <div className="flex gap-2">
                  {!bundle.signed && (
                    <button
                      type="button"
                      className={`${CH_BTN_SECONDARY} !px-3 !py-1.5 !text-xs`}
                      title={`${bundle.title} signieren`}
                    >
                      Jetzt signieren
                    </button>
                  )}
                  <button
                    type="button"
                    className={`${CH_BTN_PRIMARY} !px-3 !py-1.5 !text-xs`}
                    title={`${bundle.title} generieren`}
                  >
                    Generieren
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Included artefact types */}
      <section aria-label="Enthaltene Artefakte" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Enthaltene Artefakt-Typen</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {[
            "Immutable Audit-Log Exporte",
            "Policy-Dokumente",
            "Control-Mappings",
            "Register-Zusammenfassungen",
            "Risiko- / Incident-Summaries",
            "Board-/Assurance-PDFs",
          ].map((artefact) => (
            <div
              key={artefact}
              className="flex items-center gap-2 rounded-lg border border-slate-200/60 bg-slate-50/80 p-3"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
              <span className="text-sm text-slate-700">{artefact}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

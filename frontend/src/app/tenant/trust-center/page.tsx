import Link from "next/link";

import { EnterprisePageHeader } from "@/components/sbs/EnterprisePageHeader";
import {
  CH_BTN_PRIMARY,
  CH_BTN_SECONDARY,
  CH_CARD,
  CH_SECTION_LABEL,
  CH_SHELL,
} from "@/lib/boardLayout";

const assetCategories = [
  {
    key: "policies",
    label: "Policies & Richtlinien",
    icon: "📄",
    description: "Informationssicherheits-, Datenschutz- und AI-Governance-Richtlinien.",
    sensitivity: "customer",
    sensitivityLabel: "🟡 Customer",
    sensitivityColor: "bg-yellow-100 text-yellow-800 ring-yellow-200/70",
  },
  {
    key: "certificates",
    label: "Zertifikate & Nachweise",
    icon: "🏅",
    description: "ISO-Zertifikate, SOC-Reports und externe Prüfberichte.",
    sensitivity: "auditor",
    sensitivityLabel: "🔴 Auditor",
    sensitivityColor: "bg-red-100 text-red-800 ring-red-200/70",
  },
  {
    key: "audit_reports",
    label: "Audit-Reports",
    icon: "📊",
    description: "Interne und externe Auditberichte mit Maßnahmenverfolgung.",
    sensitivity: "auditor",
    sensitivityLabel: "🔴 Auditor",
    sensitivityColor: "bg-red-100 text-red-800 ring-red-200/70",
  },
  {
    key: "toms",
    label: "TOMs & Security Controls",
    icon: "🔒",
    description: "Technische und organisatorische Maßnahmen gemäß Art. 32 DSGVO.",
    sensitivity: "customer",
    sensitivityLabel: "🟡 Customer",
    sensitivityColor: "bg-yellow-100 text-yellow-800 ring-yellow-200/70",
  },
  {
    key: "compliance_snapshots",
    label: "Compliance-Status-Snapshots",
    icon: "📈",
    description: "Aktuelle Compliance-Standings über alle Frameworks hinweg.",
    sensitivity: "customer",
    sensitivityLabel: "🟡 Customer",
    sensitivityColor: "bg-yellow-100 text-yellow-800 ring-yellow-200/70",
  },
  {
    key: "board_pdfs",
    label: "Board & Assurance PDFs",
    icon: "📑",
    description: "Board-Reports, Executive Summaries und Assurance-Dokumentation.",
    sensitivity: "internal",
    sensitivityLabel: "⚫ Internal",
    sensitivityColor: "bg-slate-800 text-white ring-slate-700",
  },
];

const accessTiers = [
  { role: "Prospect", access: "Öffentliche Übersicht, Security-Overview", color: "bg-slate-100 text-slate-700" },
  { role: "Customer", access: "Policies, TOMs, Compliance-Snapshots", color: "bg-cyan-50 text-cyan-800" },
  { role: "Auditor", access: "Zertifikate, Audit-Reports, Evidence Bundles", color: "bg-amber-50 text-amber-800" },
  { role: "Internal Reviewer", access: "Vollzugriff inkl. Board-PDFs", color: "bg-emerald-50 text-emerald-800" },
];

export default function TenantTrustCenterPage() {
  return (
    <div className={CH_SHELL}>
      <EnterprisePageHeader
        eyebrow="Trust Center"
        title="Assurance Portal"
        description="Kontrollierter Zugang zu Compliance-Nachweisen, Sicherheitsinformationen und Audit-Dokumentation für Kunden, Auditoren und Partner."
        breadcrumbs={[
          { label: "Workspace", href: "/tenant/compliance-overview" },
          { label: "Trust Center" },
        ]}
        actions={
          <div className="flex gap-2">
            <Link
              href="/tenant/evidence-bundles"
              className={`${CH_BTN_PRIMARY} text-sm`}
            >
              Evidence Bundles
            </Link>
            <Link
              href="/tenant/compliance-mapping"
              className={`${CH_BTN_SECONDARY} text-sm`}
            >
              Compliance Mapping
            </Link>
          </div>
        }
      />

      {/* Access Tiers */}
      <section aria-label="Zugangsstufen">
        <p className={CH_SECTION_LABEL}>Zugangsstufen</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {accessTiers.map((tier) => (
            <div key={tier.role} className={CH_CARD}>
              <span className={`inline-block rounded-full px-2.5 py-0.5 text-[0.65rem] font-semibold ${tier.color}`}>
                {tier.role}
              </span>
              <p className="mt-2 text-sm text-slate-600">{tier.access}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Document Categories */}
      <section aria-label="Dokumentenkategorien">
        <p className={CH_SECTION_LABEL}>Verfügbare Dokumentenkategorien</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {assetCategories.map((cat) => (
            <article key={cat.key} className={CH_CARD}>
              <div className="flex items-center gap-3">
                <span className="text-2xl" aria-hidden>{cat.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{cat.label}</p>
                  <span className={`mt-0.5 inline-flex items-center rounded-full px-2 py-0.5 text-[0.6rem] font-semibold ring-1 ring-inset ${cat.sensitivityColor}`}>
                    {cat.sensitivityLabel}
                  </span>
                </div>
              </div>
              <p className="mt-3 text-sm text-slate-600">{cat.description}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Quick Actions */}
      <section aria-label="Schnellzugriff" className={CH_CARD}>
        <p className={CH_SECTION_LABEL}>Schnellzugriff</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Link
            href="/tenant/evidence-bundles"
            className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-center transition hover:border-cyan-200 hover:bg-cyan-50/50"
          >
            <span className="text-2xl" aria-hidden>📦</span>
            <p className="mt-2 text-sm font-medium text-slate-900">Evidence Bundles</p>
            <p className="mt-1 text-xs text-slate-500">Due-Diligence-Pakete generieren</p>
          </Link>
          <Link
            href="/tenant/compliance-mapping"
            className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-center transition hover:border-cyan-200 hover:bg-cyan-50/50"
          >
            <span className="text-2xl" aria-hidden>🗺️</span>
            <p className="mt-2 text-sm font-medium text-slate-900">Compliance Mapping</p>
            <p className="mt-1 text-xs text-slate-500">Controls × Frameworks Übersicht</p>
          </Link>
          <Link
            href="/tenant/audit-log"
            className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-center transition hover:border-cyan-200 hover:bg-cyan-50/50"
          >
            <span className="text-2xl" aria-hidden>📋</span>
            <p className="mt-2 text-sm font-medium text-slate-900">Audit-Log</p>
            <p className="mt-1 text-xs text-slate-500">Unveränderliche Ereignisspur</p>
          </Link>
        </div>
      </section>

      {/* Governance & Transparency */}
      <section aria-label="Governance und Transparenz">
        <p className={CH_SECTION_LABEL}>Governance & Transparenz</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className={CH_CARD}>
            <p className="text-sm font-semibold text-slate-900">Datenstandort</p>
            <p className="mt-1 text-sm text-slate-600">
              EU (Frankfurt / DACH) – keine Verarbeitung außerhalb der EU.
            </p>
          </div>
          <div className={CH_CARD}>
            <p className="text-sm font-semibold text-slate-900">Letzte Überprüfung</p>
            <p className="mt-1 text-sm text-slate-600">
              Trust-Center-Inhalte werden quartalsweise überprüft und aktualisiert.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
